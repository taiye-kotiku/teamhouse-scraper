import os
import sys
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from playwright.async_api import async_playwright
import uvicorn

# Configure logging FIRST
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)

# ✅ Log PORT immediately at module level
RAILWAY_PORT = os.environ.get("PORT")
logger.info(f"🔍 RAILWAY PORT ENV VAR: {RAILWAY_PORT}")
logger.info(f"🔍 ALL ENV VARS: {list(os.environ.keys())}")

# Set Playwright browser path
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/ms-playwright"

app = FastAPI(title="TeamHouse Scraper Service", version="0.1.0")

class ScrapeRequest(BaseModel):
    url: str
    wait_seconds: int = 3

@app.get("/")
async def root():
    logger.info("Root endpoint hit")
    return {"message": "TeamHouse Scraper API", "status": "running", "port": RAILWAY_PORT}

@app.get("/health")
async def health():
    logger.info("Health check received")
    return {"status": "ok", "service": "teamhouse-scraper", "port": RAILWAY_PORT}

@app.post("/scrape")
async def scrape_page(request: ScrapeRequest):
    logger.info(f"Scraping: {request.url}")
    
    try:
        async with async_playwright() as p:
            logger.info("Launching Chromium...")
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-gpu"
                ]
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1280, "height": 800},
                locale="it-IT"
            )
            page = await context.new_page()

            await page.route(
                "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,mp4,mp3}",
                lambda route: route.abort()
            )

            logger.info(f"Navigating to {request.url}...")
            await page.goto(request.url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(request.wait_seconds * 1000)

            html = await page.content()
            await browser.close()
            
            logger.info(f"Scrape successful. HTML length: {len(html)}")

            return {
                "success": True,
                "url": request.url,
                "html": html,
                "length": len(html)
            }

    except Exception as e:
        logger.error(f"Scrape failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "url": request.url,
            "error": str(e),
            "html": ""
        }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🚀 Starting uvicorn on 0.0.0.0:{port}")
    
    try:
        uvicorn.run(
            app,  # ✅ Changed from "main:app" to app directly
            host="0.0.0.0", 
            port=port,
            log_level="info",
            access_log=True
        )
    except Exception as e:
        logger.error(f"Failed to start uvicorn: {e}", exc_info=True)
        sys.exit(1)