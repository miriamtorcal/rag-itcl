FROM ollama/ollama:latest

# Instalar curl para verificar que el servicio responda antes de hacer el pull
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Script mejorado para descargar el modelo
RUN ollama serve & \
    until curl -s localhost:11434 > /dev/null; do sleep 1; done; \
    ollama pull llama3.2 && \
    pkill ollama

ENTRYPOINT ["ollama", "serve"]