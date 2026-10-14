FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del cliente
COPY . /app

# Entorno
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Exponer puerto de Streamlit
EXPOSE 8501

CMD ["streamlit", "run", "client/app.py", "--server.port=8501", "--server.address=0.0.0.0"]