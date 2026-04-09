from flask import Flask, render_template, Response, jsonify
import cv2
import queue
import threading
import time
from inference_sdk import InferenceHTTPClient
import serial

# UART
ser = serial.Serial('COM4', 115200, timeout=1)

def send_uart(angle):
    try:
        ser.write((str(angle) + '\n').encode())
    except:
        pass

app = Flask(__name__)

frame_queue = queue.Queue(maxsize=10)

latest_class = "Waiting..."
trigger_time = None
waiting = False
clear_time = None  # for auto clear

def run_system():
    global latest_class, trigger_time, waiting, clear_time

    client = InferenceHTTPClient(
        api_url="https://serverless.roboflow.com",
        api_key="gmpLseyA9K6m2TF77Y3Z"
    )

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Camera not opened!")
        return

    print("System started...")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # UART read
        if ser.in_waiting > 0:
            data = ser.readline().decode(errors='ignore').strip()

            if ("Detected" in data or "tected" in data) and not waiting:
                print("Trigger received")
                trigger_time = time.time()
                waiting = True

        #  Delay (non-blocking)
        if waiting and (time.time() - trigger_time >= 3):
            print("Capturing...")

            filename = "capture.jpg"
            cv2.imwrite(filename, frame)

            result = client.run_workflow(
                workspace_name="karthickraja-2ublz",
                workflow_id="detect-count-and-visualize-6",
                images={"image": filename},
                use_cache=True
            )

            predictions = []
            for item in result:
                preds = item.get("predictions", {}).get("predictions", [])
                for pred in preds:
                    if pred.get("confidence", 0) >= 0.50:
                        predictions.append(pred["class"])

            if predictions:
                raw_lower = predictions[0].lower().strip()
            else:
                raw_lower = None

            # Decision Logic
            if raw_lower == "cotton":
                latest_class = "Cotton Waste"
                send_uart(180)

            elif raw_lower == "saline":
                latest_class = "Saline Waste"
                send_uart(90)

            elif raw_lower == "syringe n glass":
                latest_class = "Syringe Waste"
                send_uart(180)

            elif raw_lower == "ampoule":
                latest_class = "Ampoule Waste"
                send_uart(0)

            elif raw_lower == "iv":
                latest_class = "IV Waste"
                send_uart(90)

            elif raw_lower is None:
                latest_class = "No Waste Detected"
                send_uart(0)

            else:
                latest_class = "General Waste"
                send_uart(0)

            print("Detected:", latest_class)

            #  Start clear timer
            clear_time = time.time()

            waiting = False
            trigger_time = None

        #  Auto clear after 2 sec
        if clear_time is not None and (time.time() - clear_time >= 2):
            latest_class = "Waiting..."
            clear_time = None

        # Frame → queue (for web UI)
        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            if frame_queue.full():
                frame_queue.get()
            frame_queue.put(buffer.tobytes())


def gen_frames():
    while True:
        try:
            frame = frame_queue.get(timeout=2)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        except:
            pass


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/latest_detection')
def get_latest():
    return jsonify({"detected_class": latest_class})


if __name__ == '__main__':
    threading.Thread(target=run_system, daemon=True).start()

    print("Server running at http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
