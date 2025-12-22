import os
import json
import re
from typing import List, Dict

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


def analyze_prompt_for_weighted_components(prompt: str) -> List[Dict[str, any]]:
    """
    Uses Gemini to intelligently break down a music prompt into weighted components.
    Returns a list of weighted prompts that sum to 1.0
    """
    if not API_KEY or not GEMINI_AVAILABLE:
        raise ValueError("Gemini AI is not available. Please check GOOGLE_API_KEY environment variable.")
    
    try:
        model = genai.GenerativeModel('gemini-3-flash-preview')
        
        system_prompt = """You are a music production assistant. Extract the GENRE and determine appropriate INSTRUMENTS to create weighted components.

CRITICAL RULES:
1. ALWAYS identify the genre/style from the prompt
2. If instruments are mentioned, use those
3. If NO instruments are mentioned, INFER appropriate instruments for that genre based on music production knowledge
4. Each component must be a SINGLE word or short phrase (e.g., "pop", "synthesizer", "drums", "bass")
5. Do NOT include the full prompt text or explanatory phrases
6. Create 3-5 components (genre + 2-4 instruments)
7. Weights must sum to 1.0
8. Genre typically gets 30-50% weight, lead instruments get higher weights

EXTRACTION PROCESS:
1. Identify the GENRE (e.g., pop, jazz, kpop, classical, orchestral, hip hop, rock, etc.)
2. Check if instruments are EXPLICITLY mentioned:
   - If YES: Use those instruments
   - If NO: Infer 2-4 typical instruments for that genre
3. Assign weights: genre (30-50%), lead instruments (20-30% each), supporting instruments (10-20% each)

COMMON GENRE INSTRUMENTS (use when not specified):
- Pop: synthesizer, drums, bass, electric guitar
- Jazz: piano, drums, bass, saxophone
- Hip hop: drums, bass, synthesizer
- Rock: electric guitar, drums, bass
- Classical/Orchestral: strings, brass, woodwinds, percussion
- Kpop: synthesizer, electronic beats, bass
- Neo soul: piano, strings, bass, drums

OUTPUT FORMAT (JSON only):
{
  "components": [
    {"text": "genre", "weight": 0.4},
    {"text": "instrument1", "weight": 0.3},
    {"text": "instrument2", "weight": 0.2},
    {"text": "instrument3", "weight": 0.1}
  ]
}

EXAMPLES:

Input: "i want a catchy pop song"
Output: {
  "components": [
    {"text": "pop", "weight": 0.4},
    {"text": "synthesizer", "weight": 0.3},
    {"text": "drums", "weight": 0.2},
    {"text": "bass", "weight": 0.1}
  ]
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
  ]
}

Now extract the genre and determine appropriate instruments:"""

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
            # Retry with a simpler approach
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
        
        return components
        
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

