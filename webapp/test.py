from flask import Flask, render_template, Response, jsonify
import cv2
import queue
import threading
import time
from collections import Counter
from inference_sdk import InferenceHTTPClient
from inference_sdk.webrtc import WebcamSource, StreamConfig
import serial

# ================= UART =================
ser = serial.Serial('COM67', 115200, timeout=1)

def send_uart(angle):
    ser.write((str(angle) + '\n').encode())

# 🔥 Trigger flag
trigger_received = False

# ================= UART LISTENER =================
def uart_listener():
    global trigger_received

    while True:
        if ser.in_waiting:
            data = ser.readline().decode().strip()
            print("UART Received:", data)

            if data == "IR":
                print("✅ IR Trigger Received")
                trigger_received = True

# ================= FLASK =================
app = Flask(__name__)

frame_queue = queue.Queue(maxsize=10)
latest_class = "Waiting for data..."

# ================= AI THREAD =================
def run_roboflow():
    global latest_class, trigger_received

    try:
        client = InferenceHTTPClient.init(
            api_url="https://serverless.roboflow.com",
            api_key="gmpLseyA9K6m2TF77Y3Z"
        )

        source = WebcamSource(resolution=(1280, 720))

        config = StreamConfig(
            stream_output=["output_image"],
            data_output=["predictions"],
            processing_timeout=3600,
            requested_plan="webrtc-gpu-medium",
            requested_region="us"
        )

        session = client.webrtc.stream(
            source=source,
            workflow="detect-count-and-visualize-6",
            workspace="karthickraja-2ublz",
            image_input="image",
            config=config
        )

        start_time = time.time()
        predictions_counter = Counter()

        @session.on_data()
        def on_data(data, metadata):
            global latest_class, trigger_received
            nonlocal start_time, predictions_counter

            # ❌ Ignore detection until IR trigger
            if not trigger_received:
                return

            predictions_list = data.get("predictions", {}).get("predictions", [])

            for pred in predictions_list:
                if "class" in pred and pred.get("confidence", 0) >= 0.50:
                    predictions_counter[pred['class']] += 1

            current_time = time.time()

            if current_time - start_time >= 5:
                if predictions_counter:

                    most_common_raw = predictions_counter.most_common(1)[0][0]
                    raw_lower = most_common_raw.lower().strip()

                    if raw_lower == "cotton":
                        latest_class = "Cotton Waste"
                        send_uart(0)

                    elif raw_lower == "saline":
                        latest_class = "Saline Waste"
                        send_uart(90)

                    elif raw_lower == "syringe n glass":
                        latest_class = "Syringe Waste"
                        send_uart(180)

                    elif raw_lower == "ampoule":
                        latest_class = "Ampoule Waste"
                        send_uart(90)

                    elif raw_lower == "iv":
                        latest_class = "IV Waste"
                        send_uart(180)

                    else:
                        latest_class = "General Waste"
                        send_uart(0)

                    print("✅ Sent Angle for:", latest_class)

                else:
                    latest_class = "No Waste Detected"

                # 🔥 Reset for next IR trigger
                trigger_received = False

                predictions_counter.clear()
                start_time = current_time

        frame_count = 0

        @session.on_frame
        def show_frame(frame, metadata):
            nonlocal frame_count
            frame_count += 1

            if frame_count % 30 == 0:
                print(f"[DEBUG] Streaming... {frame_count} frames")

            ret, buffer = cv2.imencode('.jpg', frame)

            if ret:
                if frame_queue.full():
                    try:
                        frame_queue.get_nowait()
                    except queue.Empty:
                        pass

                frame_queue.put(buffer.tobytes())

        print("🚀 AI Stream Started (Waiting for IR trigger...)")
        session.run()

    except Exception as e:
        print("Error:", e)

# ================= FLASK ROUTES =================
@app.route('/')
def index():
    return render_template('index.html')

def gen_frames():
    while True:
        try:
            frame = frame_queue.get(timeout=2.0)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        except queue.Empty:
            pass

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/latest_detection')
def get_latest():
    return jsonify({"detected_class": latest_class})

# ================= MAIN =================
if __name__ == '__main__':
    print("====================================")
    print("Waiting for ESP32 IR Trigger...")
    print("====================================")

    threading.Thread(target=uart_listener, daemon=True).start()
    threading.Thread(target=run_roboflow, daemon=True).start()

    app.run(host='0.0.0.0', port=5000, debug=False)
