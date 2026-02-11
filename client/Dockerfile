# client/Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

# Streamlit
CMD ["streamlit", "run", "client/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
