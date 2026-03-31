FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy app
COPY . .

# Verify Playwright installation
RUN python -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"

# Expose port
EXPOSE 8000

# Run with unbuffered output
CMD ["python", "-u", "main.py"]