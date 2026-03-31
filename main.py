import os
import sys
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async  # ← Add this
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
    return {"status": "ok"}

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
                    "--disable-blink-features=AutomationControlled",  # ← Hide automation
                ]
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="it-IT",
                timezone_id="Europe/Rome",
                geolocation={"longitude": 9.1859, "latitude": 45.4642},  # Milan coordinates
                permissions=["geolocation"],
                extra_http_headers={
                    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1"
                }
            )
            
            page = await context.new_page()
            
            # ✅ Apply stealth mode
            await stealth_async(page)
            
            # Add realistic delays
            await page.goto(request.url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)  # Human-like pause
            
            # Scroll to simulate human behavior
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await page.wait_for_timeout(1000)
            
            await page.wait_for_timeout(request.wait_seconds * 1000)
            
            html = await page.content()
            await browser.close()
            
            # Check if CAPTCHA'd
            if "captcha-delivery.com" in html or "DataDome" in html:
                logger.warning("CAPTCHA detected!")
                return {
                    "success": False,
                    "url": request.url,
                    "error": "CAPTCHA_BLOCKED",
                    "html": html[:500]  # Return snippet for debugging
                }
            
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
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info", proxy_headers=True, forwarded_allow_ips="*")