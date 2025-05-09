import cv2
import numpy as np
import time
import threading
import RPi.GPIO as GPIO
import flask
import flask_cors
from flask import request, render_template
import sqlite3
import atexit
from datetime import datetime
def log_action(action, details=""):
    conn = sqlite3.connect('moteurs.db')
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO logs (timestamp, action, details) VALUES (?, ?, ?)", (timestamp, action, details))
    conn.commit()
    conn.close()

# === Flask App Setup ===
app = flask.Flask(__name__)
flask_cors.CORS(app)

# === GPIO Setup ===
GPIO_PIN_VIT_GAUCHE = 27
GPIO_PIN_VIT_DROITE = 23
GPIO_PIN_DIR_GAUCHE = 17
GPIO_PIN_DIR_DROITE = 22
GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_PIN_VIT_GAUCHE, GPIO.OUT)
GPIO.setup(GPIO_PIN_VIT_DROITE, GPIO.OUT)
GPIO.setup(GPIO_PIN_DIR_GAUCHE, GPIO.OUT)
GPIO.setup(GPIO_PIN_DIR_DROITE, GPIO.OUT)

    #=== Motor Commands ===
def stop():
   GPIO.output(GPIO_PIN_VIT_GAUCHE, GPIO.LOW)
   GPIO.output(GPIO_PIN_VIT_DROITE, GPIO.LOW)
   GPIO.output(GPIO_PIN_DIR_GAUCHE, GPIO.LOW)
   GPIO.output(GPIO_PIN_DIR_DROITE, GPIO.LOW)

def enAvant():
   print('En avant!')
   GPIO.output(GPIO_PIN_VIT_GAUCHE, GPIO.LOW)
   GPIO.output(GPIO_PIN_VIT_DROITE, GPIO.HIGH)
   GPIO.output(GPIO_PIN_DIR_GAUCHE, GPIO.LOW)
   GPIO.output(GPIO_PIN_DIR_DROITE, GPIO.HIGH)

def enArriere():
   print('En arrière!')
   GPIO.output(GPIO_PIN_VIT_GAUCHE, GPIO.HIGH)
   GPIO.output(GPIO_PIN_VIT_DROITE, GPIO.HIGH)
   GPIO.output(GPIO_PIN_DIR_GAUCHE, GPIO.HIGH)
   GPIO.output(GPIO_PIN_DIR_DROITE, GPIO.HIGH)

def gauche():
   print('Gauche!')
   GPIO.output(GPIO_PIN_VIT_GAUCHE, GPIO.HIGH)
   GPIO.output(GPIO_PIN_VIT_DROITE, GPIO.HIGH)
   GPIO.output(GPIO_PIN_DIR_GAUCHE, GPIO.LOW)
   GPIO.output(GPIO_PIN_DIR_DROITE, GPIO.LOW)
    
def droite():
   print('Droite!')
   GPIO.output(GPIO_PIN_VIT_GAUCHE, GPIO.LOW)
   GPIO.output(GPIO_PIN_VIT_DROITE, GPIO.LOW)
   GPIO.output(GPIO_PIN_DIR_GAUCHE, GPIO.HIGH)
   GPIO.output(GPIO_PIN_DIR_DROITE, GPIO.HIGH)
    
    # === SQLite Setup ===
def init_db():
   conn = sqlite3.connect('moteurs.db')
   cursor = conn.cursor()

   cursor.execute('''CREATE TABLE IF NOT EXISTS moteurs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  isLeftPressed INTEGER,
  isRightPressed INTEGER,
  isForwardPressed INTEGER,
  isReversePressed INTEGER
   )''')

   cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT,
  action TEXT,
  details TEXT
   )''')

   conn.commit()
   conn.close()
init_db()
@app.route('/trajectoire', methods=['POST'])
def trajectoire():
    data = request.get_json()
    
    if not data or 'steps' not in data:
        return "Invalid trajectory data", 400
    
    conn = sqlite3.connect('moteurs.db')
    cursor = conn.cursor()
    
    # Log the trajectory request
    log_action("Trajectory execution started", str(data['steps']))
    
    # Execute each step in the trajectory
    for step in data['steps']:
        # Handle both simple strings and objects with duration
        action = step if isinstance(step, str) else step['action']
        duration = 0.5 if isinstance(step, str) else step['duration']/1000
        
        if action == "enAvant":
            enAvant()
        elif action == "enArriere":
            enArriere()
        elif action == "Gauche" or action == "gauche":
            gauche()
        elif action == "Droite" or action == "droite":
            droite()
        else:
            stop()
        
        # Store the step in the database
        cursor.execute("INSERT INTO moteurs (isLeftPressed, isRightPressed, isForwardPressed, isReversePressed) VALUES (?, ?, ?, ?)",
                       (int(action == "Gauche" or action == "gauche"), 
                        int(action == "Droite" or action == "droite"), 
                        int(action == "enAvant"), 
                        int(action == "enArriere")))
        
        # Wait for the specified duration
        time.sleep(duration)
    
    # Stop the motors when trajectory is completed
    stop()
    
    conn.commit()
    conn.close()
    log_action("Trajectory execution completed")
    return "Trajectory executed successfully"
@app.route('/')
def index():
    return render_template('index.html')
# === Flask Routes ===
@app.route('/moteurs', methods=['POST'])
def post_moteurs():
    moteurs = request.get_json()
    print("Moteurs received:", moteurs)  
   # Now make sure your motor logic uses these exact keys!
    if moteurs["isForwardPressed"]:
        enAvant() 
    elif moteurs["isReversePressed"]:
        enArriere()
    elif moteurs["isLeftPressed"]:
        gauche()
    elif moteurs["isRightPressed"]:
        droite()
    else :
        stop()
   
    return "Command received"
   

@app.route('/camera')
def get_camera():
   ret, frame = cap.read()
   if not ret:
    return "Camera error", 500

   _, buffer = cv2.imencode('.jpg', frame)
   response = flask.make_response(buffer.tobytes())
   response.headers.set('Content-Type', 'image/jpeg')
   return response

    # === OpenCV Ball Detection Thread ===
def detect_red_ball(frame):
   lower_green = np.array([10, 250, 100])
   upper_green = np.array([50, 120, 0])
   hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
   mask = cv2.inRange(hsv, lower_green, upper_green)
   contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

   if contours:
       largest = max(contours, key=cv2.contourArea)
       (x, y), radius = cv2.minEnclosingCircle(largest)
       return (int(x), int(y)), int(radius)
   return None, None

def open_cv_loop():
    previous = "nothing"
    lostCount = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        center, radius = detect_red_ball(frame)
        if center:
            cv2.circle(frame, center, radius, (0, 255, 0), 2)
            if center[0] > 300:
                droite()
                previous = "droite"
            elif center[0] < 200:
                gauche()
                previous = "gauche"
            else:
                enAvant()
            lostCount = 0
        elif previous == "gauche" and lostCount < 100:
            droite()
            lostCount += 1
        elif previous == "droite" and lostCount < 100:
            gauche()
            lostCount += 1
        else:
            stop()
        time.sleep(0.05)

# === Camera Capture ===
cap = cv2.VideoCapture(0)

# === Graceful Shutdown ===
def cleanup():
    print("Cleaning up...")
    stop()
    GPIO.cleanup()
    cap.release()
    cv2.destroyAllWindows()

atexit.register(cleanup)
# === Start Flask + OpenCV in Thread ===
if __name__ == '__main__':
    thread = threading.Thread(target=open_cv_loop, daemon=True)
    thread.start()
    app.run(host='0.0.0.0', port=5000, debug=True)
    
