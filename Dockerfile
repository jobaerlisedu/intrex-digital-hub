FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

RUN npm run build && python manage.py collectstatic --no-input --clear

# Startup script — runs bootstrap tasks, then starts gunicorn
RUN printf '#!/usr/bin/env bash\nset -o errexit\npython manage.py bootstrap\ngunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 4 --timeout 120 --access-logfile - --error-logfile -\n' > /start.sh && chmod +x /start.sh

EXPOSE 8000

CMD ["/start.sh"]
