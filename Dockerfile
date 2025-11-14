FROM python:3.13-slim

WORKDIR /app

# Instalar dependencias para Chrome y ChromeDriver
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    apt-transport-https \
    ca-certificates \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Instalar Chrome (Método moderno)
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo
WORKDIR /app

# 2. Copiar solo el archivo de dependencias primero para aprovechar el caché de Docker
COPY . .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Exponer el puerto para la aplicación FastAPI
EXPOSE 8080

# Comando para ejecutar la aplicación con uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]