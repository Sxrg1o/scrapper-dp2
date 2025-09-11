#!/bin/bash

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Mostrar encabezado
echo -e "${GREEN}"
echo "===================================="
echo " Despliegue de Scrapper DP2"
echo "===================================="
echo -e "${NC}"

# Verificar si Docker está instalado
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker no está instalado. Por favor instala Docker primero.${NC}"
    exit 1
fi

# Verificar si Docker Compose está instalado
if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose no está instalado. Por favor instala Docker Compose primero.${NC}"
    exit 1
fi

echo -e "${YELLOW}Construyendo y desplegando la aplicación...${NC}"

# Ejecutar Docker Compose
docker compose up -d --build

# Verificar si el despliegue fue exitoso
if [ $? -eq 0 ]; then
    echo -e "${GREEN}¡Despliegue exitoso!${NC}"
    echo -e "La aplicación está ahora disponible en: ${GREEN}http://localhost:8000${NC}"
    echo -e "Documentación API: ${GREEN}http://localhost:8000/docs${NC}"
    echo -e ""
    echo -e "Para detener la aplicación, ejecuta: ${YELLOW}docker compose down${NC}"
else
    echo -e "${RED}Error en el despliegue. Verifica los logs con: ${YELLOW}docker compose logs${NC}"
fi
