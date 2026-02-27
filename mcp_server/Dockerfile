FROM python:3.12-slim

WORKDIR /app

# Copiamos requirements específicos de mcp_server
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos código
COPY . .

# PYTHONPATH para imports con "mcp_server.*"
ENV PYTHONPATH=/app

EXPOSE 8081

# Ejecutar server
CMD ["python", "-m", "mcp_server.server"]
