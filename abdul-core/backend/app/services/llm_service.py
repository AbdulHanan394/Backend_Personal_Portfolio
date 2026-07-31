# from google import genai
# from app.config.settings import get_settings


# settings = get_settings()

# client = genai.Client(
#     api_key=settings.gemini_api_key
# )


# async def generate_response(prompt: str):

#     response = client.models.generate_content(
#         model=settings.llm_model,
#         contents=prompt,
#         config={
#             "max_output_tokens": settings.llm_max_tokens
#         }
#     )

#     return response.text