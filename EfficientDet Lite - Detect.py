import threading 

import argparse
import sys
import time
import subprocess #calling tts
import os

import cv2
from tflite_support.task import core
from tflite_support.task import processor
from tflite_support.task import vision
import utils
import csv
import RPi.GPIO as GPIO
import pygame

from collections import Counter, deque



results_file = open("efficientdet_latency_results.csv", "w", newline="")
csv_writer = csv.writer(results_file)
csv_writer.writerow(["Frame", "Latency (ms)", "FPS"])

DEBOUNCE_HISTORY = deque(maxlen=5)
last_spoken = ""
last_spoken_time = 0
speak_cooldown = 3

"""------------------------- SENSOR INITIALISATION ---------------------- """

#INITIALISE PYGAME MIXER
pygame.mixer.init()

#LOAD BEEP SOUND
beep = pygame.mixer.Sound("beep.wav") # BEEP.wav should be in same dir 

# Set GPIO mode
GPIO.setmode(GPIO.BCM)

# Define GPIO pins
TRIG = 23  # Trigger Pin
ECHO = 24  # Echo Pin

# Set up GPIO pins
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# Distance thresholds (cm)
MAX_DISTANCE = 175  # Ignore objects beyond this
FAST_BEEP = 100  # <100cm = very fast beep
MEDIUM_BEEP = 120  # <120cm = medium speed beep
SLOW_BEEP =150 # <150cm = slow beep

def measure_distance():
    #Measures distance using sensor
    GPIO.output(TRIG, False)
    time.sleep(0.1)
    
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)
    
    start_time = time.time()
    timeout = start_time + 0.2 # prevent infinite loop
    
    
    while GPIO.input(ECHO) == 0:
        if time.time() > timeout:
            return MAX_DISTANCE # if timeout assume max dist
        start_time = time.time()
        

    end_time = time.time()
    timeout = end_time + 0.2 # prevent another infinite loop
    
    
    while GPIO.input(ECHO) == 1:
        if time.time() > timeout:
            return MAX_DISTANCE
        end_time = time.time()

    duration = end_time - start_time
    distance = (duration * 34300) / 2  # cm

    return distance
    
def beep_controller():
    #CONTROLS BEEP FREQ BASED ON DIST
    try:
        while True:
            distance = measure_distance()
           

            if distance < FAST_BEEP:  # Very close, very fast beeping
                beep_interval = 0.1
                print("Very close: Fast beeping (interval 0.1s)")
            elif distance < MEDIUM_BEEP:  # Medium range, faster beeping
                beep_interval = 0.3
                print("Close: Medium beeping (interval 0.3s)")
            elif distance < SLOW_BEEP:  # Farther, slow beeping
                beep_interval = 0.7
                print("Moderate distance: Slow beeping (interval 0.7s)")

            else:
                beep_interval = 1.5  # No beep if too far
                print("Object too far: No beep")

            if distance < MAX_DISTANCE:
                beep.play()

            time.sleep(beep_interval)  # Adjust beep frequency dynamically
        
    except KeyboardInterrupt:
        GPIO.cleanup()

def format_label_summary(label_counts):
  parts = []
  for label, count in label_counts.items():
    if count == 1:
      parts.append(f"a {label}")
    else:
      parts.append(f"{count} {label}s")
      
    if not parts:
      return ""
      
    if len(parts) == 1:
      return parts[0]
    elif len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    else:
      return ", ".join(parts[:-1]) + " and " + parts[-1]
    


def narrate_with_espeak_from_labels(label_list):
  global last_spoken, last_spoken_time
  now = time.time()
  DEBOUNCE_HISTORY.append(Counter(label_list))
  
  if len(DEBOUNCE_HISTORY) < 3:
    return
    
  label_presence = Counter()
  for frame_counts in DEBOUNCE_HISTORY:
    for label in frame_counts:
      label_presence[label] += 1
    
    stable_labels = [label for label, frames_present in label_presence.items() if frames_present >= 1]
    
    label_counts = Counter(label for label in label_list if label in stable_labels)
    
    
    if not stable_labels:
      return
      
  print(f"[DEBUG] label_list: {label_list}")
  print(f"[DEBUG] stable_counts: {stable_labels}")
  print(f"[DEBUG] narration i see {format_label_summary(label_counts)}")
    
  #label_counts = Counter(label_list)
  summary = format_label_summary(label_counts)
	
  if summary == last_spoken and (now - last_spoken_time) < speak_cooldown:
    return
	
  last_spoken = summary
  
  last_spoken_time = now
  
  narration_text = f"I see {summary}."
  print(f"[Narration] {narration_text}")
	
  def speak():
      try:
        subprocess.run(["espeak", narration_text], check=True)
      except Exception as e:
        print(f"Error with eSpeak:  {e}")
  threading.Thread(target=speak, daemon=True).start()

