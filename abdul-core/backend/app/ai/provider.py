from app.config.settings import get_settings
from app.ai.llm_client import GeminiLLMClient, GithubLLMClient

settings = get_settings()

def get_llm():
    print("LLM Provider:", settings.llm_provider)

    if settings.llm_provider.lower() == "github":
        print("Using GitHub LLM")
        return GithubLLMClient()

    print("Using Gemini LLM")
    return GeminiLLMClient()