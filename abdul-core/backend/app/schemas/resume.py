from pydantic import BaseModel


class ResumeProject(BaseModel):
    title: str
    description: str
    technologies: list[str] = []


class ResumeExperience(BaseModel):
    company: str
    role: str
    description: str
    technologies: list[str] = []


class ResumeEducation(BaseModel):
    school: str
    degree: str


class ResumeSkill(BaseModel):
    name: str


class ResumeSocialLinks(BaseModel):
    github: str
    linkedin: str
    x: str
    portfolio: str


class ResumeData(BaseModel):
    summary: str
    social_links: ResumeSocialLinks | None = None
    skills: list[ResumeSkill] = []
    projects: list[ResumeProject] = []
    experience: list[ResumeExperience] = []
    education: list[ResumeEducation] = []