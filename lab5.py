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
@app.route('/start_ball_following', methods=['POST'])
def start_ball_following():
    global ball_following_thread
    if ball_following_thread is None or not ball_following_thread.is_alive():
        ball_following_thread = threading.Thread(target=ball_following, daemon=True)
        ball_following_thread.start()
        return "Ball following started", 200
    return "Ball following is already running", 400

@app.route('/stop_ball_following', methods=['POST'])
def stop_ball_following():
    global ball_following_thread
    if ball_following_thread is not None and ball_following_thread.is_alive():
        stop()  # This stops the motors, effectively halting the movement.
        ball_following_thread = None  # Reset the thread reference
        return "Ball following stopped", 200
    return "Ball following is not running", 400

# Ball detection and following logic
def filter_contours(contours):
    best_circle = None
    best_score = 0

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 400:
            continue

        ((cx, cy), radius) = cv2.minEnclosingCircle(contour)
        if radius < 10 or radius > 100:
            continue

        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            continue

        circularity = 4 * np.pi * area / (perimeter * perimeter)
        score = area * (circularity ** 1.5)

        if score > best_score:
            best_score = score
            best_circle = (int(cx), int(cy), int(radius))

    return [best_circle] if best_circle else []

def detect_orange_ball_on_frame(frame):
    lower_orange = np.array([0, 68, 160])
    upper_orange = np.array([20, 255, 255])

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask_orange = cv2.inRange(hsv, lower_orange, upper_orange)

    lower_skin = np.array([0, 20, 60])
    upper_skin = np.array([20, 170, 255])
    mask_skin = cv2.inRange(hsv, lower_skin, upper_skin)
    mask = cv2.bitwise_and(mask_orange, cv2.bitwise_not(mask_skin))

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.GaussianBlur(mask, (5, 5), 0)

    contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    circles = filter_contours(contours)
    return circles

def ball_following():
    global previous, lostCount

    cap = cv2.VideoCapture(0)
    FRAME_CENTER_X = 320
    CENTER_THRESHOLD = 50

    previous = "nothing"
    lostCount = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        circles = detect_orange_ball_on_frame(frame)

        if circles:
            x, y, radius = circles[0]
            cv2.circle(frame, (x, y), radius, (0, 255, 0), 2)
            print(f"Ball center: {x},{y} radius: {radius}")
            lostCount = 0

            if x > FRAME_CENTER_X + CENTER_THRESHOLD:
                print("La balle est à droite → tourne à droite")
                droite()
                time.sleep(0.5) # wait for the camera to adjust to the new position before continuing
                previous = "droite"
            elif x < FRAME_CENTER_X - CENTER_THRESHOLD:
                print("La balle est à gauche → tourne à gauche")
                gauche()
                time.sleep(0.5) # wait for the camera to adjust to the new position before continuing
                previous = "gauche"
            else:
                print("Balle centrée → avance")
                enAvant()
                time.sleep(0.5) # wait for the camera to adjust to the new position before continuing
        else:
            if previous == "gauche" and lostCount < 100:
                print("Balle perdue, tourne à droite pour retrouver")
                droite()
                time.sleep(0.5) # wait for the camera to adjust to the new position before continuing
                lostCount += 1
            elif previous == "droite" and lostCount < 100:
                print("Balle perdue, tourne à gauche pour retrouver")
                gauche()
                time.sleep(0.5) # wait for the camera to adjust to the new position before continuing
                lostCount += 1
            else:
                print("Impossible de retrouver, stop")
                stop()

        cv2.imshow('Ball Following', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    stop()
    cap.release()
    cv2.destroyAllWindows()

# === Graceful Shutdown ===
def cleanup():
    print("Cleaning up...")
    stop()
    GPIO.cleanup()
    try:
        conn = sqlite3.connect('logging.db')
        conn.close()
    except:
        pass

atexit.register(cleanup)
# === Graceful Shutdown ===
def cleanup():
    print("Cleaning up...")
    stop()
    GPIO.cleanup()
    cv2.destroyAllWindows()

atexit.register(cleanup)
# === Start Flask + OpenCV in Thread ===
if __name__ == '__main__':
    thread = threading.Thread(target=open_cv_loop, daemon=True)
    thread.start()
    app.run(host='0.0.0.0', port=5000, debug=True)
    
