"""HTTP bridge server for Chrome extension to communicate with Python CAPTCHA solver."""
import logging
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
from automation.captcha_solver import CaptchaSolver

logger = logging.getLogger(__name__)

app = FastAPI(title="CAPTCHA Solver Bridge")

# Enable CORS for extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to chrome-extension://
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize solver
solver = CaptchaSolver()


class SolveRequest(BaseModel):
    """Request model for CAPTCHA solving."""
    captcha_type: str  # recaptcha_v2, recaptcha_v3, hcaptcha
    site_key: str
    page_url: str
    action: Optional[str] = None  # For reCAPTCHA v3


class SolutionResponse(BaseModel):
    """Response model for CAPTCHA solution."""
    success: bool
    solution: Optional[str] = None
    error: Optional[str] = None


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/balance")
async def get_balance():
    """Get 2Captcha account balance."""
    balance = solver.get_balance()
    if balance is None:
        raise HTTPException(status_code=500, detail="Failed to get balance")
    return {"balance": balance}


@app.post("/solve", response_model=SolutionResponse)
async def solve_captcha(request: SolveRequest):
    """Solve CAPTCHA challenge.
    
    Args:
        request: CAPTCHA solving request
    
    Returns:
        Solution token or error
    """
    try:
        logger.info(f"Received solve request: type={request.captcha_type}, site_key={request.site_key[:20]}...")
        
        # Solve based on type
        if request.captcha_type == "recaptcha_v2":
            solution = solver.solve_recaptcha_v2(request.site_key, request.page_url)
        elif request.captcha_type == "recaptcha_v3":
            action = request.action or "submit"
            solution = solver.solve_recaptcha_v3(request.site_key, request.page_url, action)
        elif request.captcha_type == "hcaptcha":
            solution = solver.solve_hcaptcha(request.site_key, request.page_url)
        else:
            return SolutionResponse(
                success=False,
                error=f"Unsupported CAPTCHA type: {request.captcha_type}"
            )
        
        if solution:
            logger.info("CAPTCHA solved successfully")
            return SolutionResponse(success=True, solution=solution)
        else:
            logger.error("Failed to solve CAPTCHA")
            return SolutionResponse(
                success=False,
                error="Failed to solve CAPTCHA. Check logs for details."
            )
            
    except Exception as e:
        logger.error(f"Error solving CAPTCHA: {e}", exc_info=True)
        return SolutionResponse(
            success=False,
            error=str(e)
        )


class BridgeServer:
    """Manages the CAPTCHA bridge server."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        """Initialize bridge server.
        
        Args:
            host: Server host
            port: Server port
        """
        self.host = host
        self.port = port
        self.server = None
        self.task = None
    
    async def start(self):
        """Start the bridge server."""
        config = uvicorn.Config(
            app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=False
        )
        self.server = uvicorn.Server(config)
        self.task = asyncio.create_task(self.server.serve())
        logger.info(f"CAPTCHA bridge server started on http://{self.host}:{self.port}")
    
    async def stop(self):
        """Stop the bridge server."""
        if self.server:
            self.server.should_exit = True
        if self.task:
            await self.task
        logger.info("CAPTCHA bridge server stopped")


# Global server instance
_bridge_server: Optional[BridgeServer] = None


async def start_bridge_server(host: str = "127.0.0.1", port: int = 8765) -> BridgeServer:
    """Start the bridge server.
    
    Args:
        host: Server host
        port: Server port
    
    Returns:
        BridgeServer instance
    """
    global _bridge_server
    if _bridge_server is None:
        _bridge_server = BridgeServer(host, port)
        await _bridge_server.start()
    return _bridge_server


async def stop_bridge_server():
    """Stop the bridge server."""
    global _bridge_server
    if _bridge_server:
        await _bridge_server.stop()
        _bridge_server = None

