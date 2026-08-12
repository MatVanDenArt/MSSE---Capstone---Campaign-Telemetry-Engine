import os
import random

def get_random_api_key() -> str:
    """Returns a random API key from the GEMINI_API_KEYS environment variable."""
    keys_str = os.environ.get("GEMINI_API_KEYS", "")
    if not keys_str:
        # Fallback to single key env var, which might also contain commas
        keys_str = os.environ.get("GEMINI_API_KEY", "")
    
    # Split by comma and remove empty strings/whitespace
    keys = [k.strip() for k in keys_str.split(",") if k.strip()]
    if not keys:
        return ""
        
    return random.choice(keys)

def get_genai_client():
    """Returns a client for the new SDK (google-genai) using a random key."""
    from google import genai
    api_key = get_random_api_key()
    if not api_key:
        raise ValueError("No Gemini API key found. Please set GEMINI_API_KEYS.")
    return genai.Client(api_key=api_key)

def get_legacy_generative_model(model_name="gemini-3.5-flash"):
    """Returns a model for the old SDK (google.generativeai) using a random key."""
    import google.generativeai as genai
    api_key = get_random_api_key()
    if not api_key:
        raise ValueError("No Gemini API key found. Please set GEMINI_API_KEYS.")
    
    # Configure the global genai module with the randomly selected key
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)
