"""CAPTCHA solving integration with 2Captcha API."""
import logging
import time
import requests
from typing import Optional, Dict, Any
from utils.config import CAPTCHA_API_KEY, CAPTCHA_SERVICE

logger = logging.getLogger(__name__)


class CaptchaSolver:
    """Handles CAPTCHA solving via 2Captcha API."""
    
    API_BASE_URL = "http://2captcha.com"
    
    def __init__(self, api_key: Optional[str] = None, service: str = "2captcha"):
        """Initialize CAPTCHA solver.
        
        Args:
            api_key: 2Captcha API key (defaults to config)
            service: CAPTCHA service provider (defaults to 2captcha)
        """
        self.api_key = api_key or CAPTCHA_API_KEY
        self.service = service or CAPTCHA_SERVICE
        
        if not self.api_key:
            logger.warning("No CAPTCHA API key provided. CAPTCHA solving will be disabled.")
    
    def get_balance(self) -> Optional[float]:
        """Check 2Captcha account balance.
        
        Returns:
            Account balance in USD, or None if error
        """
        if not self.api_key:
            return None
        
        try:
            response = requests.get(
                f"{self.API_BASE_URL}/res.php",
                params={
                    "key": self.api_key,
                    "action": "getbalance"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                balance = float(response.text)
                logger.info(f"2Captcha balance: ${balance:.2f}")
                return balance
            else:
                logger.error(f"Failed to get balance: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error checking balance: {e}")
            return None
    
    def solve_recaptcha_v2(self, site_key: str, page_url: str, timeout: int = 120) -> Optional[str]:
        """Solve reCAPTCHA v2.
        
        Args:
            site_key: reCAPTCHA site key
            page_url: URL of the page with CAPTCHA
            timeout: Maximum time to wait for solution (seconds)
        
        Returns:
            Solution token, or None if failed
        """
        if not self.api_key:
            logger.error("No CAPTCHA API key configured")
            return None
        
        logger.info(f"Solving reCAPTCHA v2 for site_key: {site_key[:20]}...")
        
        # Submit CAPTCHA to 2Captcha
        submit_url = f"{self.API_BASE_URL}/in.php"
        submit_params = {
            "key": self.api_key,
            "method": "userrecaptcha",
            "googlekey": site_key,
            "pageurl": page_url,
            "json": 1
        }
        
        try:
            response = requests.post(submit_url, data=submit_params, timeout=30)
            result = response.json()
            
            if result.get("status") != 1:
                logger.error(f"Failed to submit CAPTCHA: {result.get('request')}")
                return None
            
            task_id = result.get("request")
            logger.info(f"CAPTCHA submitted. Task ID: {task_id}")
            
            # Poll for solution
            return self._poll_for_solution(task_id, timeout)
            
        except Exception as e:
            logger.error(f"Error solving reCAPTCHA v2: {e}")
            return None
    
    def solve_recaptcha_v3(self, site_key: str, page_url: str, action: str = "submit", timeout: int = 120) -> Optional[str]:
        """Solve reCAPTCHA v3.
        
        Args:
            site_key: reCAPTCHA site key
            page_url: URL of the page with CAPTCHA
            action: Action name for v3
            timeout: Maximum time to wait for solution (seconds)
        
        Returns:
            Solution token, or None if failed
        """
        if not self.api_key:
            logger.error("No CAPTCHA API key configured")
            return None
        
        logger.info(f"Solving reCAPTCHA v3 for site_key: {site_key[:20]}...")
        
        submit_url = f"{self.API_BASE_URL}/in.php"
        submit_params = {
            "key": self.api_key,
            "method": "userrecaptcha",
            "version": "v3",
            "googlekey": site_key,
            "pageurl": page_url,
            "action": action,
            "json": 1
        }
        
        try:
            response = requests.post(submit_url, data=submit_params, timeout=30)
            result = response.json()
            
            if result.get("status") != 1:
                logger.error(f"Failed to submit CAPTCHA: {result.get('request')}")
                return None
            
            task_id = result.get("request")
            logger.info(f"CAPTCHA submitted. Task ID: {task_id}")
            
            return self._poll_for_solution(task_id, timeout)
            
        except Exception as e:
            logger.error(f"Error solving reCAPTCHA v3: {e}")
            return None
    
    def solve_hcaptcha(self, site_key: str, page_url: str, timeout: int = 120) -> Optional[str]:
        """Solve hCaptcha.
        
        Args:
            site_key: hCaptcha site key
            page_url: URL of the page with CAPTCHA
            timeout: Maximum time to wait for solution (seconds)
        
        Returns:
            Solution token, or None if failed
        """
        if not self.api_key:
            logger.error("No CAPTCHA API key configured")
            return None
        
        logger.info(f"Solving hCaptcha for site_key: {site_key[:20]}...")
        
        submit_url = f"{self.API_BASE_URL}/in.php"
        submit_params = {
            "key": self.api_key,
            "method": "hcaptcha",
            "sitekey": site_key,
            "pageurl": page_url,
            "json": 1
        }
        
        try:
            response = requests.post(submit_url, data=submit_params, timeout=30)
            result = response.json()
            
            if result.get("status") != 1:
                logger.error(f"Failed to submit CAPTCHA: {result.get('request')}")
                return None
            
            task_id = result.get("request")
            logger.info(f"CAPTCHA submitted. Task ID: {task_id}")
            
            return self._poll_for_solution(task_id, timeout)
            
        except Exception as e:
            logger.error(f"Error solving hCaptcha: {e}")
            return None
    
    def _poll_for_solution(self, task_id: str, timeout: int = 120) -> Optional[str]:
        """Poll 2Captcha API for solution.
        
        Args:
            task_id: Task ID returned from submission
            timeout: Maximum time to wait (seconds)
        
        Returns:
            Solution token, or None if failed
        """
        get_url = f"{self.API_BASE_URL}/res.php"
        start_time = time.time()
        poll_interval = 5  # Poll every 5 seconds
        
        logger.info(f"Polling for solution (timeout: {timeout}s)...")
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(
                    get_url,
                    params={
                        "key": self.api_key,
                        "action": "get",
                        "id": task_id,
                        "json": 1
                    },
                    timeout=10
                )
                
                result = response.json()
                status = result.get("status")
                
                if status == 1:
                    solution = result.get("request")
                    logger.info("CAPTCHA solved successfully!")
                    return solution
                elif status == 0:
                    # Still processing
                    if "CAPCHA_NOT_READY" in result.get("request", ""):
                        logger.debug("CAPTCHA not ready yet, waiting...")
                        time.sleep(poll_interval)
                        continue
                    else:
                        logger.error(f"CAPTCHA solving failed: {result.get('request')}")
                        return None
                else:
                    logger.error(f"Unexpected response: {result}")
                    return None
                    
            except Exception as e:
                logger.warning(f"Error polling for solution: {e}, retrying...")
                time.sleep(poll_interval)
        
        logger.error(f"Timeout waiting for CAPTCHA solution (>{timeout}s)")
        return None
    
    def solve_by_type(self, captcha_type: str, site_key: str, page_url: str, **kwargs) -> Optional[str]:
        """Solve CAPTCHA by type.
        
        Args:
            captcha_type: Type of CAPTCHA (recaptcha_v2, recaptcha_v3, hcaptcha)
            site_key: CAPTCHA site key
            page_url: URL of the page
            **kwargs: Additional parameters
        
        Returns:
            Solution token, or None if failed
        """
        captcha_type = captcha_type.lower()
        
        if captcha_type == "recaptcha_v2" or captcha_type == "recaptcha2":
            return self.solve_recaptcha_v2(site_key, page_url, **kwargs)
        elif captcha_type == "recaptcha_v3" or captcha_type == "recaptcha3":
            action = kwargs.get("action", "submit")
            return self.solve_recaptcha_v3(site_key, page_url, action, **kwargs)
        elif captcha_type == "hcaptcha" or captcha_type == "hcaptcha":
            return self.solve_hcaptcha(site_key, page_url, **kwargs)
        else:
            logger.error(f"Unsupported CAPTCHA type: {captcha_type}")
            return None

