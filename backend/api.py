import os
import time
import uuid
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import lyria_generator
import audio_utils
import prompt_analyzer

app = FastAPI(title="Lyria Audio API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
expose_headers=["Content-Disposition"]
)


class WeightedPrompt(BaseModel):
    text: str
    weight: float


class GenerateRequest(BaseModel):
    prompt: Optional[str] = None
    weighted_prompts: Optional[List[WeightedPrompt]] = None
    duration: int = 15
    bpm: int = 90
    guidance: float = 7.0
    density: float = 0.5


class PreviousTrackContext(BaseModel):
    weighted_prompts: List[WeightedPrompt]
    parameters: Optional[dict] = None

class AnalyzePromptRequest(BaseModel):
    prompt: str
    previous_context: Optional[PreviousTrackContext] = None


@app.get("/")
def health_check():
    return {"status": "Lyria Backend is running 🚀"}


@app.post("/analyze-prompt")
async def analyze_prompt(req: AnalyzePromptRequest):
    """AI-powered prompt analysis endpoint with optional previous context for edits"""
    try:
        previous_context = None
        if req.previous_context:
            previous_context = {
                "weighted_prompts": [{"text": wp.text, "weight": wp.weight} for wp in req.previous_context.weighted_prompts],
                "parameters": req.previous_context.parameters or {}
            }
        
        analysis_result = prompt_analyzer.analyze_prompt_for_weighted_components(
            req.prompt,
            previous_context=previous_context
        )
        return JSONResponse(content={
            "original_prompt": req.prompt,
            "weighted_prompts": analysis_result.get("weighted_prompts", []),
            "parameters": analysis_result.get("parameters", {
                "bpm": 90,
                "guidance": 7.0,
                "density": 0.5
            })
        })
    except ValueError as e:
        print(f"Error analyzing prompt: {e}")
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}. Please check your prompt and try again.")
    except Exception as e:
        print(f"Error analyzing prompt: {e}")
        raise HTTPException(status_code=500, detail=f"Error analyzing prompt: {str(e)}")


@app.post("/generate")
async def generate_audio(req: GenerateRequest):
    try:
        filename = f"track_{int(time.time())}_{uuid.uuid4().hex[:4]}.wav"
        
        # Handle both single prompt and weighted prompts
        if req.weighted_prompts:
            weighted_prompts_data = [{"text": wp.text, "weight": wp.weight} for wp in req.weighted_prompts]
            prompt_display = " + ".join([f"{wp.text} ({wp.weight:.2f})" for wp in req.weighted_prompts])
        elif req.prompt:
            # Fallback to single prompt
            weighted_prompts_data = [{"text": req.prompt, "weight": 1.0}]
            prompt_display = req.prompt
        else:
            raise HTTPException(status_code=400, detail="Either 'prompt' or 'weighted_prompts' must be provided")
        
        print(f"--> Generando: {prompt_display}")

        result_path = await lyria_generator.generate_music_file(
            weighted_prompts=weighted_prompts_data,
            duration_seconds=req.duration,
            bpm=req.bpm,
            guidance=req.guidance,
            density=req.density,
            output_filename=filename
        )

        if not result_path:
            raise HTTPException(status_code=500, detail="Error en Lyria Generator")

        response = FileResponse(path=result_path, media_type="audio/wav", filename=filename)
        response.headers["X-Prompt-Breakdown"] = json.dumps(weighted_prompts_data)
        return response

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))