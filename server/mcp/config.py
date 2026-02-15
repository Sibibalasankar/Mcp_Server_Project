import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Figma Configuration
    FIGMA_ACCESS_TOKEN = os.getenv('FIGMA_ACCESS_TOKEN', '')
    FIGMA_API_URL = "https://api.figma.com/v1"
    
    # OpenRouter Configuration
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
    # Try this updated endpoint
    OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"  # This is correct
    # Alternative endpoint if the above doesn't work:
    # OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    # Test with a known working model
    OPENROUTER_MODEL = "openai/gpt-3.5-turbo"  # Most compatible
    
    # Server Configuration
    HOST = "0.0.0.0"
    PORT = 8000