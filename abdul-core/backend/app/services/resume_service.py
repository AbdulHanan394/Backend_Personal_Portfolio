"""Resume import service."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.activity import ManualActivityCreate
from app.schemas.resume import ResumeData
from app.services.activity_service import ActivityService


class ResumeService:
    """
    Imports resume information directly into the vector memory.

    No Gemini summarization is used here.
    Resume data is converted into structured text and embedded directly.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.activity_service = ActivityService(session)

    async def import_resume(self, resume: ResumeData) -> None:
        """
        Convert resume sections into activities
        and directly create embeddings.
        """

        # -------------------------
        # Profile Summary
        # -------------------------

        if resume.summary:
            await self._create_embedding_activity(
                title="About Abdul Hanan",
                content=f"""
PERSON:
Abdul Hanan

PROFESSIONAL SUMMARY:
{resume.summary}

This information describes Abdul Hanan's professional background,
AI engineering experience, and technical specialization.
""",
                activity_type="about",
                category="About",
                tags=["Resume", "Profile"]
            )


        # -------------------------
        # Skills
        # -------------------------

        if resume.skills:

            skills_text = "\n".join(
                [
                    f"- {skill.name}"
                    for skill in resume.skills
                ]
            )

            await self._create_embedding_activity(
                title="Technical Skills",
                content=f"""
PERSON:
Abdul Hanan

TECHNICAL SKILLS:

{skills_text}

These are the technologies, frameworks,
programming languages, AI tools,
databases and engineering skills Abdul uses.
""",
                activity_type="skills",
                category="Skills",
                tags=["Resume", "Technology"]
            )


        # -------------------------
        # Projects
        # -------------------------

        for project in resume.projects:

            technologies = ", ".join(
                project.technologies
            )

            await self._create_embedding_activity(

                title=project.title,

                content=f"""
PROJECT:
{project.title}


DESCRIPTION:
{project.description}


TECHNOLOGIES USED:
{technologies}


PROJECT INFORMATION:
This project was developed by Abdul Hanan.
The description above contains the purpose,
features and technical implementation details.
""",

                activity_type="project",
                category="Projects",
                tags=["Resume", "Project"]
            )


        # -------------------------
        # Experience
        # -------------------------

        for experience in resume.experience:

            technologies = ", ".join(
                experience.technologies
            )


            await self._create_embedding_activity(

                title=f"{experience.role} at {experience.company}",

                content=f"""
COMPANY:
{experience.company}


ROLE:
{experience.role}


WORK EXPERIENCE:
{experience.description}


TECHNOLOGIES:
{technologies}


This represents Abdul Hanan's professional
software engineering experience.
""",

                activity_type="experience",
                category="Experience",
                tags=["Resume", "Work"]
            )


        # -------------------------
        # Education
        # -------------------------

        for education in resume.education:

            await self._create_embedding_activity(

                title=education.degree,

                content=f"""
EDUCATION:

Institution:
{education.school}

Degree:
{education.degree}

This represents Abdul Hanan's academic background.
""",

                activity_type="education",
                category="Education",
                tags=["Resume"]
            )


        await self.session.commit()


    async def _create_embedding_activity(
        self,
        title: str,
        content: str,
        activity_type: str,
        category: str,
        tags: list[str],
    ):

        """
        Creates activity and directly embeds it.
        No LLM processing.
        """

        activity_request = ManualActivityCreate(

            type=activity_type,

            title=title,

            summary=content,

            technologies=[],

            tags=tags,

            category=category,

            url=""

        )


        activity = await self.activity_service.insert_manual(
            activity_request
        )


        # Direct embedding
        await self.activity_service.embed_and_publish(
            activity
        )