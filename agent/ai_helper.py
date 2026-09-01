"""
AI Helper Module
Uses Google Gemini to generate personalized cover letters
and suggest answers to screening questions.
"""
import os
import warnings
from dotenv import load_dotenv

load_dotenv()

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=FutureWarning)
    try:
        import google.generativeai as genai
        GEMINI_AVAILABLE = True
    except ImportError:
        GEMINI_AVAILABLE = False


class AIHelper:
    """AI-powered helper for cover letters and human-like screening questions."""

    def __init__(self, config: dict, account_profile: dict = None):
        self.config = config
        self.applicant = config.get("applicant", {})
        self.account_profile = account_profile or {}
        self.model = None
        self._setup_gemini()

    def _setup_gemini(self):
        """Initialize Gemini API."""
        if not GEMINI_AVAILABLE:
            return

        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key or api_key == "your_gemini_api_key_here":
            return

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning)
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel("gemini-1.5-flash")
                print("✅ Gemini AI initialized for author-style question answering.")
            except Exception as e:
                print(f"⚠️ Gemini configuration error: {e}")

    def _get_applicant_context(self) -> str:
        """Build full author persona context for AI."""
        name = self.account_profile.get("full_name") or self.applicant.get("name", "Siam Hossain")
        headline = self.account_profile.get("headline") or "Full Stack Developer (Python | Django | FastAPI | TypeScript | Next.js | React)"
        skills = ", ".join(self.account_profile.get("skills", [
            "Python", "Django", "FastAPI", "TypeScript", "React", "Next.js", "PostgreSQL",
            "REST APIs", "Docker", "Git", "Celery", "Redis", "Tailwind CSS", "JavaScript"
        ]))
        years_exp = self.applicant.get("years_of_experience", "3")
        return f"Name: {name}\nRole: {headline}\nKey Skills: {skills}\nExperience: {years_exp}+ years"

    def generate_cover_letter(self, job_title: str, company: str, job_description: str = "") -> str:
        """Generate a personalized cover letter as Siam Hossain."""
        if not self.model:
            return self._default_cover_letter(job_title, company)

        applicant_ctx = self._get_applicant_context()
        prompt = f"""
Write a compelling, natural, 1st-person cover letter for this job application.

Applicant Profile:
{applicant_ctx}

Job Details:
- Role: {job_title}
- Company: {company}
- Description Excerpt: {job_description[:800] if job_description else 'Not provided'}

Guidelines:
- 2 short paragraphs, confident and authentic tone.
- Directly highlight relevant skills (Python, Django, FastAPI, TypeScript/React).
- Sound like a passionate, experienced engineer.
- Return ONLY the cover letter body without header or subject line.
"""
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            return self._default_cover_letter(job_title, company)

    def answer_screening_question(self, question: str, is_numeric: bool = False) -> str:
        """Answer screening questions in author's voice like a real human candidate."""
        q_lower = question.lower()

        # Handle numeric inputs directly
        if is_numeric or "how many years" in q_lower or "years of experience" in q_lower:
            years = str(self.applicant.get("years_of_experience", "3"))
            # If specific technology mentioned, return 3
            return years

        if self.model:
            applicant_ctx = self._get_applicant_context()
            prompt = f"""
You are {self.applicant.get('name', 'Siam Hossain')}, answering a job screening question.
Profile:
{applicant_ctx}

Question: "{question}"

Instructions:
- Write in first person ("I have...", "I am experienced with...").
- Keep it concise (1 to 2 sentences max).
- Sound confident, professional, and authentic like a seasoned developer.
- If it is a Yes/No question, start directly with "Yes,".
- If it asks for a salary expectation, state: "$65,000 - $85,000 / year (flexible depending on total compensation)".
- Return ONLY the direct answer text.
"""
            try:
                response = self.model.generate_content(prompt)
                ans = response.text.strip().strip('"')
                if ans:
                    return ans
            except Exception:
                pass

        return self._default_answer(question)

    def _default_cover_letter(self, job_title: str, company: str) -> str:
        """Fallback cover letter."""
        name = self.account_profile.get("full_name") or self.applicant.get("name", "Siam Hossain")
        phone = self.applicant.get("phone", "+880 1700000000")
        return f"""I am thrilled to apply for the {job_title} position at {company}. With over 3 years of full-stack engineering experience building robust web applications and scalable backend systems using Python, Django, FastAPI, TypeScript, and React, I am confident in my ability to make an immediate impact on your engineering team.

Throughout my work, I have focused on designing clean RESTful APIs, optimizing database performance with PostgreSQL, and crafting responsive frontend experiences. I thrive in collaborative remote environments and look forward to discussing how my background aligns with {company}'s goals.

Best regards,
{name}
{phone}"""

    def _default_answer(self, question: str) -> str:
        """Smart fallback answers for common screening questions."""
        q = question.lower()
        years = str(self.applicant.get("years_of_experience", "3"))

        if "authorized" in q or "authorization" in q or "legally" in q or "eligible" in q:
            return "Yes, I am fully authorized and eligible to work."
        elif "sponsorship" in q or "require visa" in q or "sponsor" in q:
            return "No, I do not require visa sponsorship."
        elif "years" in q or "experience" in q:
            return f"I have over {years} years of professional experience in this area."
        elif "salary" in q or "compensation" in q or "rate" in q:
            return "$65,000 - $80,000 / year (open to discussion based on full benefits)."
        elif "remote" in q or "work from home" in q:
            return "Yes, I have extensive experience collaborating productively across distributed remote teams."
        elif "notice" in q or "start" in q or "available" in q:
            return "I am available to start immediately or within 1-2 weeks."
        elif "relocate" in q:
            return "Yes, open to relocation or remote arrangements."
        elif "background check" in q or "drug" in q:
            return "Yes, I am comfortable completing all standard background verifications."
        elif "english" in q or "language" in q:
            return "Yes, I have professional working proficiency in English."
        elif "degree" in q or "bachelor" in q or "education" in q:
            return "Yes, I hold a Bachelor's degree in Computer Science / Engineering."
        elif "why" in q or "interest" in q or "about you" in q:
            return "My deep hands-on background in Python, Django, and TypeScript aligns directly with your tech stack, and I am excited to build scalable solutions with your team."
        else:
            return "Yes, I meet all the requirements for this role and am eager to contribute."
