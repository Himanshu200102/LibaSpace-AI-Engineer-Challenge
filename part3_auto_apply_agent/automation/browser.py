"""Browser management for Playwright."""
import logging
import os
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from automation.captcha_bridge import start_bridge_server, stop_bridge_server

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages Playwright browser instance with Chrome extension."""
    
    def __init__(self, headless: bool = False, load_extension: bool = True):
        """Initialize browser manager.
        
        Args:
            headless: Run browser in headless mode
            load_extension: Whether to load the CAPTCHA solver extension
        """
        self.headless = headless
        self.load_extension = load_extension
        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self.bridge_server = None
    
    async def start(self):
        """Start browser and create page."""
        logger.info("Starting browser...")
        
        # Start CAPTCHA bridge server
        if self.load_extension:
            try:
                self.bridge_server = await start_bridge_server()
                logger.info("CAPTCHA bridge server started")
            except Exception as e:
                logger.warning(f"Failed to start bridge server: {e}. Extension may not work.")
        
        self.playwright = await async_playwright().start()
        
        # Prepare browser launch args
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage"
        ]
        
        # Load Chrome extension if enabled
        context_options = {
            "viewport": {"width": 1280, "height": 900},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        if self.load_extension:
            # Get extension path
            extension_path = Path(__file__).parent.parent / "chrome_extension"
            extension_path = extension_path.resolve()
            
            if extension_path.exists():
                launch_args.append(f"--disable-extensions-except={extension_path}")
                launch_args.append(f"--load-extension={extension_path}")
                logger.info(f"Loading Chrome extension from: {extension_path}")
            else:
                logger.warning(f"Extension path not found: {extension_path}")
        
        # Launch browser
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=launch_args
        )
        
        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()
        self.page.set_default_timeout(30000)
        logger.info("Browser started")
    
    async def close(self):
        """Close browser and cleanup."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        
        # Stop bridge server
        if self.bridge_server:
            try:
                await stop_bridge_server()
            except Exception as e:
                logger.warning(f"Error stopping bridge server: {e}")
        
        logger.info("Browser closed")
    
    def get_page(self) -> Page:
        """Get the current page."""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        return self.page

