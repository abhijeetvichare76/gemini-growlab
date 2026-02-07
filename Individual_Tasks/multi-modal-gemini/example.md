2. The Python Implementation
Create a new Python file (e.g., gemini_test.py) and use the following code. This script initializes the client, loads a local image, and sends it along with a text prompt to the Gemini 3 Flash model.

```python
import os
from google import genai
from google.genai import types

# Initialize the client
# If you don't want to set an environment variable, pass it directly:
# client = genai.Client(api_key="YOUR_API_KEY")
client = genai.Client(api_key='YOUR_API_KEY') 

def analyze_image(image_path, prompt):
    # Read the image file as bytes
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    # Create the multimodal request
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[
            types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg", # Change to image/png if applicable
            ),
            prompt
        ]
    )

    print("-" * 30)
    print(f"Prompt: {prompt}")
    print(f"Response: {response.text}")
    print("-" * 30)

# Usage
analyze_image("path/to/your/image.jpg", "Identify the main objects in this image and describe their layout.")