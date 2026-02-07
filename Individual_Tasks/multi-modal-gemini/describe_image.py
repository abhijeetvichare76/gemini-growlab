import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables from .env, overriding any existing ones
load_dotenv(override=True)

# Explicitly set the Google Application Credentials environment variable
# This ensures that the client picks up the correct service account JSON
creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if creds_path:
    # If the path is relative, make it absolute based on the project root
    if not os.path.isabs(creds_path):
        creds_path = os.path.join(os.getcwd(), creds_path)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

# Initialize the Vertex AI client
project_id = os.getenv("GCP_PROJECT_ID")
location = os.getenv("GCP_LOCATION", "global")

if not project_id:
    raise ValueError("GCP_PROJECT_ID not found in .env file")

# Use vertexai=True to use Vertex AI with the specified credentials
# location='global' is required for the preview model
client = genai.Client(
    vertexai=True, 
    project=project_id, 
    location=location
)

def analyze_image(image_path, prompt):
    # Check if the image path is absolute, if not make it relative to the script's directory
    if not os.path.isabs(image_path):
        # Assuming we are running from the root of the project
        image_path = os.path.join(os.getcwd(), image_path)

    if not os.path.exists(image_path):
        print(f"Error: Image file not found at {image_path}")
        return

    # Read the image file as bytes
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    # Create the multimodal request
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/jpeg",
                ),
                prompt
            ]
        )

        print("-" * 30)
        print(f"Image: {image_path}")
        print(f"Prompt: {prompt}")
        print(f"Response: {response.text}")
        print("-" * 30)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Path to the specific image requested by the user
    target_image = r"Individual_Tasks\pixel7control\test_records\PXL_20260124_213757712.jpg"
    
    # Description prompt
    prompt_text = "Please describe this image in detail."
    
    analyze_image(target_image, prompt_text)
