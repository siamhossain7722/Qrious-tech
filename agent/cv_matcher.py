"""
CV Matcher Module
Extracts skills, experience, and keywords from applicant CV/Resume (PDF)
and computes a match score (0-100%) against job descriptions.
"""
import re
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


COMMON_TECH_SKILLS = [
    # Languages
    "python", "javascript", "typescript", "java", "c++", "c#", "golang", "go",
    "rust", "php", "ruby", "sql", "html", "css", "bash", "shell",
    # Frameworks & Libraries
    "django", "flask", "fastapi", "react", "next.js", "nextjs", "vue", "angular",
    "node.js", "nodejs", "express", "spring boot", "laravel", "rails", "asp.net",
    "tailwind", "bootstrap", "sass", "graphql", "rest api", "restful", "grpc",
    # Databases & Caching
    "postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis", "elasticsearch",
    "dynamodb", "mariadb", "cassandra", "supabase", "firebase",
    # DevOps & Cloud
    "docker", "kubernetes", "k8s", "aws", "azure", "gcp", "google cloud", "git",
    "github", "gitlab", "ci/cd", "terraform", "ansible", "nginx", "linux",
    # Architecture & Tools
    "microservices", "celery", "kafka", "rabbitmq", "pytest", "unit testing",
    "tdd", "agile", "scrum", "jira", "oop", "algorithms", "data structures",
    # AI & Data
    "machine learning", "deep learning", "nlp", "llm", "pandas", "numpy",
    "scikit-learn", "tensorflow", "pytorch", "langchain",
]


def safe_print(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))


class CVMatcher:
    """Extracts CV data and scores job descriptions against applicant background."""

    def __init__(self, resume_path: str = "", account_profile: Optional[dict] = None, config: Optional[dict] = None, ai_helper=None):
        self.resume_path = resume_path
        self.account_profile = account_profile or {}
        self.config = config or {}
        self.ai = ai_helper

        self.cv_text = ""
        self.cv_skills: List[str] = []
        self.cv_titles: List[str] = []
        self.years_exp = 0

        self._load_cv_and_profile()

    def _load_cv_and_profile(self):
        """Extract text and skills from CV file and profile data."""
        # 1. Read PDF file if provided
        if self.resume_path and os.path.exists(self.resume_path) and PYPDF_AVAILABLE:
            try:
                reader = pypdf.PdfReader(self.resume_path)
                pages_text = [page.extract_text() or "" for page in reader.pages]
                self.cv_text = "\n".join(pages_text).strip()
            except Exception as e:
                safe_print(f"[!] Error reading CV PDF: {e}")

        # 2. Extract skills from extracted CV text
        extracted_from_text = self._extract_skills_from_text(self.cv_text) if self.cv_text else []

        # 3. Augment with LinkedIn Account Profile skills
        profile_skills = []
        if isinstance(self.account_profile, dict):
            profile_skills = self.account_profile.get("skills", [])
            if isinstance(profile_skills, str):
                try:
                    import json
                    profile_skills = json.loads(profile_skills)
                except Exception:
                    profile_skills = [profile_skills]

        # 4. Augment with Config
        applicant_cfg = self.config.get("applicant", {})
        config_title = applicant_cfg.get("current_position", "")
        config_years = applicant_cfg.get("years_of_experience", "2")
        try:
            self.years_exp = int(re.sub(r"[^\d]", "", str(config_years)) or "2")
        except Exception:
            self.years_exp = 2

        # Combine all unique skills (lowercased)
        combined_skills = set(s.lower() for s in (extracted_from_text + profile_skills) if s)
        self.cv_skills = list(combined_skills)

        # Titles
        titles = []
        if config_title:
            titles.append(config_title.lower())
        if self.account_profile.get("headline"):
            titles.append(self.account_profile.get("headline", "").lower())
        self.cv_titles = titles

        skills_preview = ", ".join(self.cv_skills[:8]) if self.cv_skills else "Configured keywords"
        safe_print(f"📄 CV Matcher initialized | Extracted {len(self.cv_skills)} skills: {skills_preview}")

    def _extract_skills_from_text(self, text: str) -> List[str]:
        """Scan raw CV text for known technical skills."""
        text_lower = text.lower()
        found = []
        for skill in COMMON_TECH_SKILLS:
            # Word boundary matching
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, text_lower):
                found.append(skill)
        return found

    def evaluate_match(self, job_title: str, company: str, job_description: str = "") -> Tuple[int, str, bool]:
        """
        Evaluate how well a job matches the applicant's CV.
        Returns:
            match_score (int: 0-100)
            reasons (str: explanation and matching highlights)
            is_good_match (bool: True if >= threshold)
        """
        title_lower = job_title.lower()
        desc_lower = (job_description or "").lower()
        combined_job_text = f"{title_lower} {desc_lower}"

        # 1. Role / Title Match Score (0 - 40 points)
        title_score = 0
        matching_title_keywords = []

        # Check configured keywords and CV titles
        target_keywords = self.config.get("job_search", {}).get("keywords", [])
        search_terms = target_keywords + self.cv_titles + ["developer", "engineer", "software", "backend", "python", "full stack"]

        for term in set(search_terms):
            if not term:
                continue
            words = term.lower().split()
            matched_words = [w for w in words if w in title_lower]
            if len(matched_words) == len(words):
                title_score = max(title_score, 40)
                matching_title_keywords.append(term)
            elif len(matched_words) > 0:
                title_score = max(title_score, 25)
                matching_title_keywords.extend(matched_words)

        if not matching_title_keywords and ("developer" in title_lower or "engineer" in title_lower):
            title_score = 20

        # 2. Skills Match Score (0 - 45 points)
        matched_skills = []
        if self.cv_skills:
            for skill in self.cv_skills:
                pattern = r"\b" + re.escape(skill) + r"\b"
                if re.search(pattern, combined_job_text):
                    matched_skills.append(skill)

            skill_ratio = min(1.0, len(matched_skills) / max(3, min(8, len(self.cv_skills))))
            skill_score = int(skill_ratio * 45)
        else:
            # Fallback if no CV skills extracted: check generic Python/Django stack
            default_stack = ["python", "django", "sql", "api", "git", "backend"]
            matched_skills = [s for s in default_stack if s in combined_job_text]
            skill_score = min(45, len(matched_skills) * 9)

        # 3. Experience & Keyword Bonus (0 - 15 points)
        exp_score = 15
        if "senior" in title_lower and self.years_exp < 3:
            exp_score = 5
        elif "lead" in title_lower and self.years_exp < 5:
            exp_score = 0
        elif "junior" in title_lower or "entry" in title_lower or "associate" in title_lower:
            exp_score = 15

        # Calculate Total Heuristic Score
        total_score = min(100, max(10, title_score + skill_score + exp_score))

        # Format match reasons summary
        matched_str = ", ".join(list(dict.fromkeys(matched_skills))[:6])
        if not matched_str:
            matched_str = "Title & role alignment"

        reasons = f"Matched skills: {matched_str}"
        if matching_title_keywords:
            reasons += f" | Title match: {', '.join(list(set(matching_title_keywords))[:2])}"

        return total_score, reasons, total_score >= 60
