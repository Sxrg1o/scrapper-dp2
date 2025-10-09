"""
Servicio de scraping de Domotica.

Este módulo proporciona servicios de negocio para orquestar el scraping
de datos desde la plataforma Domotica INC.
"""

import logging
from typing import List

from src.repository.domotica_page import DomoticaPage
from src.model.schemas import ProductoDomotica, MesaDomotica
from src.core.config import get_settings

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
    settings = get_settings()
    logger.info("Servicio: Iniciando obtención de productos")
    
    driver_page = None
    
    try:
        # Crear instancia de DomoticaPage
        driver_page = DomoticaPage(
            username=settings.domotica_username,
            password=settings.domotica_password
        )
        
        # Ejecutar scraping completo (login, scraping, logout) - LA LÓGICA ESTÁ EN EL REPOSITORY
        productos = driver_page.scrape_productos_complete()
        
        logger.info(f"Servicio: {len(productos)} productos obtenidos")
        return productos
        
    except Exception as e:
        logger.error(f"Servicio: Error obteniendo productos: {str(e)}", exc_info=True)
        return []
    
    finally:
        # Asegurar que el driver se cierre siempre
        if driver_page:
            try:
                driver_page.close()
                logger.debug("Servicio: Driver cerrado correctamente (productos)")
            except Exception as e:
                logger.error(f"Servicio: Error cerrando driver: {e}")


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
    settings = get_settings()
    logger.info("Servicio: Iniciando obtención de mesas")
    
    driver_page = None
    
    try:
        # Crear instancia de DomoticaPage
        driver_page = DomoticaPage(
            username=settings.domotica_username,
            password=settings.domotica_password
        )
        
        # Ejecutar scraping completo (login, scraping, logout) - LA LÓGICA ESTÁ EN EL REPOSITORY
        mesas = driver_page.scrape_mesas_complete()
        
        logger.info(f"Servicio: {len(mesas)} mesas obtenidas")
        return mesas
        
    except Exception as e:
        logger.error(f"Servicio: Error obteniendo mesas: {str(e)}", exc_info=True)
        return []
    
    finally:
        # Asegurar que el driver se cierre siempre
        if driver_page:
            try:
                driver_page.close()
                logger.debug("Servicio: Driver cerrado correctamente (mesas)")
            except Exception as e:
                logger.error(f"Servicio: Error cerrando driver: {e}")
