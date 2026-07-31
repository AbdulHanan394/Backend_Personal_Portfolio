from abc import ABC, abstractmethod

from google import genai
from google.genai import types

from openai import AsyncOpenAI

from app.config.settings import get_settings

settings = get_settings()


class LLMClient(ABC):

    @abstractmethod
    async def complete(
        self,
        system: str,
        user: str,
        max_tokens: int | None = None,
        json_output: bool = False,
    ) -> str:
        ...


class GeminiLLMClient(LLMClient):

    async def complete(
        self,
        system: str,
        user: str,
        max_tokens: int | None = None,
        json_output: bool = False,
    ) -> str:

        client = genai.Client(api_key=settings.gemini_api_key)

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

        if not response.text:
            raise RuntimeError("Gemini returned empty response.")

        return response.text.strip()


class GithubLLMClient(LLMClient):

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.github_models_api_key,
            base_url=settings.github_models_endpoint,
        )

    async def complete(
        self,
        system: str,
        user: str,
        max_tokens: int | None = None,
        json_output: bool = False,
    ) -> str:

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        kwargs = {}

        if json_output:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await self.client.chat.completions.create(
                model=settings.github_llm_model,
                messages=messages,
                max_tokens=max_tokens or settings.llm_max_tokens,
                temperature=0.2,
                **kwargs,
            )
        except Exception:
            print("========== GITHUB ERROR ==========")
            import traceback
            traceback.print_exc()
            raise

        text = response.choices[0].message.content

        if not text:
            raise RuntimeError("GitHub Model returned empty response.")

        return text.strip()


class GroqLLMClient(LLMClient):

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
        )

    async def complete(
        self,
        system: str,
        user: str,
        max_tokens: int | None = None,
        json_output: bool = False,
    ) -> str:

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        kwargs = {}

        if json_output:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await self.client.chat.completions.create(
                model=settings.groq_model,
                messages=messages,
                max_tokens=max_tokens or settings.llm_max_tokens,
                temperature=0.2,
                **kwargs,
            )
        except Exception:
            print("========== GROQ ERROR ==========")
            import traceback
            traceback.print_exc()
            raise

        text = response.choices[0].message.content

        if not text:
            raise RuntimeError("Groq returned empty response.")

        return text.strip()