def run(model: str, camera_id: int, width: int, height: int, num_threads: int,
        enable_edgetpu: bool) -> None:
  """Continuously run inference on images acquired from the camera.

  Args:
    model: Name of the TFLite object detection model.
    camera_id: The camera id to be passed to OpenCV.
    width: The width of the frame captured from the camera.
    height: The height of the frame captured from the camera.
    num_threads: The number of CPU threads to run the model.
    enable_edgetpu: True/False whether the model is a EdgeTPU model.
  """


  # Variables to calculate FPS
  counter, fps = 0, 0
  start_time = time.time()

  # Start capturing video input from the camera
  cap = cv2.VideoCapture("slowedDarkNIGHtComp.mp4")
  cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
  cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

  # Visualization parameters
  row_size = 20  # pixels
  left_margin = 24  # pixels
  text_color = (0, 0, 255)  # red
  font_size = 1
  font_thickness = 1
  fps_avg_frame_count = 10

  # Initialize the object detection model
  base_options = core.BaseOptions(
      file_name=model, use_coral=enable_edgetpu, num_threads=num_threads)
  detection_options = processor.DetectionOptions(
      max_results=3, score_threshold=0.5)
  options = vision.ObjectDetectorOptions(
      base_options=base_options, detection_options=detection_options)
  detector = vision.ObjectDetector.create_from_options(options)

  # Continuously capture images from the camera and run inference
  while cap.isOpened():
    success, image = cap.read()
    if not success:
      sys.exit(
          'ERROR: Unable to read from webcam. Please verify your webcam settings.'
      )

    counter += 1
    #image = cv2.flip(image, 1)

    # Convert the image from BGR to RGB as required by the TFLite model.
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Create a TensorImage object from the RGB image.
    input_tensor = vision.TensorImage.create_from_array(rgb_image)

    # Run object detection estimation using the model.
        # 🕒 Start measuring inference time
    start_inference = time.time()

    # Run object detection
    detection_result = detector.detect(input_tensor)

    # 🕒 End measuring inference time
    end_inference = time.time()

    # Calculate latency and FPS
    latency_ms = (end_inference - start_inference) * 1000
    fps_current = 1 / (end_inference - start_inference)

    print(f"[Frame {counter}] Latency: {latency_ms:.2f} ms | FPS: {fps:.2f}")
    csv_writer.writerow([counter, latency_ms, fps])


    # Draw keypoints and edges on input image
    image = utils.visualize(image, detection_result)
    
    # Narrate the detected objects
    if detection_result.detections:
      label_list = []
      for detection in detection_result.detections:
        label = detection.categories[0].category_name
        label_list.append(label)
        
      # Get most confident detection
      #most_confident_detection = detection_result.detections[0]
      #label = most_confident_detection.categories[0].category_name
      #confidence = most_confident_detection.categories[0].score
      
      # Format text for narration
      #narration_text = f"There is a {label} detected."
      #print(narration_text) # For debugging
      print("[DEBUG] Detected labels:", label_list)
      narrate_with_espeak_from_labels(label_list)

    # Calculate the FPS
    if counter % fps_avg_frame_count == 0:
      end_time = time.time()
      fps = fps_avg_frame_count / (end_time - start_time)
      start_time = time.time()

    # Show the FPS
    fps_text = 'FPS = {:.1f}'.format(fps)
    text_location = (left_margin, row_size)
    cv2.putText(image, fps_text, text_location, cv2.FONT_HERSHEY_PLAIN,
                font_size, text_color, font_thickness)

    # Stop the program if the ESC key is pressed.
    if cv2.waitKey(1) == 27:
      break
    cv2.imshow('object_detector', image)
  
  results_file.close()
  

  cap.release()
  cv2.destroyAllWindows()


def main():
  parser = argparse.ArgumentParser(
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument(
      '--model',
      help='Path of the object detection model.',
      required=False,
      default='efficientdet_lite0.tflite')
  parser.add_argument(
      '--cameraId', help='Id of camera.', required=False, type=int, default=0)
  parser.add_argument(
      '--frameWidth',
      help='Width of frame to capture from camera.',
      required=False,
      type=int,
      default=640)
  parser.add_argument(
      '--frameHeight',
      help='Height of frame to capture from camera.',
      required=False,
      type=int,
      default=480)
  parser.add_argument(
      '--numThreads',
      help='Number of CPU threads to run the model.',
      required=False,
      type=int,
      default=4)
  parser.add_argument(
      '--enableEdgeTPU',
      help='Whether to run the model on EdgeTPU.',
      action='store_true',
      required=False,
      default=False)
  args = parser.parse_args()

  run(args.model, int(args.cameraId), args.frameWidth, args.frameHeight,
      int(args.numThreads), bool(args.enableEdgeTPU))
      


if __name__ == '__main__':
  #START BEEP THREAD
  beep_thread = threading.Thread(target=beep_controller, daemon=True)
  beep_thread.start()
  
  main()
