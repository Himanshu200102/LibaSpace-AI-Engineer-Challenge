"""Form filling handler for Lever job applications."""
import asyncio
import logging
from typing import Dict, Any, Optional
from playwright.async_api import Page
from core.llm_client import LLMClient
from utils.resume import ResumeHelper

logger = logging.getLogger(__name__)


class FormHandler:
    """Handles all form filling operations."""
    
    def __init__(self, page: Page, llm_client: Optional[LLMClient], resume_helper: ResumeHelper, 
                 resume_data: Dict[str, Any], resume_file_path: Optional[str] = None, 
                 job_description: str = ""):
        """Initialize form handler."""
        self.page = page
        self.llm_client = llm_client
        self.resume_helper = resume_helper
        self.resume_data = resume_data
        self.resume_file_path = resume_file_path
        self.job_description = job_description
    
    async def fill_basic_info(self, result: Dict[str, Any]):
        """Fill the basic info section - DIRECT from resume, no LLM needed."""
        personal = self.resume_data.get("personal_info", {})
        experience = self.resume_data.get("experience", [{}])
        
        # Basic fields to fill directly
        basic_fields = [
            ("Full name", personal.get("full_name", "")),
            ("Email", personal.get("email", "")),
            ("Phone", personal.get("phone", "")),
            ("Current company", experience[0].get("company", "") if experience else ""),
        ]
        
        for label_text, value in basic_fields:
            if not value:
                continue
            await self._fill_field_by_label(label_text, value, result)
        
        # Handle location separately (autocomplete)
        location = personal.get("location", "")
        if location:
            await self.fill_location(location, result)
    
    async def _fill_field_by_label(self, label_text: str, value: str, result: Dict[str, Any]):
        """Fill a field by finding it through its label text."""
        try:
            # Find the listitem containing this label
            listitem = await self.page.query_selector(f'li:has-text("{label_text}")')
            if not listitem:
                logger.warning(f"Field not found: {label_text}")
                return
            
            # Find the input/textarea inside
            input_field = await listitem.query_selector('input, textarea')
            if not input_field:
                logger.warning(f"Input not found in: {label_text}")
                return
            
            # Fill it
            await input_field.click()
            await asyncio.sleep(0.1)
            await input_field.fill(value)
            await asyncio.sleep(0.2)
            
            result["fields_filled"].append(label_text.lower().replace(" ", "_"))
            logger.info(f"Filled {label_text}: {value[:30]}...")
            
        except Exception as e:
            logger.warning(f"Could not fill {label_text}: {e}")
    
    async def fill_location(self, location: str, result: Dict[str, Any]):
        """Fill location with autocomplete - DIRECT value."""
        try:
            logger.info(f"Filling location: {location}")
            
            # Find location field by label
            listitem = await self.page.query_selector('li:has-text("Current location")')
            if not listitem:
                logger.warning("Location field not found")
                return
            
            # Get the visible input (first one)
            inputs = await listitem.query_selector_all('input')
            if not inputs:
                logger.warning("Location input not found")
                return
            
            element = inputs[0]  # First input is the visible one
            
            # Click and clear
            await element.click()
            await asyncio.sleep(0.3)
            await element.press("Control+a")
            await element.press("Backspace")
            await asyncio.sleep(0.2)
            
            # Type to trigger autocomplete
            logger.info("Typing location...")
            await element.type(location, delay=80)
            
            # Wait for suggestions
            logger.info("Waiting for dropdown...")
            await asyncio.sleep(2)
            
            # Select first option with keyboard
            logger.info("Selecting first suggestion...")
            await element.press("ArrowDown")
            await asyncio.sleep(0.3)
            await element.press("Enter")
            await asyncio.sleep(0.5)
            
            # Click elsewhere to close dropdown
            await self.page.click("body")
            await asyncio.sleep(0.3)
            
            result["fields_filled"].append("location")
            logger.info("Location filled successfully")
            
        except Exception as e:
            logger.warning(f"Location error: {e}")
            result["errors"].append(f"Location: {str(e)}")
    
    async def fill_application_form(self, result: Dict[str, Any]):
        """Fill application form - uses LLM for complex questions."""
        
        # Get all form questions (listitems in the application form section)
        form_items = await self.page.query_selector_all('li[class*="posting-field"]')
        if not form_items:
            # Try alternative selector
            form_items = await self.page.query_selector_all('form li')
        
        logger.info(f"Found {len(form_items)} form items")
        
        # First, handle all consent checkboxes
        await self.fill_all_consent_checkboxes(result)
        
        # Handle cover letter specifically
        await self.fill_cover_letter(result)
        
        # Track which items we've already processed (to avoid processing child items)
        processed_questions = set()
        
        for item in form_items:
            try:
                # Get the question text
                item_text = await item.inner_text()
                if not item_text or len(item_text.strip()) < 3:
                    continue
                
                # Get first line as question (ignore option texts)
                lines = item_text.split('\n')
                question = lines[0].strip()
                
                # Check if this item has a dropdown/select field (even if question is short)
                has_dropdown = await item.query_selector('[role="combobox"], select')
                
                # Skip if this looks like just an option (short text without ?)
                # BUT don't skip if it has a dropdown (like "Ethnicity", "Gender", etc.)
                if len(question) < 10 and "?" not in question and "✱" not in question and "*" not in question:
                    if not has_dropdown:
                        continue  # Skip only if it doesn't have a dropdown
                
                # Skip already processed or basic fields
                basic_labels = ["full name", "email", "phone", "current location", "current company", "resume", "linkedin", "cv"]
                if any(label in question.lower() for label in basic_labels):
                    continue
                
                # Skip if we already processed a similar question
                question_key = question.lower()[:30]
                if question_key in processed_questions:
                    continue
                processed_questions.add(question_key)
                
                logger.info(f"Processing: {question[:50]}...")
                
                # Log diversity fields explicitly for debugging
                if any(word in question.lower() for word in ["ethnicity", "race", "ethnic", "gender", "diverse"]):
                    logger.info(f"🔍 DIVERSITY FIELD DETECTED: {question[:50]}")
                
                # Determine field type and fill accordingly
                dropdown = await item.query_selector('[role="combobox"], select')
                radio_buttons = await item.query_selector_all('input[type="radio"]')
                checkbox_buttons = await item.query_selector_all('input[type="checkbox"]')
                text_input = await item.query_selector('input[type="text"]:not([type="hidden"]), textarea')
                
                filled = False
                
                # Priority: Handle dropdowns first, especially diversity fields
                if dropdown:
                    # For diversity fields, ensure we fill them
                    if any(word in question.lower() for word in ["ethnicity", "race", "ethnic", "gender", "age bracket", "veteran", "disability"]):
                        logger.info(f"🔍 Filling diversity dropdown: {question[:50]}")
                    filled = await self.fill_dropdown_smart(item, question, result)
                elif len(radio_buttons) > 0:
                    filled = await self.fill_radio_smart(item, radio_buttons, question, result)
                elif len(checkbox_buttons) > 0:
                    filled = await self.fill_checkbox_smart(item, checkbox_buttons, question, result)
                elif text_input:
                    filled = await self.fill_text_smart(item, text_input, question, result)
                
                if not filled:
                    logger.warning(f"Could not fill: {question[:40]}...")
                    
            except Exception as e:
                logger.warning(f"Error processing form item: {e}")
    
    async def fill_diversity_fields(self, result: Dict[str, Any]):
        """Explicitly find and fill diversity fields (ethnicity, gender, etc.)."""
        try:
            logger.info("Checking diversity fields...")
            
            # Find all form items that might contain diversity fields
            form_items = await self.page.query_selector_all('form li')
            
            for item in form_items:
                try:
                    item_text = await item.inner_text()
                    if not item_text:
                        continue
                    
                    question = item_text.split('\n')[0].strip()
                    
                    # Check if this is a diversity field
                    is_diversity = any(word in question.lower() for word in 
                                     ["ethnicity", "race", "ethnic", "gender", "age bracket", "veteran", "disability"])
                    
                    if is_diversity:
                        # Check if it has a dropdown
                        dropdown = await item.query_selector('[role="combobox"], select')
                        if dropdown:
                            # Check if already filled
                            current_text = await dropdown.inner_text()
                            if current_text and "Select" not in current_text and len(current_text.strip()) > 3:
                                logger.info(f"Diversity field already filled: {question[:30]} = {current_text[:20]}")
                                continue
                            
                            # Fill it
                            logger.info(f"🔍 Filling diversity field: {question[:30]}")
                            filled = await self.fill_dropdown_smart(item, question, result)
                            if filled:
                                logger.info(f"✓ Successfully filled diversity field: {question[:30]}")
                            else:
                                logger.warning(f"Failed to fill diversity field: {question[:30]}")
                except Exception as e:
                    logger.debug(f"Error checking diversity field: {e}")
                    continue
                    
        except Exception as e:
            logger.warning(f"Diversity fields check error: {e}")
    
    async def fill_all_consent_checkboxes(self, result: Dict[str, Any]):
        """Find and check all consent checkboxes based on preferences."""
        try:
            logger.info("Looking for consent checkboxes...")
            
            # Get consent preferences from resume.json
            consent_prefs = self.resume_helper.get_consent_preferences()
            auto_check_consent = consent_prefs.get("auto_check_consent", True)
            auto_check_terms = consent_prefs.get("auto_check_terms", True)
            auto_check_privacy = consent_prefs.get("auto_check_privacy", True)
            
            if not (auto_check_consent or auto_check_terms or auto_check_privacy):
                logger.info("Consent auto-check disabled in preferences")
                return
            
            # Find all checkboxes that look like consent
            checkboxes = await self.page.query_selector_all('input[type="checkbox"]')
            
            for checkbox in checkboxes:
                try:
                    is_checked = await checkbox.is_checked()
                    if not is_checked:
                        # Check the parent for consent-related text
                        parent = await checkbox.evaluate_handle("el => el.closest('label') || el.closest('li') || el.parentElement")
                        if parent:
                            text = await parent.evaluate("el => el.innerText || ''")
                            text_lower = text.lower()
                            
                            # Check consent boxes
                            if auto_check_consent and any(word in text_lower for word in ["consent", "agree", "accept", "acknowledge", "confirm"]):
                                await checkbox.click()
                                await asyncio.sleep(0.2)
                                logger.info(f"Checked consent: {text[:40]}... (from preferences)")
                                result["fields_filled"].append("consent_checkbox")
                            
                            # Check terms boxes
                            elif auto_check_terms and "terms" in text_lower:
                                await checkbox.click()
                                await asyncio.sleep(0.2)
                                logger.info(f"Checked terms: {text[:40]}... (from preferences)")
                                result["fields_filled"].append("terms_checkbox")
                            
                            # Check privacy boxes
                            elif auto_check_privacy and "privacy" in text_lower:
                                await checkbox.click()
                                await asyncio.sleep(0.2)
                                logger.info(f"Checked privacy: {text[:40]}... (from preferences)")
                                result["fields_filled"].append("privacy_checkbox")
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"Consent checkbox error: {e}")
    
    async def fill_cover_letter(self, result: Dict[str, Any]):
        """Fill cover letter field with LLM-generated content."""
        try:
            logger.info("Looking for cover letter field...")
            
            # Find cover letter field by looking for textarea in relevant sections
            textarea = None
            
            # Method 1: Find by label text
            cover_letter_item = await self.page.query_selector('li:has-text("cover letter")')
            if cover_letter_item:
                textarea = await cover_letter_item.query_selector('textarea')
            
            # Method 2: Find textarea with cover letter placeholder
            if not textarea:
                textareas = await self.page.query_selector_all('textarea')
                for ta in textareas:
                    placeholder = await ta.get_attribute("placeholder") or ""
                    aria_label = await ta.get_attribute("aria-label") or ""
                    combined = (placeholder + aria_label).lower()
                    if "cover" in combined or "letter" in combined or "why" in combined:
                        textarea = ta
                        break
            
            # Method 3: Find in "Additional Information" section
            if not textarea:
                additional_section = await self.page.query_selector('li:has-text("Additional")')
                if additional_section:
                    textarea = await additional_section.query_selector('textarea')
            
            if not textarea:
                logger.info("No cover letter field found")
                return
            
            # Check if already filled
            current_value = await textarea.input_value()
            if current_value and len(current_value) > 50:
                logger.info("Cover letter already filled")
                return
            
            # Generate cover letter with LLM
            if self.llm_client:
                cover_letter = self.llm_client.ask(
                    "Write a professional cover letter for this job application",
                    self.resume_data,
                    self.job_description,
                    """Write a concise, professional cover letter (3-4 paragraphs).
                    - Express enthusiasm for the role
                    - Highlight relevant experience from the resume
                    - Match skills to job requirements
                    - Keep it under 250 words
                    - Do NOT include [brackets] or placeholder text"""
                )
                
                if cover_letter:
                    await textarea.click()
                    await asyncio.sleep(0.1)
                    await textarea.fill(cover_letter)
                    await asyncio.sleep(0.2)
                    result["fields_filled"].append("cover_letter")
                    logger.info(f"Filled cover letter ({len(cover_letter)} chars)")
            else:
                # Default cover letter
                default_letter = f"""Dear Hiring Manager,

I am writing to express my strong interest in this position. With my background in {self.resume_data.get('experience', [{}])[0].get('position', 'the field')}, I am confident I can make valuable contributions to your team.

My experience has equipped me with the skills needed to excel in this role. I am particularly drawn to this opportunity because it aligns with my career goals and expertise.

Thank you for considering my application. I look forward to the opportunity to discuss how I can contribute to your organization.

Best regards,
{self.resume_data.get('personal_info', {}).get('full_name', 'Candidate')}"""
                
                await textarea.click()
                await asyncio.sleep(0.1)
                await textarea.fill(default_letter)
                await asyncio.sleep(0.2)
                result["fields_filled"].append("cover_letter")
                logger.info("Filled default cover letter")
                
        except Exception as e:
            logger.warning(f"Cover letter error: {e}")
    
    async def fill_dropdown_smart(self, item, question: str, result: Dict[str, Any]) -> bool:
        """Fill dropdown with smart option selection. Returns True if filled."""
        try:
            dropdown = await item.query_selector('[role="combobox"]')
            if not dropdown:
                dropdown = await item.query_selector('select')
            if not dropdown:
                return False
            
            # Check if already selected
            current_text = await dropdown.inner_text()
            if current_text:
                lines = current_text.strip().split('\n')
                if len(lines) > 1 or any(word in current_text.lower() for word in ["male", "female", "select", "choose"]):
                    pass
                elif current_text.strip() and "Select" not in current_text:
                    logger.info(f"Dropdown already filled: {question[:30]}... = {current_text[:20]}")
                    return True
            
            # Click to open dropdown and ensure focus
            await dropdown.scroll_into_view_if_needed()
            await asyncio.sleep(0.1)
            await dropdown.click()
            await asyncio.sleep(0.4)
            await dropdown.focus()
            await asyncio.sleep(0.1)
            
            # Get available options
            option_selectors = [
                '[role="option"]',
                '[role="listbox"] > div',
                '[class*="dropdown"] li',
                '[class*="dropdown"] div[class*="option"]',
                'ul[class*="dropdown"] li',
            ]
            
            options = []
            for sel in option_selectors:
                options = await self.page.query_selector_all(sel)
                if len(options) > 1:
                    break
            
            option_texts = []
            option_elements = []
            
            for opt in options:
                try:
                    text = await opt.inner_text()
                    text = text.strip()
                    if text and text != "Select..." and text != "Select" and len(text) > 0:
                        option_texts.append(text)
                        option_elements.append(opt)
                except:
                    continue
            
            # If still no options, try getting them from the dropdown itself
            if not option_texts:
                try:
                    dropdown_options = await dropdown.query_selector_all('option, [role="option"], div')
                    for opt in dropdown_options:
                        text = await opt.inner_text()
                        text = text.strip()
                        if text and text != "Select..." and text != "Select":
                            option_texts.append(text)
                            option_elements.append(opt)
                except:
                    pass
            
            logger.info(f"Found {len(option_texts)} options for '{question[:30]}'")
            
            if not option_texts:
                # Last resort: try keyboard navigation
                logger.info("No visible options found, trying keyboard navigation...")
                q_lower = question.lower()
                if any(word in q_lower for word in ["gender", "ethnicity", "race", "ethnic", "age bracket", "veteran", "disability"]):
                    for i in range(10):
                        await self.page.keyboard.press("ArrowDown")
                        await asyncio.sleep(0.1)
                        current_text = await dropdown.inner_text()
                        if current_text and any(phrase in current_text.lower() for phrase in ["prefer not", "decline", "not to say"]):
                            await self.page.keyboard.press("Enter")
                            await asyncio.sleep(0.2)
                            result["fields_filled"].append(f"dropdown_{question[:20]}")
                            logger.info(f"✓ Selected 'Prefer not to say' via keyboard")
                            return True
                    await self.page.keyboard.press("Enter")
                    await asyncio.sleep(0.2)
                    result["fields_filled"].append(f"dropdown_{question[:20]}")
                    logger.info(f"✓ Selected option via keyboard (diversity field)")
                    return True
                
                await self.page.keyboard.press("ArrowDown")
                await asyncio.sleep(0.2)
                await self.page.keyboard.press("Enter")
                await asyncio.sleep(0.2)
                result["fields_filled"].append(f"dropdown_{question[:20]}")
                logger.info(f"✓ Selected first option via keyboard")
                return True
            
            # Determine best option
            q_lower = question.lower()
            best_match = None
            
            # 1. Diversity fields
            if any(word in q_lower for word in ["gender", "ethnicity", "race", "age bracket", "veteran", "disability", "diversity"]):
                for opt in option_texts:
                    if "prefer not" in opt.lower() or "decline" in opt.lower():
                        best_match = opt
                        break
            
            # 2. Use resume helper for defaults
            if not best_match:
                best_match = self.resume_helper.get_default_dropdown_value(question, option_texts)
            
            # 3. Use LLM for unknown fields
            if not best_match and self.llm_client:
                llm_answer = self.llm_client.ask(
                    f"Question: {question}",
                    self.resume_data,
                    self.job_description,
                    f"Available options: {', '.join(option_texts[:15])}\n\nBased on the candidate's resume, which option should be selected? Reply with ONLY the exact option text, nothing else."
                )
                for opt in option_texts:
                    if opt.lower() == llm_answer.lower() or opt.lower() in llm_answer.lower() or llm_answer.lower() in opt.lower():
                        best_match = opt
                        break
            
            # 4. Default: first option
            if not best_match and option_texts:
                best_match = option_texts[0]
            
            # Select the option - KEYBOARD FIRST
            if best_match:
                logger.info(f"Selecting '{best_match}' for '{question[:30]}'")
                
                # METHOD 1: Keyboard navigation
                for i, opt_text in enumerate(option_texts):
                    if opt_text == best_match:
                        try:
                            for _ in range(i + 1):
                                await self.page.keyboard.press("ArrowDown")
                                await asyncio.sleep(0.05)
                            
                            await self.page.keyboard.press("Enter")
                            await asyncio.sleep(0.5)
                            
                            try:
                                is_open = await dropdown.evaluate("el => el.getAttribute('aria-expanded') === 'true'")
                                if not is_open:
                                    result["fields_filled"].append(f"dropdown_{question[:20]}")
                                    logger.info(f"✓ Selected '{best_match}' via keyboard (dropdown closed)")
                                    return True
                                
                                new_text = await dropdown.inner_text()
                                if new_text and "Select" not in new_text and len(new_text.strip().split('\n')) <= 2:
                                    result["fields_filled"].append(f"dropdown_{question[:20]}")
                                    logger.info(f"✓ Selected '{best_match}' via keyboard (text changed)")
                                    return True
                                
                                result["fields_filled"].append(f"dropdown_{question[:20]}")
                                logger.info(f"✓ Selected '{best_match}' via keyboard (assumed success)")
                                return True
                            except Exception as verify_error:
                                logger.debug(f"Verification error (assuming success): {verify_error}")
                                result["fields_filled"].append(f"dropdown_{question[:20]}")
                                logger.info(f"✓ Selected '{best_match}' via keyboard")
                                return True
                        except Exception as e:
                            logger.debug(f"Keyboard navigation failed: {e}")
                            break
                
                # METHOD 2: Fallback - try clicking
                logger.debug("Keyboard failed, trying click...")
                for i, opt_text in enumerate(option_texts):
                    if opt_text == best_match:
                        try:
                            await option_elements[i].click()
                            await asyncio.sleep(0.3)
                            result["fields_filled"].append(f"dropdown_{question[:20]}")
                            logger.info(f"✓ Selected '{best_match}' via click")
                            return True
                        except Exception as e:
                            logger.debug(f"Click failed: {e}")
                            break
            
            # Close dropdown
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(0.2)
            return False
            
        except Exception as e:
            logger.warning(f"Dropdown error for '{question[:30]}': {e}")
            try:
                await self.page.keyboard.press("Escape")
            except:
                pass
            return False
    
    async def fill_radio_smart(self, item, radio_buttons, question: str, result: Dict[str, Any]) -> bool:
        """Fill radio buttons with smart selection. Returns True if filled."""
        try:
            # Check if any is already selected
            for radio in radio_buttons:
                if await radio.is_checked():
                    logger.info(f"Radio already selected for: {question[:30]}...")
                    return True
            
            # Get option labels
            option_texts = []
            option_labels = []
            for radio in radio_buttons:
                try:
                    label = await radio.evaluate_handle("el => el.closest('label') || el.parentElement.querySelector('label')")
                    if label:
                        text = await label.evaluate("el => el.innerText || ''")
                        text = text.strip()
                        if text:
                            option_texts.append(text)
                            option_labels.append(label)
                except:
                    continue
            
            if not option_texts:
                return False
            
            logger.info(f"Radio options for '{question[:30]}': {option_texts[:5]}")
            
            # Determine best option
            q_lower = question.lower()
            best_match = None
            
            # Yes/No questions - smart defaults
            if set(opt.lower() for opt in option_texts) == {"yes", "no"}:
                if any(word in q_lower for word in ["open to", "willing", "available", "interested", "able to", "authorized"]):
                    best_match = next((opt for opt in option_texts if opt.lower() == "yes"), None)
                elif any(word in q_lower for word in ["require", "need", "visa"]):
                    best_match = next((opt for opt in option_texts if opt.lower() == "no"), None)
            
            # Use LLM if no match
            if not best_match and self.llm_client:
                llm_answer = self.llm_client.ask(
                    f"Question: {question}",
                    self.resume_data,
                    self.job_description,
                    f"Available options: {', '.join(option_texts)}\n\nBased on the candidate's resume, which option should be selected? Reply with ONLY the exact option text."
                )
                for opt in option_texts:
                    if opt.lower() == llm_answer.lower() or opt.lower() in llm_answer.lower():
                        best_match = opt
                        break
            
            # Default: first option
            if not best_match:
                best_match = option_texts[0]
            
            # Click the matching label
            for i, opt_text in enumerate(option_texts):
                if opt_text == best_match:
                    try:
                        await option_labels[i].click()
                        await asyncio.sleep(0.2)
                        result["fields_filled"].append(f"radio_{question[:20]}")
                        logger.info(f"✓ Selected '{best_match}' for '{question[:30]}'")
                        return True
                    except:
                        pass
            
            return False
            
        except Exception as e:
            logger.warning(f"Radio error: {e}")
            return False
    
    async def fill_checkbox_smart(self, item, checkboxes, question: str, result: Dict[str, Any]) -> bool:
        """Fill checkboxes - consent boxes and relevant options. Returns True if any checked."""
        try:
            checked_any = False
            consent_prefs = self.resume_helper.get_consent_preferences()
            auto_check_consent = consent_prefs.get("auto_check_consent", True)
            auto_check_terms = consent_prefs.get("auto_check_terms", True)
            auto_check_privacy = consent_prefs.get("auto_check_privacy", True)
            
            for checkbox in checkboxes:
                try:
                    if await checkbox.is_checked():
                        checked_any = True
                        continue
                    
                    label_text = await checkbox.evaluate("el => el.closest('label')?.innerText || el.parentElement?.innerText || ''")
                    label_lower = label_text.lower()
                    
                    if auto_check_consent and any(word in label_lower for word in ["consent", "agree", "accept", "acknowledge", "confirm"]):
                        await checkbox.click()
                        await asyncio.sleep(0.2)
                        logger.info(f"✓ Checked consent: {label_text[:40]} (from preferences)")
                        checked_any = True
                        continue
                    
                    if auto_check_terms and "terms" in label_lower:
                        await checkbox.click()
                        await asyncio.sleep(0.2)
                        logger.info(f"✓ Checked terms: {label_text[:40]} (from preferences)")
                        checked_any = True
                        continue
                    
                    if auto_check_privacy and "privacy" in label_lower:
                        await checkbox.click()
                        await asyncio.sleep(0.2)
                        logger.info(f"✓ Checked privacy: {label_text[:40]} (from preferences)")
                        checked_any = True
                        continue
                    
                    # For other checkboxes, use LLM if available
                    if self.llm_client:
                        should_check = self.llm_client.ask(
                            f"Question: {question}\nOption: {label_text}",
                            self.resume_data,
                            self.job_description,
                            "Should this checkbox be selected based on the candidate's resume? Answer only 'yes' or 'no'."
                        )
                        if "yes" in should_check.lower():
                            await checkbox.click()
                            await asyncio.sleep(0.2)
                            logger.info(f"✓ Checked: {label_text[:30]}")
                            checked_any = True
                except:
                    continue
            
            if checked_any:
                result["fields_filled"].append(f"checkbox_{question[:20]}")
            
            return checked_any
            
        except Exception as e:
            logger.warning(f"Checkbox error: {e}")
            return False
    
    async def fill_text_smart(self, item, text_input, question: str, result: Dict[str, Any]) -> bool:
        """Fill text field with resume data or LLM answer. Returns True if filled."""
        try:
            # Check if already filled
            current_value = await text_input.input_value()
            if current_value and len(current_value.strip()) > 0:
                logger.info(f"Text field already filled: {question[:30]}...")
                return True
            
            # Get answer from resume first
            answer = self.resume_helper.get_answer(question)
            
            # If not in resume, use LLM
            if not answer and self.llm_client:
                answer = self.llm_client.ask(
                    f"Question: {question}",
                    self.resume_data,
                    self.job_description,
                    "Based on the candidate's resume, provide a concise professional answer. Keep it brief (1-2 sentences for short answer, 3-4 for longer questions)."
                )
            
            if answer:
                await text_input.scroll_into_view_if_needed()
                await asyncio.sleep(0.1)
                await text_input.click()
                await asyncio.sleep(0.1)
                await text_input.fill(answer)
                await asyncio.sleep(0.2)
                result["fields_filled"].append(f"text_{question[:20]}")
                logger.info(f"✓ Filled '{question[:30]}': {answer[:30]}...")
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Text field error: {e}")
            return False
    
    async def upload_resume(self, result: Dict[str, Any]):
        """Upload resume file."""
        try:
            resume_item = await self.page.query_selector('li:has-text("Resume")')
            if not resume_item:
                resume_item = await self.page.query_selector('li:has-text("CV")')
            
            if resume_item:
                attach_link = await resume_item.query_selector('a:has-text("ATTACH")')
                if attach_link:
                    await attach_link.click()
                    await asyncio.sleep(0.5)
            
            file_input = await self.page.query_selector('input[type="file"]')
            if file_input and self.resume_file_path:
                await file_input.set_input_files(self.resume_file_path)
                await asyncio.sleep(2)
                result["fields_filled"].append("resume")
                logger.info("Resume uploaded")
            else:
                logger.warning("Resume file input not found or no file provided")
                
        except Exception as e:
            logger.warning(f"Resume upload error: {e}")
            result["errors"].append(f"Resume: {str(e)}")
    
    async def verify_and_fill_empty_fields(self, result: Dict[str, Any]):
        """Verify all fields are filled and re-fill empty ones."""
        logger.info("Scanning all form fields for empty values...")
        
        # First, explicitly check and fill diversity fields
        await self.fill_diversity_fields(result)
        
        # Then check consent checkboxes again
        await self.fill_all_consent_checkboxes(result)
        
        # Get all form items
        form_items = await self.page.query_selector_all('form li')
        empty_fields = []
        
        for item in form_items:
            try:
                item_text = await item.inner_text()
                if not item_text:
                    continue
                    
                question = item_text.split('\n')[0].strip()
                has_dropdown = await item.query_selector('[role="combobox"], select')
                
                if len(question) < 15 and "?" not in question and "✱" not in question:
                    if not has_dropdown:
                        continue
                
                if any(skip in question.lower() for skip in ["linkedin", "portfolio", "website", "github"]):
                    continue
                
                words = question.split()
                is_diversity_field = any(word in question.lower() for word in ["ethnicity", "race", "ethnic", "gender", "age bracket", "veteran", "disability"])
                if len(words) <= 3 and "?" not in question and "✱" not in question and "*" not in question:
                    if not is_diversity_field and not has_dropdown:
                        continue
                
                # Check different field types
                text_input = await item.query_selector('input[type="text"], textarea')
                if text_input:
                    value = await text_input.input_value()
                    if not value or value.strip() == "":
                        empty_fields.append(("text", item, question))
                        logger.warning(f"EMPTY TEXT: {question[:50]}...")
                    continue
                
                dropdown = await item.query_selector('[role="combobox"], select')
                if dropdown:
                    # Check if dropdown actually has a value selected
                    # For Lever comboboxes, check the input element inside
                    is_filled = await dropdown.evaluate('''
                        (el) => {
                            // For select elements, check if a real option is selected
                            if (el.tagName === 'SELECT') {
                                return el.selectedIndex > 0 && el.value && el.value !== '' && el.value !== 'Select';
                            }
                            
                            // For combobox (Lever style), check the input element
                            const input = el.querySelector('input[type="text"], input[type="hidden"]');
                            if (input) {
                                const value = input.value || input.getAttribute('value') || '';
                                const trimmed = value.trim();
                                // Check if it has a real value (not empty, not "Select", not placeholder)
                                if (trimmed && trimmed.length > 2 && !trimmed.toLowerCase().includes('select')) {
                                    return true;
                                }
                            }
                            
                            // Check if dropdown is open (if open, might not be filled, but could be false positive)
                            const isOpen = el.getAttribute('aria-expanded') === 'true';
                            
                            // Check for selected option visible
                            const selectedOption = el.querySelector('[aria-selected="true"], .selected, option[selected]');
                            if (selectedOption && selectedOption.textContent) {
                                const text = selectedOption.textContent.trim();
                                if (text && text.length > 2 && !text.toLowerCase().includes('select')) {
                                    return true;
                                }
                            }
                            
                            // Check the visible text - if it's a single line and not "Select", it's probably filled
                            const text = el.textContent || el.innerText || '';
                            const lines = text.trim().split('\\n').filter(l => l.trim());
                            // If only one line (or two with one being the selected value), and it's not "Select"
                            if (lines.length <= 2) {
                                const firstLine = lines[0] ? lines[0].trim() : '';
                                if (firstLine && firstLine.length > 2 && 
                                    !firstLine.toLowerCase().startsWith('select') &&
                                    !firstLine.toLowerCase().includes('select...')) {
                                    // Don't check if dropdown is open - just check if it looks filled
                                    return true;
                                }
                            }
                            
                            return false;
                        }
                    ''')
                    
                    if not is_filled:
                        # Double-check by looking at the input value directly
                        input_elem = await dropdown.query_selector('input[type="text"], input[type="hidden"]')
                        if input_elem:
                            input_value = await input_elem.input_value()
                            if input_value and input_value.strip() and len(input_value.strip()) > 2 and "select" not in input_value.lower():
                                is_filled = True
                        
                        if not is_filled:
                            dropdown_text = await dropdown.inner_text()
                            empty_fields.append(("dropdown", item, question))
                            logger.warning(f"EMPTY DROPDOWN: {question[:50]}... (text: '{dropdown_text[:30]}')")
                    continue
                
                radios = await item.query_selector_all('input[type="radio"]')
                if len(radios) > 1:
                    any_checked = False
                    for radio in radios:
                        if await radio.is_checked():
                            any_checked = True
                            break
                    if not any_checked:
                        empty_fields.append(("radio", item, question))
                        logger.warning(f"EMPTY RADIO GROUP: {question[:50]}...")
                    continue
                
                checkbox = await item.query_selector('input[type="checkbox"]')
                if checkbox:
                    is_checked = await checkbox.is_checked()
                    if not is_checked:
                        if any(word in question.lower() for word in ["consent", "agree", "accept", "acknowledge"]):
                            empty_fields.append(("checkbox", item, question))
                            logger.warning(f"UNCHECKED CONSENT: {question[:50]}...")
                    continue
                    
            except Exception as e:
                logger.debug(f"Error checking field: {e}")
        
        # Re-fill empty fields
        if empty_fields:
            logger.info(f"Found {len(empty_fields)} empty fields. Re-filling...")
            
            for field_type, item, question in empty_fields:
                try:
                    logger.info(f"Re-filling: {question[:40]}...")
                    
                    if field_type == "text":
                        text_input = await item.query_selector('input[type="text"], textarea')
                        if text_input:
                            await self.fill_text_smart(item, text_input, question, result)
                    
                    elif field_type == "dropdown":
                        await self.fill_dropdown_smart(item, question, result)
                    
                    elif field_type == "radio":
                        radios = await item.query_selector_all('input[type="radio"]')
                        if radios:
                            await self.fill_radio_smart(item, radios, question, result)
                    
                    elif field_type == "checkbox":
                        checkbox = await item.query_selector('input[type="checkbox"]')
                        if checkbox:
                            await checkbox.click()
                            await asyncio.sleep(0.2)
                            result["fields_filled"].append(f"checkbox_{question[:20]}")
                            logger.info(f"Checked: {question[:40]}")
                    
                    await asyncio.sleep(0.3)
                    
                except Exception as e:
                    logger.warning(f"Error re-filling {question[:30]}: {e}")
                    result["fields_empty"].append(question[:50])
        else:
            logger.info("All fields appear to be filled!")
    
    async def final_verification(self, result: Dict[str, Any]):
        """Final check of all required fields."""
        logger.info("Performing final verification...")
        
        all_filled = True
        form_items = await self.page.query_selector_all('form li')
        
        for item in form_items:
            try:
                item_text = await item.inner_text()
                if not item_text:
                    continue
                    
                question = item_text.split('\n')[0].strip()
                
                if len(question) < 15 and "?" not in question and "✱" not in question:
                    continue
                
                words = question.split()
                if len(words) <= 3 and "?" not in question and "✱" not in question:
                    continue
                
                if any(skip in question.lower() for skip in ["linkedin", "website", "portfolio", "additional"]):
                    continue
                
                is_required = "✱" in item_text or "*" in item_text
                if not is_required:
                    continue
                
                # Check text inputs
                text_input = await item.query_selector('input[type="text"], textarea')
                if text_input:
                    value = await text_input.input_value()
                    if not value or value.strip() == "":
                        logger.error(f"STILL EMPTY: {question[:50]}...")
                        result["fields_empty"].append(question[:50])
                        all_filled = False
                    else:
                        logger.info(f"✓ {question[:40]}: {value[:20]}...")
                    continue
                
                # Check dropdowns
                dropdown = await item.query_selector('[role="combobox"]')
                if dropdown:
                    dropdown_text = await dropdown.inner_text()
                    if "Select" in dropdown_text:
                        logger.error(f"STILL EMPTY: {question[:50]}...")
                        result["fields_empty"].append(question[:50])
                        all_filled = False
                    else:
                        logger.info(f"✓ {question[:40]}: {dropdown_text[:20]}...")
                    continue
                
                # Check radios
                radios = await item.query_selector_all('input[type="radio"]')
                if radios:
                    any_checked = False
                    for radio in radios:
                        if await radio.is_checked():
                            any_checked = True
                            break
                    if not any_checked:
                        logger.error(f"STILL EMPTY: {question[:50]}...")
                        result["fields_empty"].append(question[:50])
                        all_filled = False
                    else:
                        logger.info(f"✓ {question[:40]}: (selected)")
                        
            except Exception as e:
                logger.debug(f"Verification error: {e}")
        
        if all_filled:
            logger.info("=" * 50)
            logger.info("✓ ALL REQUIRED FIELDS ARE FILLED!")
            logger.info("=" * 50)
        else:
            logger.warning("=" * 50)
            logger.warning(f"⚠ {len(result['fields_empty'])} required fields still empty")
            logger.warning("=" * 50)
    
    async def check_captcha(self) -> bool:
        """Check if CAPTCHA is present."""
        captcha_selectors = [
            'iframe[src*="captcha"]',
            'iframe[src*="challenge"]',
            '[class*="captcha"]',
            '.g-recaptcha',
            '.h-captcha',
            '[data-sitekey]',
        ]
        
        for sel in captcha_selectors:
            try:
                element = await self.page.query_selector(sel)
                if element:
                    return True
            except:
                continue
        
        return False
    
    async def solve_captcha(self) -> bool:
        """Detect and solve CAPTCHA using extension or direct API.
        
        Returns:
            True if CAPTCHA was solved, False otherwise
        """
        try:
            logger.info("Checking for CAPTCHA...")
            has_captcha = await self.check_captcha()
            
            if not has_captcha:
                logger.info("No CAPTCHA detected")
                return True
            
            logger.info("CAPTCHA detected, attempting to solve...")
            
            # Detect CAPTCHA type and extract site key
            detection_result = await self.page.evaluate('''
                () => {
                    const pageUrl = window.location.href;
                    let captchaType = null;
                    let siteKey = null;
                    
                    // Check for reCAPTCHA v2
                    const recaptchaElement = document.querySelector('.g-recaptcha, [data-sitekey]');
                    if (recaptchaElement) {
                        siteKey = recaptchaElement.getAttribute('data-sitekey');
                        if (siteKey) {
                            captchaType = 'recaptcha_v2';
                        }
                    }
                    
                    // Check for hCaptcha
                    if (!captchaType) {
                        const hcaptchaElement = document.querySelector('.h-captcha');
                        if (hcaptchaElement) {
                            siteKey = hcaptchaElement.getAttribute('data-sitekey');
                            if (siteKey) {
                                captchaType = 'hcaptcha';
                            }
                        }
                    }
                    
                    // Check iframes for site keys
                    if (!siteKey) {
                        const iframes = document.querySelectorAll('iframe[src*="recaptcha"], iframe[src*="hcaptcha"]');
                        iframes.forEach(iframe => {
                            try {
                                const src = iframe.src;
                                if (src.includes('recaptcha')) {
                                    const match = src.match(/[&?]k=([^&]+)/);
                                    if (match) {
                                        siteKey = match[1];
                                        captchaType = 'recaptcha_v2';
                                    }
                                } else if (src.includes('hcaptcha')) {
                                    const match = src.match(/[&?]sitekey=([^&]+)/);
                                    if (match) {
                                        siteKey = match[1];
                                        captchaType = 'hcaptcha';
                                    }
                                }
                            } catch (e) {
                                // Cross-origin
                            }
                        });
                    }
                    
                    return { captchaType, siteKey, pageUrl };
                }
            ''')
            
            if not detection_result or not detection_result.get('captchaType') or not detection_result.get('siteKey'):
                logger.warning("Could not detect CAPTCHA type or site key")
                return False
            
            captcha_type = detection_result['captchaType']
            site_key = detection_result['siteKey']
            page_url = detection_result['pageUrl']
            
            logger.info(f"Detected {captcha_type} CAPTCHA, site key: {site_key[:20]}...")
            
            # Try to solve via extension (if available)
            # Extension will handle solving and injection automatically
            # But we can also trigger it via JavaScript
            
            # Trigger extension to solve via message
            try:
                solved = await self.page.evaluate(f'''
                    async () => {{
                        // Check if extension is available
                        if (window.__captchaDetection) {{
                            // Extension detected CAPTCHA, trigger solve
                            return new Promise((resolve) => {{
                                chrome.runtime.sendMessage({{
                                    action: 'solveCaptcha',
                                    captchaType: '{captcha_type}',
                                    siteKey: '{site_key}',
                                    pageUrl: '{page_url}'
                                }}, (response) => {{
                                    resolve(response && response.success);
                                }});
                            }});
                        }}
                        return false;
                    }}
                ''')
                
                if solved:
                    logger.info("CAPTCHA solved via extension")
                    await asyncio.sleep(2)  # Wait for injection
                    return True
            except Exception as e:
                logger.debug(f"Extension solve failed (expected if extension not available): {e}")
            
            # Fallback: Use direct API if extension not available
            # Import here to avoid circular dependency
            from automation.captcha_solver import CaptchaSolver
            
            solver = CaptchaSolver()
            solution = solver.solve_by_type(captcha_type, site_key, page_url)
            
            if solution:
                logger.info("CAPTCHA solved via API, injecting solution...")
                
                # Inject solution
                injected = await self.page.evaluate(f'''
                    (solution) => {{
                        let success = false;
                        
                        if ('{captcha_type}' === 'recaptcha_v2') {{
                            const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                            if (textarea) {{
                                textarea.value = solution;
                                textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                success = true;
                            }}
                        }} else if ('{captcha_type}' === 'hcaptcha') {{
                            const textarea = document.querySelector('textarea[name="h-captcha-response"]');
                            if (textarea) {{
                                textarea.value = solution;
                                textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                success = true;
                            }}
                        }}
                        
                        return success;
                    }}
                ''', solution)
                
                if injected:
                    logger.info("Solution injected successfully")
                    await asyncio.sleep(1)
                    return True
                else:
                    logger.warning("Solution received but injection failed")
                    return False
            else:
                logger.error("Failed to solve CAPTCHA")
                return False
                
        except Exception as e:
            logger.error(f"Error solving CAPTCHA: {e}", exc_info=True)
            return False
    
    async def submit_form(self, result: Dict[str, Any]):
        """Submit the application form."""
        try:
            # Try multiple strategies to find the visible submit button
            submit_btn = None
            
            # Strategy 1: Look for visible submit button (excluding hidden hCaptcha buttons)
            try:
                submit_btn = await self.page.wait_for_selector(
                    'button[type="submit"]:not(.hidden):not([class*="hidden"]):visible, '
                    'button:has-text("Submit"):not(.hidden):not([class*="hidden"]):visible',
                    timeout=3000
                )
            except:
                pass
            
            # Strategy 2: Find all submit buttons and filter for visible ones
            if not submit_btn:
                try:
                    buttons = await self.page.query_selector_all('button[type="submit"], button:has-text("Submit")')
                    for btn in buttons:
                        # Check if button is visible (not hidden)
                        is_hidden = await btn.evaluate('''
                            el => {
                                const style = window.getComputedStyle(el);
                                return style.display === 'none' || 
                                       style.visibility === 'hidden' || 
                                       el.classList.contains('hidden') ||
                                       el.id.includes('hcaptcha');
                            }
                        ''')
                        if not is_hidden:
                            # Double check visibility
                            bounding_box = await btn.bounding_box()
                            if bounding_box and bounding_box['width'] > 0 and bounding_box['height'] > 0:
                                submit_btn = btn
                                break
                except Exception as e:
                    logger.debug(f"Strategy 2 failed: {e}")
            
            # Strategy 3: Look for Lever-specific submit button
            if not submit_btn:
                try:
                    submit_btn = await self.page.wait_for_selector(
                        'button[data-qa="submit"]:visible, '
                        'button.postings-btn-template__button:visible, '
                        'button.postings-btn:visible',
                        timeout=2000
                    )
                except:
                    pass
            
            if submit_btn:
                logger.info("Found submit button, clicking...")
                await submit_btn.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
                
                # Try to click
                try:
                    await submit_btn.click()
                except:
                    # Fallback: use JavaScript click
                    await submit_btn.evaluate('el => el.click()')
                
                await asyncio.sleep(3)
                
                # Check for success indicators
                success_indicators = [
                    'text="Thank you"',
                    'text="Application submitted"',
                    'text="success"',
                    '[data-qa="success"]'
                ]
                
                for indicator in success_indicators:
                    success = await self.page.query_selector(indicator)
                    if success:
                        result["fields_filled"].append("submitted")
                        logger.info("Application submitted successfully!")
                        return
                
                # If no success indicator found, check if we're still on the form page
                current_url = self.page.url
                if "apply" not in current_url.lower():
                    # URL changed, might have submitted
                    result["fields_filled"].append("submitted")
                    logger.info("Application likely submitted (URL changed)")
                else:
                    logger.warning("Submission status unclear - still on form page")
                    result["errors"].append("Submission status unclear")
            else:
                logger.error("Could not find visible submit button")
                result["errors"].append("Could not find submit button")
                    
        except Exception as e:
            logger.warning(f"Submit error: {e}")
            result["errors"].append(f"Submit: {str(e)}")

