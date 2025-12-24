import os
import time
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import lyria_generator
import audio_utils

app = FastAPI(title="Lyria Audio API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
expose_headers=["Content-Disposition"]
)


class GenerateRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = ""
    seed: Optional[int] = None


@app.get("/")
def health_check():
    return {"status": "Lyria Backend is running 🚀"}


@app.post("/generate")
async def generate_audio(req: GenerateRequest):
    try:
        filename = f"track_{int(time.time())}_{uuid.uuid4().hex[:4]}.wav"
        
        print(f"--> Generating: {req.prompt}")

        result_path = await lyria_generator.generate_music_file(
            prompt=req.prompt,
            negative_prompt=req.negative_prompt,
            seed=req.seed,
            output_filename=filename
        )

        if not result_path:
            raise HTTPException(status_code=500, detail="Error in Lyria Generator")

        response = FileResponse(path=result_path, media_type="audio/wav", filename=filename)
        return response

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))