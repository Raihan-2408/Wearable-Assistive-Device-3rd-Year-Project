import RPi.GPIO as GPIO
import time
import pygame

# Initialize pygame mixer
pygame.mixer.init()

# Load beep sound
beep = pygame.mixer.Sound("beep.wav")  # Ensure "beep.wav" is in the same directory

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
FAST_BEEP = 100  # <10cm = very fast beep
MEDIUM_BEEP = 125  # <30cm = medium speed beep
SLOW_BEEP = 150  # <60cm = slow beep

def measure_distance():
    GPIO.output(TRIG, False)
    time.sleep(0.1)

    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    start_time = time.time()
    while GPIO.input(ECHO) == 0:
        start_time = time.time()

    end_time = time.time()
    while GPIO.input(ECHO) == 1:
        end_time = time.time()

    duration = end_time - start_time
    distance = (duration * 34300) / 2  # cm

    return distance

try:
    while True:
        distance = measure_distance()
        print(f"Distance: {distance:.2f} cm")

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

        if distance < MAX_DISTANCE and beep_interval < 1.5:
            beep.play()

        time.sleep(beep_interval)  # Adjust beep frequency dynamically

except KeyboardInterrupt:
    print("Measurement stopped")
    GPIO.cleanup()
