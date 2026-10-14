FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código
COPY . /app/mcp_server

# Configurar el entorno para encontrar el paquete mcp_server
ENV PYTHONPATH=/app

# Exponer el puerto del server MCP
EXPOSE 8000

# Ejecutar usando el módulo para evitar problemas de path
CMD ["uvicorn", "mcp_server.server:app", "--host", "0.0.0.0", "--port", "8000"]