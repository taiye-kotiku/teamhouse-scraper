FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy app
COPY . .

# Render assigns PORT automatically
ENV PORT=10000

EXPOSE 10000

# Start app
CMD ["python", "-u", "main.py"]