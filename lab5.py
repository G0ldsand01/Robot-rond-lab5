import cv2
import numpy as np
import time
import RPi.GPIO as GPIO
import flask
import flask_cors
from flask import request
import os
import sqlite3

conn = sqlite3.connect('moteurs.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS moteurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    isDirGauche INTEGER,
    isVitGauche INTEGER,
    isDirDroite INTEGER,
    isVitDroite INTEGER
    )''')
conn.commit()
conn.close()

app = flask.Flask(__name__)
cors = flask_cors.CORS(app)

#Moteurs
GPIO_PIN_VIT_GAUCHE = 27
GPIO_PIN_VIT_DROITE = 23
GPIO_PIN_DIR_GAUCHE = 17
GPIO_PIN_DIR_DROITE = 22
GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_PIN_VIT_GAUCHE, GPIO.OUT)
GPIO.setup(GPIO_PIN_VIT_DROITE, GPIO.OUT)
GPIO.setup(GPIO_PIN_DIR_GAUCHE, GPIO.OUT)
GPIO.setup(GPIO_PIN_DIR_DROITE, GPIO.OUT)

def stop():
    GPIO.output(GPIO_PIN_VIT_GAUCHE, GPIO.LOW)
    GPIO.output(GPIO_PIN_VIT_DROITE, GPIO.LOW)
    GPIO.output(GPIO_PIN_DIR_GAUCHE, GPIO.LOW)
    GPIO.output(GPIO_PIN_DIR_DROITE, GPIO.LOW)
    cursor.execute("INSERT INTO moteurs VALUES (NULL, ?, ?, ?, ?)", (0, 0, 0, 0))
    GPIO.cleanup()


def gauche():
    print('Gauche!')
    GPIO.output(GPIO_PIN_VIT_GAUCHE, GPIO.LOW)
    GPIO.output(GPIO_PIN_VIT_DROITE, GPIO.HIGH)
    GPIO.output(GPIO_PIN_DIR_GAUCHE, GPIO.LOW)
    GPIO.output(GPIO_PIN_DIR_DROITE, GPIO.HIGH)
    cursor.execute("INSERT INTO moteurs VALUES (NULL, ?, ?, ?, ?)", (0, 1, 0, 1))
    time.sleep(0.01)

def droite():
    print('Droite!')
    GPIO.output(GPIO_PIN_VIT_GAUCHE, GPIO.HIGH)
    GPIO.output(GPIO_PIN_VIT_DROITE, GPIO.LOW)
    GPIO.output(GPIO_PIN_DIR_GAUCHE, GPIO.HIGH)
    GPIO.output(GPIO_PIN_DIR_DROITE, GPIO.LOW)
    cursor.execute("INSERT INTO moteurs VALUES (NULL, ?, ?, ?, ?)", (1, 0, 1, 0))
    time.sleep(0.01)

def enAvant():
    print('En avant!')
    GPIO.output(GPIO_PIN_VIT_GAUCHE, GPIO.HIGH)
    GPIO.output(GPIO_PIN_VIT_DROITE, GPIO.HIGH)
    GPIO.output(GPIO_PIN_DIR_GAUCHE, GPIO.LOW)
    GPIO.output(GPIO_PIN_DIR_DROITE, GPIO.LOW)
    cursor.execute("INSERT INTO moteurs VALUES (NULL, ?, ?, ?, ?)", (1, 1, 0, 0))
    time.sleep(0.1)


def enArriere():
    print('En arriere!')
    GPIO.output(GPIO_PIN_VIT_GAUCHE, GPIO.LOW)
    GPIO.output(GPIO_PIN_VIT_DROITE, GPIO.LOW)
    GPIO.output(GPIO_PIN_DIR_GAUCHE, GPIO.HIGH)
    GPIO.output(GPIO_PIN_DIR_DROITE, GPIO.LOW)
    cursor.execute("INSERT INTO moteurs VALUES (NULL, ?, ?, ?, ?)", (0, 0, 1, 1))
    time.sleep(1)

def detect_red_ball(frame):
    """
    Detects a Green ball in an image using OpenCV.

    Args:
        frame: The input image frame.

    Returns:
        A tuple containing:
            - The center coordinates of the detected ball (x, y) if found, 
              otherwise None.
            - The radius of the detected ball if found, otherwise None.
    """

    # Define the lower and upper bounds for Green color in HSV
    lower_green = np.array([10, 250, 100])
    upper_green = np.array([50, 120, 0])

    # Convert the image from BGR to HSV color space
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Create a mask for the red color range
    mask = cv2.inRange(hsv, lower_green, upper_green)

    # Find contours in the masked image
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Find the largest contour (assuming it's the ball)
    if len(contours) > 0:
        largest_contour = max(contours, key=cv2.contourArea)

        # Fit a circle to the contour
        (x, y), radius = cv2.minEnclosingCircle(largest_contour)
        center = (int(x), int(y))
        radius = int(radius)

        return center, radius
    else:
        return None, None

# Example usage with a video file
cap = cv2.VideoCapture(0)

previous = "nothing"
lostCount = 0

@app.route('/moteurs' , methods=['POST', 'GET'])
def post_moteurs():
    moteurs = request.json
    print(moteurs)
    if moteurs["isDirGauche"]:
        gauche()
    elif moteurs["isDirDroite"]:
        droite()
    elif moteurs["isVitGauche"]:
        enAvant()
    elif moteurs["isVitDroite"]:
        enArriere()
    stop()
    cursor.execute("INSERT INTO moteurs VALUES (NULL, ?, ?, ?, ?)", (moteurs["isDirGauche"], moteurs["isVitGauche"], moteurs["isDirDroite"], moteurs["isVitDroite"]))
    return "OK"

@app.route('/camera')
def get_camera():
    # Capture frame-by-frame from the camera
    ret, frame = cap.read()
    if not ret:
        return "Failed to capture image", 500

    # Encode the frame as JPEG
    _, buffer = cv2.imencode('.jpg', frame)
    response = flask.make_response(buffer.tobytes())
    response.headers.set('Content-Type', 'image/jpeg')
    return response


while(True):
    # Capture frame-by-frame
    ret, frame = cap.read()

    if not ret:
        break

    # Detect the red ball
    center, radius = detect_red_ball(frame)

    # Draw a circle around the detected ball if found
    if center is not None:
        cv2.circle(frame, center, radius, (0, 255, 0), 2)
        print(center)
        lostCount = 0
        if(center[0]>300):
            droite()
            previous = "droite"
        elif(center[0]<200):
            gauche()
            previous = "gauche"
        enAvant()
    elif previous == "gauche" and lostCount < 100:
        droite()
        lostCount+=1
    elif previous == "droite" and lostCount < 100:
        gauche()
        lostCount+=1
    cursor.execute("INSERT INTO moteurs VALUES (NULL, ?, ?, ?, ?)", (0, 0, 0, 0))  # Replace with appropriate values or logic
    stop()


    # Display the resulting frame
    cv2.imshow('frame', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()
GPIO.cleanup()
conn.commit()
conn.close()