FROM python:3.9-slim

WORKDIR /app

# Copy requirements and install first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Set Python path to include both /app and /app/app
ENV PYTHONPATH=/app:/app/app

EXPOSE 8000

CMD ["python", "app/main.py"]
