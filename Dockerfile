FROM python:3.11-slim

WORKDIR /app

RUN useradd --create-home --shell /bin/bash --no-log-init app

COPY requirements.txt . 
RUN pip install -r requirements.txt

COPY . .

# Create data directory for database with proper permissions
RUN mkdir -p /app/data && chown -R app:app /app

USER app

EXPOSE 5010

CMD ["gunicorn", "--bind", "0.0.0.0:5010", "main:app", "-t 600"]
