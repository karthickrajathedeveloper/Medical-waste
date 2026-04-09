 from inference_sdk import InferenceHTTPClient
import serial
import time
import cv2

ser = serial.Serial('COM4', 115200, timeout=1)
time.sleep(2)

client = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="gmpLseyA9K6m2TF77Y3Z"
)

print("Listening from ESP32...\n")

def send_uart(angle):
    try:
        ser.write((str(angle) + '\n').encode())
        print("Sent to ESP32:", angle)
    except:
        print("UART send failed")

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Camera not opened!")
    exit()

image_count = 0

while True:
    ret, frame = cap.read()

    if ret:
        cv2.imshow("Camera", frame)

    if ser.in_waiting > 0:
        data = ser.readline().decode('utf-8', errors='ignore').strip()

        if data:
            print("ESP32:", data)

            if "Detected" in data or "tected" in data:
                print("Object detected, waiting 3 seconds...")

                # Delay before capture
                time.sleep(3)

                # Take fresh frame after delay
                ret, frame = cap.read()

                if ret:
                    filename = f"captured_{image_count}.jpg"
                    cv2.imwrite(filename, frame)
                    print("Image Saved:", filename)

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

                    print("Final Output:", latest_class)

                    # image_count += 1

                    # avoid multiple triggers
                    time.sleep(2)

                else:
                    print("Failed to capture image")

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
ser.close()
