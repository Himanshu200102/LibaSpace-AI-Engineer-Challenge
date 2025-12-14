"""Resume data helper utilities."""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ResumeHelper:
    """Helper class for extracting data from resume."""
    
    def __init__(self, resume_data: Dict[str, Any]):
        """Initialize with resume data."""
        self.resume_data = resume_data
        self.prefs = resume_data.get("application_preferences", {})
        self.diversity_prefs = self.prefs.get("diversity_fields", {})
        self.common_prefs = self.prefs.get("common_questions", {})
    
    def get_answer(self, question: str) -> str:
        """Try to get answer directly from resume data."""
        q_lower = question.lower()
        
        # Salary
        if "salary" in q_lower:
            salary = self.resume_data.get("salary_expectations", {})
            if salary:
                return f"${salary.get('min', 80000):,} - ${salary.get('max', 100000):,}"
        
        # Notice period
        if "notice" in q_lower:
            return self.resume_data.get("notice_period", "2 weeks")
        
        # Visa/work authorization
        if "visa" in q_lower or "authorized" in q_lower or ("work" in q_lower and "permit" in q_lower):
            return self.resume_data.get("visa_status", "Authorized to work")
        
        # Languages
        if "language" in q_lower:
            languages = self.resume_data.get("skills", {}).get("languages", ["English"])
            if languages:
                return languages[0]
        
        return ""
    
    def get_default_dropdown_value(self, question: str, options: List[str]) -> str:
        """Get default dropdown value from resume preferences or fallback logic."""
        q_lower = question.lower()
        
        # 1. Diversity/demographic fields - from resume.json preferences
        diversity_keywords = {
            "gender": ["gender"],
            "ethnicity": ["ethnicity", "ethnic"],
            "race": ["race"],
            "age_bracket": ["age bracket", "age"],
            "veteran_status": ["veteran"],
            "disability_status": ["disability"]
        }
        
        for field_key, keywords in diversity_keywords.items():
            if any(keyword in q_lower for keyword in keywords):
                preferred_value = self.diversity_prefs.get(field_key) or self.diversity_prefs.get("default", "Prefer not to say")
                # Try to find exact match or similar
                for opt in options:
                    opt_lower = opt.lower()
                    if preferred_value.lower() in opt_lower or opt_lower in preferred_value.lower():
                        logger.info(f"Selected '{opt}' for diversity field '{field_key}' (from preferences)")
                        return opt
                # Fallback: look for "prefer not to say" type options
                for opt in options:
                    opt_lower = opt.lower()
                    if any(phrase in opt_lower for phrase in ["prefer not", "decline", "not to say"]):
                        return opt
        
        # 2. Common questions - from resume.json preferences
        # Notice period
        if "notice" in q_lower:
            preferred = self.common_prefs.get("start_date_preference", "2 weeks notice")
            for opt in options:
                if preferred.lower() in opt.lower() or opt.lower() in preferred.lower():
                    return opt
            # Fallback to shortest notice
            for opt in options:
                if "1 week" in opt.lower() or "available" in opt.lower() or "immediate" in opt.lower():
                    return opt
        
        # Start date
        if "start" in q_lower or "date" in q_lower:
            preferred = self.common_prefs.get("start_date_preference", "2 weeks notice")
            # Try to match months
            months = ["February", "March", "January", "April", "May", "June", 
                     "July", "August", "September", "October", "November", "December"]
            for month in months:
                for opt in options:
                    if month in opt:
                        return opt
        
        # How did you hear
        if "hear" in q_lower or "found" in q_lower or "where did you" in q_lower:
            preferred = self.common_prefs.get("how_did_you_hear", "Job board")
            for opt in options:
                opt_lower = opt.lower()
                if preferred.lower() in opt_lower or opt_lower in preferred.lower():
                    return opt
        
        # Work authorization / visa
        if "authorized" in q_lower or "visa" in q_lower or ("work" in q_lower and "permit" in q_lower):
            if self.common_prefs.get("require_visa_sponsorship", "No").lower() == "no":
                for opt in options:
                    opt_lower = opt.lower()
                    if "yes" in opt_lower or "authorized" in opt_lower or "citizen" in opt_lower or "no" in opt_lower:
                        return opt
        
        # Yes/No questions - from preferences
        if len(options) <= 3:
            yes_no_options = [opt for opt in options if opt.lower() in ["yes", "no"]]
            if yes_no_options:
                # Check preferences
                if "open to" in q_lower or "willing" in q_lower or "available" in q_lower:
                    preferred = self.common_prefs.get("open_to_remote", "Yes") if "remote" in q_lower else self.common_prefs.get("open_to_relocation", "No")
                    for opt in yes_no_options:
                        if preferred.lower() in opt.lower():
                            return opt
                elif "immediate" in q_lower or "available" in q_lower:
                    preferred = self.common_prefs.get("available_immediately", "Yes")
                    for opt in yes_no_options:
                        if preferred.lower() in opt.lower():
                            return opt
        
        # Default: first non-empty option
        for opt in options:
            if opt and opt != "Select..." and opt.strip():
                return opt
        
        return options[0] if options else ""
    
    def get_consent_preferences(self) -> Dict[str, bool]:
        """Get consent checkbox preferences."""
        consent_prefs = self.prefs.get("consent_preferences", {})
        return {
            "auto_check_consent": consent_prefs.get("auto_check_consent", True),
            "auto_check_terms": consent_prefs.get("auto_check_terms", True),
            "auto_check_privacy": consent_prefs.get("auto_check_privacy", True)
        }

