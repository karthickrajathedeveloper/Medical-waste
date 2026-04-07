from flask import Flask, render_template, Response, jsonify
import cv2
import queue
import threading
import time
from collections import Counter
from inference_sdk import InferenceHTTPClient
from inference_sdk.webrtc import WebcamSource, StreamConfig
import serial


ser = serial.Serial('COM67', 115200, timeout=1)

def send_uart(angle):
    ser.write((str(angle) + '\n').encode())

app = Flask(__name__)

# To hold the latest JPEG frame
frame_queue = queue.Queue(maxsize=10)
# To hold the latest medical waste detected
latest_class = "Waiting for data..."

# --- Roboflow WebRTC Background Thread ---
def run_roboflow():
    global latest_class
    try:
        # Initialize client
        client = InferenceHTTPClient.init(
            api_url="https://serverless.roboflow.com",
            api_key="gmpLseyA9K6m2TF77Y3Z"
        )
        
        # Configure video source (webcam)
        source = WebcamSource(resolution=(1280, 720))
        
        # Configure streaming options
        config = StreamConfig(
            stream_output=["output_image"],  # Get video back with annotations
            data_output=["predictions"],     # Get prediction data
            processing_timeout=3600,         # 60 minutes
            requested_plan="webrtc-gpu-medium",
            requested_region="us"
        )
        
        # Create streaming session
        session = client.webrtc.stream(
            source=source,
            workflow="detect-count-and-visualize-6",
            workspace="karthickraja-2ublz",
            image_input="image",
            config=config
        )
        
        start_time = time.time()
        predictions_counter = Counter()

        # Handle prediction data
        @session.on_data()
        def on_data(data, metadata):
            nonlocal start_time, predictions_counter
            global latest_class
            
            predictions_list = data.get("predictions", {}).get("predictions", [])
            for pred in predictions_list:
                if "class" in pred and pred.get("confidence", 0) >= 0.50:
                    predictions_counter[pred['class']] += 1

            current_time = time.time()
            if current_time - start_time >= 5: # 5 seconds window
                if predictions_counter:
                    # Get the most common raw class name
                    most_common_raw = predictions_counter.most_common(1)[0][0]
                    raw_lower = most_common_raw.lower().strip()
                    
                    # Apply user's custom naming rules
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
                else:
                    latest_class = "No Waste Detected"
                
                # Reset counter and timer
                predictions_counter.clear()
                start_time = current_time

        frame_count = 0
        # Handle incoming video frames
        @session.on_frame
        def show_frame(frame, metadata):
            nonlocal frame_count
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"[DEBUG] WebRTC streaming correctly... received {frame_count} frames")
            
            # frame is a numpy array returned by Roboflow WebRTC
            # Encode it as JPEG to stream over HTTP
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                # Put in queue, discard oldest if full
                if frame_queue.full():
                    try:
                        frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                frame_queue.put(buffer.tobytes())

        # Start the session (Blocks this thread)
        print("Starting AI Video Stream...")
        session.run()
        
    except Exception as e:
        print(f"Error in Roboflow thread: {e}")

# --- Flask Routes ---
@app.route('/')
def index():
    return render_template('index.html')

def gen_frames():
    """Video streaming generator function."""
    while True:
        try:
            frame_bytes = frame_queue.get(timeout=2.0)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        except queue.Empty:
            pass

@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/latest_detection')
def get_latest():
    """API endpoint for frontend to fetch the latest detected object."""
    return jsonify({"detected_class": latest_class})

if __name__ == '__main__':
    # Start AI model in a background thread
    threading.Thread(target=run_roboflow, daemon=True).start()
    
    # Run Web Server on 0.0.0.0 to allow access from local IP (WiFi network)
    print("=============================================")
    print("Server started on network. Access it via:")
    print("http://[Your-Local-IP]:5000 (e.g. 192.168.1.X:5000)")
    print("=============================================")
    app.run(host='0.0.0.0', port=5000, debug=False)
