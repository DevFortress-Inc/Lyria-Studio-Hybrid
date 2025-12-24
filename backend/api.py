import os
import time
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import lyria_generator
import audio_utils

# Load environment variables from .env file
load_dotenv()

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
    duration: int = 15
    bpm: int = 90
    density: float = 0.5


@app.get("/")
def health_check():
    return {"status": "Lyria Backend is running 🚀"}


@app.post("/generate")
async def generate_audio(req: GenerateRequest):
    try:
        filename = f"track_{int(time.time())}_{uuid.uuid4().hex[:4]}.wav"
        print(f"--> Generando: {req.prompt}")

        result_path = await lyria_generator.generate_music_file(
            prompt=req.prompt,
            duration_seconds=req.duration,
            bpm=req.bpm,
            guidance=7.0,
            density=req.density,
            output_filename=filename
        )

        if not result_path:
            raise HTTPException(status_code=500, detail="Error en Lyria Generator")

        return FileResponse(path=result_path, media_type="audio/wav", filename=filename)

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))