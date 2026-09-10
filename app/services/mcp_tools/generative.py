import json

def generate_ab_test_variants(asset_id: str, variable: str, campaign_id: str = None, timeframe: int = 0, **kwargs) -> dict:
    from app.services.llm_rotator import get_genai_client
    try:
        client = get_genai_client()
        prompt = f"You are an expert B2B copywriter. Create A/B test variants for an asset named '{asset_id}' (in the context of campaign '{campaign_id}'). The variable to test is '{variable}'. Output a JSON object with keys: 'control', 'variant_a', 'variant_b', and 'rationale'."
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return json.loads(response.text)
    except Exception as e:
        return {"error": str(e)}


def draft_outreach_sequence(persona: str, context_data: str, campaign_id: str = None, timeframe: int = 0, **kwargs) -> dict:
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
        return json.loads(response.text)
    except Exception as e:
        return {"error": str(e)}
