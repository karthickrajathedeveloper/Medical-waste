

# 1. Import the library
from inference_sdk import InferenceHTTPClient

# 2. Connect to your workflow
client = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="gmpLseyA9K6m2TF77Y3Z"
)

# 3. Run your workflow on an image
result = client.run_workflow(
    workspace_name="karthickraja-2ublz",
    workflow_id="detect-count-and-visualize-6",
    images={
        "image": "C:/Users/Admin/Desktop/M/syringes-1.jpg" # Path to your image file
    },
    use_cache=True # Speeds up repeated requests
)

# 4. Get your results
#print(result)

# 5. Extract the Class
for item in result:
    for pred in item['predictions']['predictions']:
        print(pred['class'])



