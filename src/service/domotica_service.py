"""
Servicio de scraping de Domotica.

Este módulo proporciona servicios de negocio para orquestar el scraping
de datos desde la plataforma Domotica INC.
"""

import logging
from typing import List

from src.repository.domotica_page import DomoticaPage
from src.model.schemas import ProductoDomotica, MesaDomotica

# Configurar logging
logger = logging.getLogger(__name__)


def scrape_and_get_productos() -> List[ProductoDomotica]:
    """
    Obtiene productos mediante scraping.

    Este servicio crea una instancia del repository DomoticaPage,
    ejecuta el scraping completo de productos y cierra el driver.

    Returns
    -------
    List[ProductoDomotica]
        Lista de productos extraídos
    """
    logger.info("Servicio: Iniciando obtención de productos")

    try:
        with DomoticaPage() as domotica:
            domotica.login()
            platos = domotica.scrap_productos()
            return platos

    except Exception as e:
        logger.error(f"Servicio: Error obteniendo productos: {str(e)}", exc_info=True)
        return []


def scrape_and_get_mesas() -> List[MesaDomotica]:
    """
    Obtiene mesas mediante scraping.

    Este servicio crea una instancia del repository DomoticaPage,
    ejecuta el scraping completo de mesas y cierra el driver.

    Returns
    -------
    List[MesaDomotica]
        Lista de mesas extraídas
    """
    logger.info("Servicio: Iniciando obtención de mesas")

    try:
        # Inicializar DomoticaPage y extraer mesas
        with DomoticaPage() as domotica:
            domotica.login()
            mesas = domotica.scrap_mesas()
            logger.info(f"Se extrajeron {len(mesas)} mesas para sincronización")
            return mesas

    except Exception as e:
        logger.error(f"Servicio: Error obteniendo mesas: {str(e)}", exc_info=True)
        return []
