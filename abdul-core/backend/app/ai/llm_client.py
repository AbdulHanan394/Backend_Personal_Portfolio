"""LLM client implementations."""

from abc import ABC, abstractmethod

from google import genai
from google.genai import types

from app.config.settings import get_settings

settings = get_settings()


class LLMClient(ABC):
    """Abstract interface for all LLM providers."""

    @abstractmethod
    async def complete(
        self,
        system: str,
        user: str,
        max_tokens: int | None = None,
        json_output: bool = False,
    ) -> str:
        """Return the model response."""
        raise NotImplementedError


class GeminiLLMClient(LLMClient):
    """Gemini implementation of the LLM client."""

    async def complete(
        self,
        system: str,
        user: str,
        max_tokens: int | None = None,
        json_output: bool = False,
    ) -> str:
        client = genai.Client(api_key=settings.gemini_api_key)

        print("========== SYSTEM ==========")
        print(system)

        print("========== USER ==========")
        print(user)

        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens or settings.llm_max_tokens,
            temperature=0.2,
        )
        if json_output:
            config.response_mime_type = "application/json"

        response = await client.aio.models.generate_content(
            model=settings.llm_model,
            contents=user,
            config=config,
        )

        print("========== GEMINI RESPONSE ==========")
        print(response.text)

        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")

        return response.text.strip()