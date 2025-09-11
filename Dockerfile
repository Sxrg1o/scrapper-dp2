FROM python:3.10-slim

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

# Instalar Chrome (Método moderno y corregido)
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Configurar Chrome para ejecutarse sin sandbox (necesario para Docker)
ENV CHROME_OPTIONS="--headless --disable-gpu --no-sandbox --disable-dev-shm-usage"

# Copiar los archivos del proyecto
COPY . .

# 1. Usar una imagen base que ya contenga Miniconda
FROM continuumio/miniconda3

# Instalar dependencias del sistema para Chrome
# La imagen de miniconda está basada en Debian, por lo que apt-get funciona
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
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

# 3. Crear el entorno de Conda usando tu archivo
RUN conda create --name app-env --file requirements.txt -c conda-forge -c defaults

# Configurar Chrome para ejecutarse sin sandbox
ENV CHROME_OPTIONS="--headless --disable-gpu --no-sandbox --disable-dev-shm-usage"

# Exponer el puerto para la aplicación FastAPI
EXPOSE 8000

# 4. Comando para ejecutar la aplicación DENTRO del entorno de Conda
CMD ["conda", "run", "-n", "app-env", "--no-capture-output", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]