#!/usr/bin/env python3
"""
Ejemplo que demuestra el flujo completo de scraping para Domotica Peru.

Este script utiliza la clase DomoticaPage para realizar las siguientes acciones:
1. Iniciar sesión
2. Navegar al panel de control
3. Navegar a la sección de mesas
4. Seleccionar una mesa específica
5. Extraer las categorías de productos
6. Extraer todos los productos de todas las categorías
"""

import sys
import time
import logging
from pathlib import Path

# Añadir el directorio raíz al path para poder importar los módulos
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from typing import List
from src.model.schemas import MesaDomotica, ProductoDomotica
from src.repository.domotica_page import DomoticaPage
from src.core.config import get_settings

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("complete_scraping_flow")


def main():
    """Ejecuta el flujo completo de scraping en pasos secuenciales"""
    # Obtener configuración
    settings = get_settings()
    username = settings.domotica_username
    password = settings.domotica_password

    try:
        with DomoticaPage(username=username, password=password) as page:
            logger.info("Página inicial cargada.")
            if not page.login():
                logger.error("Error de inicio de sesión. Verifica tus credenciales.")
                return

            mesas: List[MesaDomotica] = []
            try:
                mesas = page.scrap_mesas()
                for mesa in mesas:
                    logger.info(f"Mesa encontrada: {mesa}")
            except Exception as e:
                logger.error(f"Error al extraer las mesas: {str(e)}")
                return

            platos: List[ProductoDomotica] = []
            try:
                platos = page.scrap_platos()
                for plato in platos:
                    logger.info(f"Plato encontrado: {plato}")
            except Exception as e:
                logger.error(f"Error al extraer los platos: {str(e)}")
                return

            time.sleep(10)

    except Exception as e:
        logger.exception(f"Error durante la ejecución: {str(e)}")


if __name__ == "__main__":
    main()
