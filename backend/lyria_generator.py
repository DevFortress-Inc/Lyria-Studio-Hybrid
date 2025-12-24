import os
from dotenv import load_dotenv
load_dotenv()

import base64
from google.cloud import aiplatform
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value

MODEL_ID = 'lyria-002'
PROJECT_ID = os.environ.get("PROJECT_ID")
LOCATION = os.environ.get("LOCATION", "us-central1")
CREDENTIALS_PATH = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")


async def generate_music_file(
        prompt: str,
        negative_prompt: str = "",
        seed: int = None,
        output_filename: str = "temp_music.wav"
) -> str:
    """Generates high-fidelity audio using the lyria-002 batch model."""
    
    # Validate required environment variables
    if not PROJECT_ID:
        raise ValueError("PROJECT_ID not found in environment.")
    if not CREDENTIALS_PATH:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not found in environment.")
    if not os.path.exists(CREDENTIALS_PATH):
        raise ValueError(f"Credentials file not found at {CREDENTIALS_PATH}")
    
    print(f"Requesting music generation from {MODEL_ID}...")
    
    try:
        # Initialize the Vertex AI client
        aiplatform.init(project=PROJECT_ID, location=LOCATION)

        # The endpoint for Lyria-002
        endpoint_path = f"projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_ID}"
        
        # Prepare the instance (the prompt data)
        instance_dict = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
        }
        if seed is not None:
            instance_dict["seed"] = seed

        # Convert dict to a Protobuf Value object
        instance = json_format.ParseDict(instance_dict, Value())
        instances = [instance]

        # Parameters: sample_count can be 1-4 (Note: cannot use with seed)
        parameters_dict = {}
        if seed is None:
            parameters_dict["sample_count"] = 1
            
        parameters = json_format.ParseDict(parameters_dict, Value())

        # Create the prediction client
        client_options = {"api_endpoint": f"{LOCATION}-aiplatform.googleapis.com"}
        predict_client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)

        # Make the prediction request
        response = predict_client.predict(
            endpoint=endpoint_path, 
            instances=instances, 
            parameters=parameters
        )

        # Handle the response
        for i, prediction in enumerate(response.predictions):
            # Lyria returns audioContent as a base64 encoded string
            audio_data_b64 = prediction.get("audioContent")
            
            if audio_data_b64:
                # Decode and save the file
                audio_bytes = base64.b64decode(audio_data_b64)
                
                # If generating multiple samples, append index to filename
                final_name = f"{i}_{output_filename}" if len(response.predictions) > 1 else output_filename
                
                with open(final_name, "wb") as f:
                    f.write(audio_bytes)
                
                print(f"Success! Music saved to {final_name}")
                return final_name
            else:
                raise ValueError("No audioContent in prediction response")
        
        raise ValueError("No predictions returned from model")

    except Exception as e:
        print(f"API Error: {e}")
        return None
