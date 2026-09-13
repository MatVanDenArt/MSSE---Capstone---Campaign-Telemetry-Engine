"""
Generative content synthesis - MCP tools

Implements AI-driven content generation tools invoked autonomously by the Copilot:
  - `generate_ab_test_variants`: Synthesizes A/B test variations (Control, Variant A, Variant B)
    along with strategic testing rationale for a given creative variable.
  - `draft_outreach_sequence`: Drafts a tailored 3-step cadence (Email -> LinkedIn InMail -> Email)
    personalized to target contact seniority and observed intent signals.
"""

import json
import re

def _clean_and_parse_json(raw_text: str) -> dict:
    """Safely parse JSON from an LLM response, tolerating markdown fences and trailing text."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        start_idx = text.find('{')
        if start_idx != -1:
            try:
                obj, _ = json.JSONDecoder().raw_decode(text[start_idx:])
                return obj
            except Exception:
                pass
        raise

def generate_ab_test_variants(asset_id: str, variable: str, campaign_id: str = None, timeframe: int = 0, **kwargs) -> dict:
    """
    Generate structured A/B test copy variations and strategic hypotheses for an asset.
    Returns JSON with control, variant_a, variant_b, and strategic rationale.
    """
    from app.services.llm_rotator import get_genai_client
    try:
        client = get_genai_client()
        target_persona = kwargs.get('target_persona', 'B2B Technical & Economic Decision Maker')
        prompt = (
            f"You are an expert B2B copywriter specializing in industrial engineering and energy transition marketing.\n"
            f"Create rigorous A/B test variants for an asset named '{asset_id}' (Campaign: '{campaign_id}').\n"
            f"Testing Variable: '{variable}'.\n"
            f"Target Audience: '{target_persona}'.\n"
            f"Output a JSON object with keys: 'control', 'variant_a', 'variant_b', and 'rationale' explaining the behavioral hypothesis behind each variant."
        )
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return _clean_and_parse_json(response.text)
    except Exception as e:
        return {"error": str(e)}


def draft_outreach_sequence(persona: str, context_data: str, campaign_id: str = None, timeframe: int = 0, **kwargs) -> dict:
    """
    Generate a 3-step multi-touch sales outreach cadence tailored to contact persona and observed intent signals.
    """
    from app.services.llm_rotator import get_genai_client

    try:
        client = get_genai_client()
        prompt = f"""
        You are an expert B2B sales development representative. 
        Write a 3-step outreach sequence (Email -> LinkedIn -> Email) tailored for a '{persona}' persona.
        They recently showed intent around: '{context_data}'.
        
        Write the email and message body naturally. Do not just blindly copy/paste the intent data into a template. 
        Weave the context organically into the copy.
        
        Return a JSON object with this exact structure:
        {{
            "persona": "{persona}",
            "context": "{context_data}",
            "sequence": [
                {{
                    "step": "Day 1: Contextual Intro",
                    "channel": "Email",
                    "content": "..."
                }},
                {{
                    "step": "Day 3: Value Add",
                    "channel": "LinkedIn Message",
                    "content": "..."
                }},
                {{
                    "step": "Day 7: Breakup",
                    "channel": "Email",
                    "content": "..."
                }}
            ],
            "strategic_note": "A 1-sentence note explaining the tone and angle used."
        }}
        """
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return _clean_and_parse_json(response.text)
    except Exception as e:
        return {"error": str(e)}
