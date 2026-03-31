import os
import sys
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from playwright.async_api import async_playwright
import uvicorn

logging.basicConfig(level=logging.INFO, stream=sys.stdout, force=True)
logger = logging.getLogger(__name__)

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/ms-playwright"

app = FastAPI(title="TeamHouse Scraper Service", version="0.1.0")

class ScrapeRequest(BaseModel):
    url: str
    wait_seconds: int = 3

@app.get("/")
async def root():
    return {"status": "running"}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "teamhouse-scraper"}

@app.post("/scrape")
async def scrape_page(request: ScrapeRequest):
    logger.info(f"Scraping: {request.url}")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-gpu"
                ]
            )

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                locale="it-IT",
                extra_http_headers={
                    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                }
            )

            page = await context.new_page()

            await page.route(
                "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,mp4,mp3}",
                lambda route: route.abort()
            )

            await page.goto(request.url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(request.wait_seconds * 1000)

            html = await page.content()
            await browser.close()

            blocked = (
                "captcha-delivery.com" in html
                or "DataDome" in html
                or "geo.captcha-delivery.com" in html
            )

            return {
                "success": not blocked,
                "url": request.url,
                "html": html,
                "length": len(html),
                "blocked": blocked
            }

    except Exception as e:
        logger.error(f"Scrape failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "url": request.url,
            "error": str(e),
            "html": "",
            "blocked": False
        }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting uvicorn on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")