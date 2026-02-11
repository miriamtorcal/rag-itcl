FROM python:3.12-slim

WORKDIR /app

# Copiamos requirements específicos de mcp_server
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos código
COPY . .

# PYTHONPATH para imports con "mcp_server.*"
ENV PYTHONPATH=/app

# Ejecutar server
CMD ["uvicorn", "mcp_server.server:app", "--host", "0.0.0.0", "--port", "8081"]
