from app.config.settings import get_settings
from app.ai.llm_client import (
    GeminiLLMClient,
    GithubLLMClient,
    GroqLLMClient,
)

settings = get_settings()


def get_llm():
    provider = settings.llm_provider.lower()

    print("LLM Provider:", provider)

    if provider == "github":
        print("Using GitHub LLM")
        return GithubLLMClient()

    elif provider == "groq":
        print("Using Groq LLM")
        return GroqLLMClient()

    elif provider == "gemini":
        print("Using Gemini LLM")
        return GeminiLLMClient()

    raise ValueError(f"Unsupported LLM provider: {provider}")