"""Main agent for Lever job applications."""
import asyncio
import logging
from typing import Dict, Any, Optional
from automation.browser import BrowserManager
from core.llm_client import LLMClient
from core.form_handler import FormHandler
from utils.resume import ResumeHelper

logger = logging.getLogger(__name__)


class LeverJobApplicant:
    """Lever-specific job application agent with LLM support."""
    
    def __init__(self, resume_data: Dict[str, Any], resume_file_path: Optional[str] = None, headless: bool = False):
        """Initialize Lever job applicant."""
        self.resume_data = resume_data
        self.resume_file_path = resume_file_path
        self.job_description = ""
        
        # Initialize components
        self.browser_manager = BrowserManager(headless=headless)
        self.llm_client = LLMClient()  # Will handle None API key internally
        self.resume_helper = ResumeHelper(resume_data)
    
    async def apply(self, job_url: str) -> Dict[str, Any]:
        """Apply to a Lever job."""
        result = {
            "success": False,
            "fields_filled": [],
            "fields_empty": [],
            "errors": []
        }
        
        try:
            # Start browser
            await self.browser_manager.start()
            page = self.browser_manager.get_page()
            
            # Initialize form handler
            form_handler = FormHandler(
                page=page,
                llm_client=self.llm_client,
                resume_helper=self.resume_helper,
                resume_data=self.resume_data,
                resume_file_path=self.resume_file_path,
                job_description=self.job_description
            )
            
            # First, get the job description from the main job page
            logger.info(f"Getting job description from: {job_url}")
            await page.goto(job_url, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            
            # Extract job description
            try:
                jd_element = await page.query_selector('[class*="posting-page"] [class*="section-wrapper"]')
                if jd_element:
                    self.job_description = await jd_element.inner_text()
                    logger.info(f"Got job description ({len(self.job_description)} chars)")
                    # Update form handler with job description
                    form_handler.job_description = self.job_description
            except:
                pass
            
            # Navigate to apply page
            apply_url = f"{job_url}/apply" if not job_url.endswith("/apply") else job_url
            logger.info(f"Navigating to: {apply_url}")
            await page.goto(apply_url, wait_until="domcontentloaded")
            await asyncio.sleep(3)  # Wait for page to fully load
            
            # Dismiss cookie consent if present
            await self._dismiss_cookies(page)
            
            # Fill basic info section (direct from resume)
            logger.info("=" * 50)
            logger.info("STEP 1: Filling basic info...")
            logger.info("=" * 50)
            await form_handler.fill_basic_info(result)
            
            # Fill application form section (dropdowns + LLM for complex)
            logger.info("=" * 50)
            logger.info("STEP 2: Filling application form...")
            logger.info("=" * 50)
            await form_handler.fill_application_form(result)
            
            # Upload resume if provided
            if self.resume_file_path:
                logger.info("=" * 50)
                logger.info("STEP 3: Uploading resume...")
                logger.info("=" * 50)
                await form_handler.upload_resume(result)
            
            # VERIFICATION: Check all fields and re-fill empty ones
            logger.info("=" * 50)
            logger.info("STEP 4: Verifying all fields are filled...")
            logger.info("=" * 50)
            await form_handler.verify_and_fill_empty_fields(result)
            
            # Second verification pass
            logger.info("=" * 50)
            logger.info("STEP 5: Final verification...")
            logger.info("=" * 50)
            await form_handler.final_verification(result)
            
            # Solve CAPTCHA if present
            logger.info("Checking for CAPTCHA...")
            captcha_solved = await form_handler.solve_captcha()
            if not captcha_solved:
                logger.warning("CAPTCHA solving failed - form may not submit")
                result["errors"].append("CAPTCHA solving failed")
            
            # Wait a moment for CAPTCHA solution to be processed
            await asyncio.sleep(2)
            
            # Submit the form
            logger.info("Submitting form...")
            await form_handler.submit_form(result)
            
            result["success"] = len(result["errors"]) == 0
            
        except Exception as e:
            logger.error(f"Application failed: {e}")
            result["errors"].append(str(e))
        
        finally:
            # Keep browser open for inspection
            logger.info("Keeping browser open for 30 seconds for inspection...")
            await asyncio.sleep(30)
            await self.browser_manager.close()
        
        return result
    
    async def _dismiss_cookies(self, page):
        """Dismiss cookie consent dialog."""
        try:
            dismiss_btn = await page.wait_for_selector(
                'button:has-text("Dismiss"), button:has-text("Accept")',
                timeout=3000
            )
            if dismiss_btn:
                await dismiss_btn.click()
                await asyncio.sleep(0.5)
                logger.info("Dismissed cookie consent")
        except:
            pass

