import os
import json
import re
from typing import List, Dict, Optional

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

API_KEY = os.environ.get("GOOGLE_API_KEY")

# Configure Gemini if available
if API_KEY and GEMINI_AVAILABLE:
    try:
        genai.configure(api_key=API_KEY)
    except Exception as e:
        print(f"Warning: Could not configure Gemini: {e}")
        GEMINI_AVAILABLE = False


def analyze_prompt_for_weighted_components(
    prompt: str,
    previous_context: Optional[Dict[str, any]] = None
) -> Dict[str, any]:
    """
    Uses Gemini to intelligently break down a music prompt into weighted components
    and extract/infer BPM, guidance, and density parameters.
    
    If previous_context is provided, treats the prompt as an edit instruction
    and merges it with the previous track's components.
    
    Returns a dict with 'weighted_prompts' and 'parameters' (bpm, guidance, density)
    """
    if not API_KEY or not GEMINI_AVAILABLE:
        raise ValueError("Gemini AI is not available. Please check GOOGLE_API_KEY environment variable.")
    
    # Detect if this is an edit instruction
    # If previous context exists, check if prompt looks like an edit
    is_edit = False
    if previous_context:
        edit_keywords = ["add", "remove", "more", "less", "increase", "decrease", "change", "make it", "make the", "turn it", "adjust", "faster", "slower", "quieter", "louder"]
        prompt_lower = prompt.lower()
        looks_like_edit = any(keyword in prompt_lower for keyword in edit_keywords)
        
        # If context exists and it looks like an edit, treat as edit
        # Otherwise, if context exists but doesn't look like edit, treat as new track (user wants fresh start)
        is_edit = looks_like_edit
    
    try:
        model = genai.GenerativeModel('gemini-3-flash-preview')
        
        if is_edit and previous_context:
            # EDIT MODE: Modify existing track based on instruction
            previous_components = previous_context.get("weighted_prompts", [])
            previous_params = previous_context.get("parameters", {})
            
            system_prompt = f"""You are a music production assistant. The user wants to EDIT a previous track based on this instruction: "{prompt}"

PREVIOUS TRACK COMPONENTS:
{json.dumps(previous_components, indent=2)}

PREVIOUS PARAMETERS:
- BPM: {previous_params.get('bpm', 90)}
- Guidance: {previous_params.get('guidance', 7.0)}
- Density: {previous_params.get('density', 0.5)}

EDIT INSTRUCTION: "{prompt}"

YOUR TASK:
1. Understand the edit instruction (e.g., "add more piano", "remove drums", "make it faster", "less dense")
2. MODIFY the previous components based on the instruction:
   - "add [instrument]": Increase weight of existing instrument OR add new instrument
   - "remove [instrument]": Remove that component entirely
   - "more [instrument]": Increase its weight significantly
   - "less [instrument]": Decrease its weight or remove if very low
   - "make it faster/slower": Adjust BPM accordingly
   - "more/less dense": Adjust density parameter
   - "change genre to X": Update genre component
3. Keep components that aren't mentioned in the edit
4. Re-normalize weights to sum to 1.0
5. Update parameters if mentioned (BPM, guidance, density)

EDIT EXAMPLES:

Previous: [{{"text": "pop", "weight": 0.4}}, {{"text": "piano", "weight": 0.3}}, {{"text": "drums", "weight": 0.2}}, {{"text": "bass", "weight": 0.1}}]
Instruction: "add more piano"
Output: [{{"text": "pop", "weight": 0.35}}, {{"text": "piano", "weight": 0.45}}, {{"text": "drums", "weight": 0.15}}, {{"text": "bass", "weight": 0.05}}]

Previous: [{{"text": "jazz", "weight": 0.4}}, {{"text": "piano", "weight": 0.3}}, {{"text": "drums", "weight": 0.2}}, {{"text": "bass", "weight": 0.1}}]
Instruction: "remove drums"
Output: [{{"text": "jazz", "weight": 0.5}}, {{"text": "piano", "weight": 0.35}}, {{"text": "bass", "weight": 0.15}}]

Previous: [{{"text": "pop", "weight": 0.4}}, {{"text": "synthesizer", "weight": 0.3}}, {{"text": "drums", "weight": 0.2}}, {{"text": "bass", "weight": 0.1}}]
BPM: 120
Instruction: "make it faster"
Output: Same components, but BPM increased to 140-160

OUTPUT FORMAT (JSON only):
{{
  "components": [
    {{"text": "genre", "weight": 0.4}},
    {{"text": "instrument1", "weight": 0.3}},
    {{"text": "instrument2", "weight": 0.2}},
    {{"text": "instrument3", "weight": 0.1}}
  ],
  "parameters": {{
    "bpm": 120,
    "guidance": 7.0,
    "density": 0.6
  }}
}}

Apply the edit instruction now:"""
        else:
            # NEW TRACK MODE: Original behavior
            system_prompt = """You are a music production assistant. Extract the GENRE, determine appropriate INSTRUMENTS, and infer BPM, GUIDANCE, and DENSITY parameters.

CRITICAL RULES:
1. ALWAYS identify the genre/style from the prompt
2. If instruments are mentioned, use those
3. If NO instruments are mentioned, INFER appropriate instruments for that genre based on music production knowledge
4. Each component must be a SINGLE word or short phrase (e.g., "pop", "synthesizer", "drums", "bass")
5. Do NOT include the full prompt text or explanatory phrases
6. Create 3-5 components (genre + 2-4 instruments)
7. Weights must sum to 1.0
8. Genre typically gets 30-50% weight, lead instruments get higher weights
9. EXTRACT or INFER BPM, GUIDANCE, and DENSITY from the prompt

EXTRACTION PROCESS:
1. Identify the GENRE (e.g., pop, jazz, kpop, classical, orchestral, hip hop, rock, etc.)
2. Check if instruments are EXPLICITLY mentioned:
   - If YES: Use those instruments
   - If NO: Infer 2-4 typical instruments for that genre
3. Assign weights: genre (30-50%), lead instruments (20-30% each), supporting instruments (10-20% each)

REFERENCE LISTS (preferred but not exclusive - use these when appropriate, but allow other terms if mentioned):

COMMON INSTRUMENTS (prefer these when they fit - these are exact Lyria-recognized names):

Strings:
- violin, viola, cello, bass, strings, string section, viola ensemble, fiddle

Brass:
- trumpet, trombone, tuba, horn, french horn, brass section

Woodwinds:
- flute, clarinet, oboe, bassoon, saxophone, alto saxophone, bass clarinet, woodwinds

Percussion:
- drums, cymbals, timpani, snare, kick, percussion, bongos, conga drums, djembe, drumline, tabla, maracas, glockenspiel, marimba, vibraphone, steel drum, funk drums

Keys/Piano:
- piano, keyboard, synthesizer, organ, harpsichord, ragtime piano, rhodes piano, smooth pianos, clavichord, mellotron

Guitar Family:
- electric guitar, acoustic guitar, bass guitar, guitar, warm acoustic guitar, flamenco guitar, slide guitar, shredding guitar, banjo, mandolin, bouzouki, charango, pipa, shamisen, sitar, dulcimer

Bass:
- bass, precision bass, acid bass, boomy bass

Electronic/Synths:
- synthesizer, synth, electronic beats, sampler, pad, sequencer, buchla synths, dirty synths, spacey synths, synth pads, moog oscillations, tr-909 drum machine, 808 hip hop beat, metallic twang

World/Ethnic:
- didgeridoo, hang drum, kalimba, mbira, koto, lyre, ocarina, persian tar, balalaika ensemble, bagpipes, accordion, harmonica, hurdy-gurdy, harp

Vocals:
- choir, vocals, voice, vocal harmonies

COMMON GENRES/THEMES (prefer these when they fit):
- Popular: pop, rock, jazz, blues, country, folk, acoustic
- Electronic: EDM, techno, house, trance, dubstep, electronic, ambient
- Classical: classical, orchestral, cinematic, baroque, romantic
- Urban: hip hop, rap, R&B, neo soul, funk, disco
- World: Kpop, Jpop, Latin, reggae, world music, ethnic
- Styles: ballad, energetic, calm, dark, epic, emotional, mysterious, upbeat, slow, fast

RULES FOR REFERENCE LISTS:
- PREFER terms from the reference lists when they fit the prompt
- If the prompt mentions something NOT in the lists, use it (e.g., "sitar", "didgeridoo", "trap", "drill")
- If the prompt is vague, choose from reference lists
- Group similar instruments into families (e.g., "strings" not "violin, cello, bass")
- Use single-word or short phrases only

4. Extract or infer PARAMETERS:
   - BPM: Look for explicit BPM values (e.g., "120 BPM", "at 140 bpm") OR infer from genre/style:
     * Slow/ballad/ambient: 60-80
     * Jazz/blues: 80-120
     * Pop/rock: 100-140
     * EDM/hip hop: 120-160
     * Fast/energetic: 140-180
   - GUIDANCE: Look for explicit values OR infer from prompt specificity:
     * Very specific prompt with details: 8.0-9.0
     * Moderately specific: 6.0-7.5
     * Vague/creative: 4.0-6.0
     * Default: 7.0
   - DENSITY: Look for explicit values (e.g., "sparse", "dense", "minimal") OR infer from genre:
     * Minimal/ambient: 0.2-0.4
     * Pop/rock: 0.5-0.7
     * Orchestral/complex: 0.7-0.9
     * Default: 0.5

GENRE-SPECIFIC INSTRUMENT SUGGESTIONS (use reference lists above):
- Pop: synthesizer, drums, bass, electric guitar, smooth pianos
- Jazz: piano, drums, bass, saxophone, alto saxophone, rhodes piano
- Hip hop: 808 hip hop beat, drums, bass, synthesizer, tr-909 drum machine, acid bass
- Rock: electric guitar, drums, bass, shredding guitar, precision bass
- Classical/Orchestral: strings, brass, woodwinds, percussion, cello, viola ensemble
- Kpop: synthesizer, electronic beats, bass, spacey synths, synth pads
- Neo soul: piano, strings, bass, drums, rhodes piano, smooth pianos
- Electronic/EDM: buchla synths, dirty synths, spacey synths, synth pads, moog oscillations, tr-909 drum machine
- Funk: funk drums, precision bass, electric guitar, synthesizer
- World/Ethnic: Use appropriate world instruments from reference list (sitar, koto, tabla, etc.)

OUTPUT FORMAT (JSON only):
{
  "components": [
    {"text": "genre", "weight": 0.4},
    {"text": "instrument1", "weight": 0.3},
    {"text": "instrument2", "weight": 0.2},
    {"text": "instrument3", "weight": 0.1}
  ],
  "parameters": {
    "bpm": 120,
    "guidance": 7.0,
    "density": 0.6
  }
}

EXAMPLES:

Input: "i want a catchy pop song"
Output: {
  "components": [
    {"text": "pop", "weight": 0.4},
    {"text": "synthesizer", "weight": 0.3},
    {"text": "drums", "weight": 0.2},
    {"text": "bass", "weight": 0.1}
  ],
  "parameters": {
    "bpm": 120,
    "guidance": 7.0,
    "density": 0.6
  }
}

Input: "i want to develop a catchy pop song that has trumpets leading"
Output: {
  "components": [
    {"text": "pop", "weight": 0.5},
    {"text": "trumpets", "weight": 0.3},
    {"text": "synthesizer", "weight": 0.15},
    {"text": "drums", "weight": 0.05}
  ]
}

Input: "A neo soul track with piano and strings"
Output: {
  "components": [
    {"text": "neo soul", "weight": 0.4},
    {"text": "piano", "weight": 0.3},
    {"text": "strings", "weight": 0.2},
    {"text": "bass", "weight": 0.1}
  ]
}

Input: "Jazz piano with drums and bass"
Output: {
  "components": [
    {"text": "jazz", "weight": 0.35},
    {"text": "piano", "weight": 0.3},
    {"text": "drums", "weight": 0.2},
    {"text": "bass", "weight": 0.15}
  ]
}

Input: "I want to develop a theme song for an assassin family. Key Instruments: Violins, cellos, and basses. Brass: Low brass like tuba and horns. Woodwinds: Flute, bassoon, and clarinet. Percussion: Timpani and triangle. Choir/Synthesizer: Vocal choir and synth elements."
Output: {
  "components": [
    {"text": "dark orchestral", "weight": 0.4},
    {"text": "strings", "weight": 0.25},
    {"text": "brass", "weight": 0.15},
    {"text": "woodwinds", "weight": 0.1},
    {"text": "percussion", "weight": 0.1}
  ]
}

Input: "Kpop with electronic beats and synthesizer"
Output: {
  "components": [
    {"text": "kpop", "weight": 0.4},
    {"text": "electronic beats", "weight": 0.3},
    {"text": "synthesizer", "weight": 0.2},
    {"text": "bass", "weight": 0.1}
  ]
}

Input: "a good pop song with the piano having the most weight"
Output: {
  "components": [
    {"text": "pop", "weight": 0.35},
    {"text": "piano", "weight": 0.4},
    {"text": "drums", "weight": 0.15},
    {"text": "bass", "weight": 0.1}
  ],
  "parameters": {
    "bpm": 110,
    "guidance": 7.5,
    "density": 0.6
  }
}

Input: "slow jazz ballad at 80 bpm with low density"
Output: {
  "components": [
    {"text": "jazz", "weight": 0.4},
    {"text": "piano", "weight": 0.35},
    {"text": "bass", "weight": 0.15},
    {"text": "drums", "weight": 0.1}
  ],
  "parameters": {
    "bpm": 80,
    "guidance": 7.0,
    "density": 0.3
  }
}

Input: "fast energetic EDM track at 140 bpm"
Output: {
  "components": [
    {"text": "edm", "weight": 0.4},
    {"text": "synthesizer", "weight": 0.3},
    {"text": "electronic beats", "weight": 0.2},
    {"text": "bass", "weight": 0.1}
  ],
  "parameters": {
    "bpm": 140,
    "guidance": 7.0,
    "density": 0.7
  }
}

Now extract the genre, determine appropriate instruments, and infer BPM, guidance, and density:"""
        
        # Construct the full prompt
        if is_edit and previous_context:
            # For edits, the prompt is already included in the system prompt
            full_prompt = system_prompt
        else:
            # For new tracks, append the user prompt
            full_prompt = f"{system_prompt}\n\n{prompt}"
        response = model.generate_content(full_prompt)
        
        # Extract JSON from response - handle different response formats
        try:
            if hasattr(response, 'text'):
                response_text = response.text
            elif hasattr(response, 'candidates') and len(response.candidates) > 0:
                # Handle newer API format
                candidate = response.candidates[0]
                if hasattr(candidate, 'content'):
                    response_text = candidate.content.parts[0].text if hasattr(candidate.content, 'parts') else str(candidate.content)
                else:
                    response_text = str(candidate)
            else:
                response_text = str(response)
            
            if not response_text:
                print(f"Error: Empty response from AI model. Response object: {response}")
                raise ValueError("AI model returned empty response")
            
            response_text = response_text.strip()
            
        except Exception as e:
            print(f"Error extracting text from response: {e}")
            print(f"Response object type: {type(response)}")
            print(f"Response object: {response}")
            raise ValueError(f"Failed to extract text from AI response: {e}")
        
        # Handle markdown code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        result = json.loads(response_text)
        
        # Validate and normalize weights
        components = result.get("components", [])
        if not components:
            print(f"Warning: AI returned no components for prompt: {prompt}")
            print(f"AI Response: {response_text[:500]}")
            raise ValueError("No components returned from AI")
        
        # Validate components have proper structure
        valid_components = []
        for comp in components:
            if isinstance(comp, dict) and "text" in comp and "weight" in comp:
                text = str(comp["text"]).strip()
                # Reject if component is too long (likely the full prompt)
                if len(text) > 50:
                    print(f"Warning: Skipping component that looks like full prompt: {text[:50]}...")
                    continue
                valid_components.append({"text": text, "weight": float(comp.get("weight", 0))})
        
        if not valid_components:
            print(f"Warning: No valid components after validation for prompt: {prompt}")
            raise ValueError("No valid components after validation")
        
        # Normalize weights to sum to 1.0
        total_weight = sum(comp.get("weight", 0) for comp in valid_components)
        if total_weight > 0:
            components = [
                {"text": comp["text"], "weight": comp["weight"] / total_weight}
                for comp in valid_components
            ]
        else:
            # Equal weights if no weights provided
            weight_per_component = 1.0 / len(valid_components)
            components = [
                {"text": comp["text"], "weight": weight_per_component}
                for comp in valid_components
            ]
        
        # Extract parameters with defaults
        params = result.get("parameters", {})
        bpm = int(params.get("bpm", 90))
        guidance = float(params.get("guidance", 7.0))
        density = float(params.get("density", 0.5))
        
        # Validate and clamp parameters
        bpm = max(60, min(180, bpm))  # Clamp between 60-180
        guidance = max(1.0, min(10.0, guidance))  # Clamp between 1.0-10.0
        density = max(0.0, min(1.0, density))  # Clamp between 0.0-1.0
        
        return {
            "weighted_prompts": components,
            "parameters": {
                "bpm": bpm,
                "guidance": guidance,
                "density": density
            }
        }
        
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        response_text = locals().get('response_text', 'N/A')
        if response_text != 'N/A':
            print(f"Response text (first 1000 chars): {response_text[:1000]}")
        raise ValueError(f"Failed to parse AI response as JSON: {e}. Response: {response_text[:200] if response_text != 'N/A' else 'N/A'}")
    except AttributeError as e:
        print(f"Attribute error (likely response format issue): {e}")
        print(f"Response object type: {type(response) if 'response' in locals() else 'N/A'}")
        raise ValueError(f"AI response format error: {e}")
    except Exception as e:
        print(f"Error analyzing prompt with AI: {type(e).__name__}: {e}")
        print(f"Prompt was: {prompt}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        if 'response_text' in locals():
            print(f"AI Response (first 1000 chars): {response_text[:1000]}")
        # Don't fallback - raise error so we know something is wrong
        raise ValueError(f"AI analysis failed: {type(e).__name__}: {e}")


def simple_breakdown(prompt: str) -> List[Dict[str, any]]:
    """
    DEPRECATED: This fallback is no longer used.
    Raises an error instead of returning bad results.
    """
    raise ValueError("AI analysis failed and fallback is disabled. Please check AI configuration and try again.")

