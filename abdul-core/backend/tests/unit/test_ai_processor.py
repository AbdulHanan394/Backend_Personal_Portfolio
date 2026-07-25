"""Unit tests for AI enrichment parsing."""

import pytest

from app.services.ai_processor import AIProcessor


class FakeLLM:
    """Fake LLM client returning a fixed response."""

    async def complete(self, system: str, user: str, *, max_tokens: int | None = None) -> str:
        """Return valid enrichment JSON."""

        return (
            '{"summary":"Abdul refined the backend pipeline.",'
            '"tags":["Backend"],"technologies":["FastAPI"],"category":"Platform Engineering"}'
        )


@pytest.mark.asyncio
async def test_ai_processor_parses_structured_json() -> None:
    """The processor validates summary metadata from structured JSON."""

    processor = AIProcessor(llm_client=FakeLLM())
    activity = type(
        "ActivityStub",
        (),
        {
            "title": "Pipeline work",
            "type": "Push",
            "source": type("SourceStub", (), {"slug": "github"})(),
            "raw_payload": {"id": "1"},
        },
    )()

    enrichment = await processor.enrich(activity)

    assert enrichment.summary == "Abdul refined the backend pipeline."
    assert enrichment.tags == ["Backend"]
    assert enrichment.technologies == ["FastAPI"]
    assert enrichment.category == "Platform Engineering"

