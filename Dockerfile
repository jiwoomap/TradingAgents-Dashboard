FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git build-essential curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install streamlit

COPY . .

# Make entrypoint script executable
RUN chmod +x docker-entrypoint.sh

EXPOSE 8501

# Use entrypoint script to start both scheduler and streamlit
ENTRYPOINT ["/app/docker-entrypoint.sh"]
