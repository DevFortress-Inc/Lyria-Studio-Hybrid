import os

from dotenv import load_dotenv
load_dotenv()

import json
import base64
import wave
import asyncio
import contextlib
from typing import List, Dict
from websockets.asyncio.client import connect

MODEL = 'models/lyria-realtime-exp'
HOST = 'generativelanguage.googleapis.com'
API_KEY = os.environ.get("GOOGLE_API_KEY")

URI = f'wss://{HOST}/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateMusic?key={API_KEY}'


@contextlib.contextmanager
def wave_file(filename, channels=2, rate=24000, sample_width=2):
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        yield wf


async def generate_music_file(
        weighted_prompts: List[Dict[str, any]],
        duration_seconds: int,
        bpm: int,
        guidance: float,
        density: float,
        output_filename: str = "temp_music.wav"
) -> str:
    if not API_KEY:
        raise ValueError("GOOGLE_API_KEY not found in environment.")
    target_duration = duration_seconds

    sample_rate = 24000
    CHANNELS = 2
    SAMPLE_WIDTH_BYTES = 2

    print(f"Connecting to Lyria...")

    try:
        async with connect(URI, additional_headers={'Content-Type': 'application/json'}) as ws:
            await ws.send(json.dumps({'setup': {"model": MODEL}}))
            raw_setup = await ws.recv()
            setup_response = json.loads(raw_setup)

            music_config = {
                'music_generation_config': {
                    'bpm': str(bpm),
                    'guidance': guidance,
                    'density': density
                }
            }

            await ws.send(json.dumps({"client_content": {"weighted_prompts": weighted_prompts}}))
            await ws.send(json.dumps(music_config))
            await ws.send(json.dumps({'playback_control': 'PLAY'}))

            bytes_per_second = sample_rate * CHANNELS * SAMPLE_WIDTH_BYTES
            target_total_bytes = bytes_per_second * target_duration
            total_bytes_written = 0

            with wave_file(output_filename, rate=sample_rate, channels=CHANNELS,
                           sample_width=SAMPLE_WIDTH_BYTES) as wav:
                async for raw_response in ws:
                    response = json.loads(raw_response)
                    server_content = response.pop('serverContent', None)

                    if server_content:
                        audio_chunk = server_content.pop('audioChunks', None)
                        if audio_chunk:
                            b64data = audio_chunk[0]
                            pcm_data = base64.b64decode(b64data['data'])
                            wav.writeframes(pcm_data)
                            total_bytes_written += len(pcm_data)

                            if total_bytes_written >= target_total_bytes:
                                await ws.send(json.dumps({'playback_control': 'STOP'}))
                                break

            return output_filename

    except Exception as e:
        print(f"API Error: {e}")
        return None