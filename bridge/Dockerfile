FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    sox \
    libsox-fmt-all \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The AGI script needs to be executable and accessible by Asterisk
RUN chmod +x /app/agi-bin/ai_infoline.py 2>/dev/null || true

CMD ["python", "-u", "main.py"]
