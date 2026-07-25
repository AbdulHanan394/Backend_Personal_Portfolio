"""Structured enrichment prompt and schema description."""

CATEGORIES = [
    "AI Infrastructure",
    "Platform Engineering",
    "Applied AI",
    "Frontend",
    "Thought Leadership",
    "DevOps",
    "Other",
]

ENRICHMENT_SYSTEM_PROMPT = f"""You enrich portfolio activity data.
Respond only with valid JSON matching this schema:
{{
  "summary": "string under about 40 words",
  "tags": ["0 to 3 short labels"],
  "technologies": ["0 to 5 technology names"],
  "category": "one of: {", ".join(CATEGORIES)}"
}}
Never invent facts absent from the title or raw payload.
Avoid marketing words such as revolutionary or cutting-edge."""

