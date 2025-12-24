# Lyria Studio V2: Hybrid Audio Architecture

## Overview
This repository hosts the V2 architecture for the Athena Audio Engine. It transitions from a monolithic script to a Client-Server architecture, decoupling the generation logic (Python/FastAPI) from the user experience (React/Next.js).

This hybrid approach allows for a "Consumer-Grade" chat interface for rapid ideation, while retaining a "Pro-Grade" studio environment for granular DSP editing.

DEMO: https://youtu.be/lGW3Mi-l6m0

---

## Quick Start (Execution Guide)
### QUICK ACCESS LINK (Live Version)
The public partial/client UI (No advanced settings) is deployed on Vercel and accessible here:
**https://lyria-studio.vercel.app/**

# Local
To run the full suite, you need 3 separate terminals running concurrently.

### Terminal 1: The Backend Core (API)
Handles the connection to Vertex AI and exposes the generation endpoints.

cd backend
# Ensure your environment is active (e.g., conda activate stitch_test)
uvicorn api:app --reload --port 8000

### Terminal 2: The Frontend Client (UI)
Launches the Next.js Chat Interface (Consumer View).

cd frontend
npm run dev
# Running on http://localhost:3000

### Terminal 3: The Advanced Studio (DSP Engine)
Launches the Deep Editor for segmentation and stitching.

cd backend
streamlit run studio.py --server.port 8501

**Usage Flow:**
1. Open http://localhost:3000
2. Generate a track using the Chat UI.
3. Click "Open in Studio" to transfer the asset to the advanced editor.

---

## Installation & Setup

### Prerequisites
* Python 3.10+ (Recommended: Anaconda/Miniconda)
* Node.js 18+ (LTS Version)
* FFmpeg installed and added to system PATH.

### 1. Backend Setup
Initialize the Python environment for signal processing and API management.

cd backend
pip install -r requirements.txt

**Environment Variables Required:**
- `PROJECT_ID`: Your Google Cloud Project ID
- `LOCATION`: Vertex AI region (default: `us-central1`)
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to your service account JSON key file

Example `.env` file:
```
PROJECT_ID=your-gcp-project-id
LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

**Note:** The backend now uses Vertex AI SDK with service account authentication. Ensure your service account has the necessary permissions to access the Lyria-002 model.

### 2. Frontend Setup
Install the React dependencies and UI component libraries.

cd frontend
npm install

---

## System Architecture & File Roles

### Backend Layer (/backend)
Contains the proprietary logic for audio manipulation and external model orchestration.

* api.py
    * Role: REST Interface & Entry Point.
    * Function: Handles CORS policies and routes JSON requests from the Frontend to the generation engine. Exposes specific headers for cross-origin file handling.
* studio.py
    * Role: Advanced DSP Visualizer.
    * Function: A specialized environment for non-linear editing. Handles the "Session State" when importing assets from the chat and executes the final rendering pipeline.
* audio_utils.py
    * Role: Signal Processing Middleware.
    * Function: Contains the core algorithms for "Smart Stitching," crossfade calculation, and temporary file management. This is the DSP engine of the project.
* lyria_generator.py
    * Role: Model Gateway.
    * Function: Manages the Vertex AI REST API connection to the Google Lyria-002 model, handling batch generation and audio file output.

### Frontend Layer (/frontend)
A modern, responsive client built with Next.js 14 (App Router).

* src/app/page.tsx
    * Role: Client State Manager.
    * Function: Manages the chat history, audio playback states, and the logic that constructs the deep links to open the Studio with the correct context.
* src/app/layout.tsx
    * Role: Global Context.
    * Function: Handles font optimization and suppresses hydration warnings for browser extensions compatibility.

---

## Notes for Deployment
* Storage: Currently uses local ephemeral storage for low-latency processing during the MVP phase. Production migration would require an S3/GCS bucket implementation.
* Security: The API currently allows all origins for development ease. This must be restricted to the specific frontend domain in production.
EOF
