import cv2
import time
from collections import Counter
from inference_sdk import InferenceHTTPClient
from inference_sdk.webrtc import WebcamSource, StreamConfig, VideoMetadata

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
    data_output=["count_objects","predictions"],      # Get prediction data via datachannel,
    processing_timeout=3600,              # 60 minutes,
    requested_plan="webrtc-gpu-medium",  # Options: webrtc-gpu-small, webrtc-gpu-medium, webrtc-gpu-large
    requested_region="us"                # Options: us, eu, ap
)

# Create streaming session
session = client.webrtc.stream(
    source=source,
    workflow="detect-count-and-visualize-6",
    workspace="karthickraja-2ublz",
    image_input="image",
    config=config
)

# Handle incoming video frames
@session.on_frame
def show_frame(frame, metadata):
    cv2.imshow("Webcam Feed", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        session.close()

# Global variables to track AI outputs over time
start_time = time.time()
predictions_counter = Counter()

# Handle prediction data via datachannel
@session.on_data()
def on_data(data: dict, metadata: VideoMetadata):
    global start_time, predictions_counter

    # Extract prediction list
    predictions_list = data.get("predictions", {}).get("predictions", [])
    
    # Track detected objects passing the confidence threshold
    for pred in predictions_list:
        if "class" in pred and pred.get("confidence", 0) >= 0.50:
            predictions_counter[pred['class']] += 1

    # Check if 10 seconds have passed
    current_time = time.time()
    if current_time - start_time >= 10:
        if predictions_counter:
            # Find the most commonly detected item in the last 10 seconds
            most_common_class, count = predictions_counter.most_common(1)[0]
            print(f"\n=======================================================")
            print(f"[RESULT] Most Confident Object (over 10s): {most_common_class}")
            print(f"=======================================================\n")
        else:
            print("\n[INFO] No confident objects detected in the last 10s.\n")
        
        # Reset the timer and counter for the next 10 seconds
        predictions_counter.clear()
        start_time = current_time

# Run the session (blocks until closed)
session.run()

