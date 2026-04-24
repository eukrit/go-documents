FROM python:3.11-slim

# WeasyPrint runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libffi8 \
    libjpeg62-turbo fonts-liberation \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY material-submission-template.html drawing-submission-template.html ./

EXPOSE 8080
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "--chdir", "src", "app:app"]
