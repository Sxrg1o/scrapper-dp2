"""
Scrapers para extraer datos de mesas del sistema Domotica INC.

Este módulo contiene las clases y funciones específicas para extraer
información de mesas mediante web scraping.
"""

import logging
from typing import List, Optional
from bs4 import Tag

from src.model.schemas import MesaDomotica
from src.repository.http_client import scraping_client

# Configurar logger para este módulo
logger = logging.getLogger(__name__)


class MesaScraper:
    """
    Extractor de datos de mesas mediante web scraping.
    
    Esta clase se encarga de navegar por el sistema Domotica INC,
    localizar los elementos HTML correspondientes a mesas y
    extraer la información estructurada.
    """
    
    def __init__(self):
        """Inicializa el scraper de mesas."""
        # Rutas de navegación
        self.mesas_path = "/mesas"
        self.zonas_path = "/mesas/zonas"
    
    async def get_mesas(self) -> List[MesaDomotica]:
        """
        Obtiene la lista de todas las mesas disponibles.
        
        Returns:
            List[MesaDomotica]: Lista de mesas con su información
            
        Raises:
            Exception: Si ocurre un error al extraer las mesas
        """
        try:
            html, _ = await scraping_client.get_page(self.mesas_path)
            soup = await scraping_client.parse_html(html)
            
            # Buscar los elementos HTML que contienen las mesas
            # (Ajustar estos selectores según la estructura real del sitio)
            mesa_elements = soup.select('.mesa-item') or soup.select('table.mesas tr')
            
            if not mesa_elements:
                logger.warning("No se encontraron mesas en la página")
                return []
            
            mesas: List[MesaDomotica] = []
            
            for elemento in mesa_elements:
                # Intentar extraer los datos de la mesa
                try:
                    mesa = await self._extraer_datos_mesa(elemento)
                    if mesa:
                        mesas.append(mesa)
                except Exception as e:
                    logger.error(f"Error extrayendo datos de una mesa: {str(e)}")
                    continue
            
            logger.info(f"Mesas extraídas: {len(mesas)}")
            return mesas
            
        except Exception as e:
            logger.error(f"Error al obtener mesas: {str(e)}")
            raise Exception(f"Error al obtener mesas: {str(e)}")
    
    async def get_mesas_por_zona(self, zona: str) -> List[MesaDomotica]:
        """
        Obtiene la lista de mesas para una zona específica.
        
        Args:
            zona: Nombre de la zona a buscar
            
        Returns:
            List[MesaDomotica]: Lista de mesas de la zona
            
        Raises:
            Exception: Si ocurre un error al extraer las mesas
        """
        try:
            # Construir URL de mesas filtradas por zona
            # (Ajustar según cómo funcione el sitio real)
            path = f"{self.mesas_path}?zona={zona}"
            html, _ = await scraping_client.get_page(path)
            soup = await scraping_client.parse_html(html)
            
            # Buscar los elementos que representan las mesas
            # (Ajustar estos selectores según la estructura real del sitio)
            mesa_elements = soup.select('.mesa-item') or soup.select('table.mesas tr')
            
            if not mesa_elements:
                logger.warning(f"No se encontraron mesas para la zona '{zona}'")
                return []
            
            mesas: List[MesaDomotica] = []
            
            for elemento in mesa_elements:
                # Intentar extraer los datos de la mesa
                try:
                    mesa = await self._extraer_datos_mesa(elemento)
                    # Validar que la mesa pertenezca a la zona solicitada
                    if mesa and mesa.zona.lower() == zona.lower():
                        mesas.append(mesa)
                except Exception as e:
                    logger.error(f"Error extrayendo datos de una mesa: {str(e)}")
                    continue
            
            logger.info(f"Mesas extraídas de la zona '{zona}': {len(mesas)}")
            return mesas
            
        except Exception as e:
            logger.error(f"Error al obtener mesas de zona '{zona}': {str(e)}")
            raise Exception(f"Error al obtener mesas de la zona '{zona}': {str(e)}")
    
    async def get_zonas(self) -> List[str]:
        """
        Obtiene la lista de zonas disponibles.
        
        Returns:
            List[str]: Lista de nombres de zonas
            
        Raises:
            Exception: Si ocurre un error al extraer las zonas
        """
        try:
            html, _ = await scraping_client.get_page(self.zonas_path)
            soup = await scraping_client.parse_html(html)
            
            # Buscar los elementos HTML que contienen las zonas
            # (Ajustar estos selectores según la estructura real del sitio)
            zona_elements = soup.select('ul.zonas li a') or soup.select('.zona-item')
            
            if not zona_elements:
                logger.warning("No se encontraron zonas en la página")
                return []
            
            # Extraer nombres de zonas
            zonas = [
                zona.get_text().strip()
                for zona in zona_elements
                if zona and zona.get_text().strip()
            ]
            
            logger.info(f"Zonas extraídas: {len(zonas)}")
            return zonas
            
        except Exception as e:
            logger.error(f"Error al obtener zonas: {str(e)}")
            raise Exception(f"Error al obtener zonas: {str(e)}")
    
    async def _extraer_datos_mesa(self, elemento: Tag) -> Optional[MesaDomotica]:
        """
        Extrae los datos de una mesa desde su elemento HTML.
        
        Args:
            elemento: Elemento HTML que contiene los datos de la mesa
            
        Returns:
            Optional[MesaDomotica]: Datos de la mesa o None si no se pudo extraer
        """
        try:
            # Extraer identificador de la mesa
            # (Ajustar estos selectores según la estructura real del sitio)
            id_element = elemento.select_one('.id-mesa') or elemento.select_one('td.identificador')
            identificador = id_element.get_text().strip() if id_element else None
            
            if not identificador:
                logger.warning("No se encontró el identificador de la mesa, omitiendo")
                return None
            
            # Extraer zona
            # (Ajustar estos selectores según la estructura real del sitio)
            zona_element = elemento.select_one('.zona-mesa') or elemento.select_one('td.zona')
            zona = zona_element.get_text().strip() if zona_element else "Desconocida"
            
            # Extraer estado de ocupación
            # (Ajustar estos selectores según la estructura real del sitio)
            estado_element = elemento.select_one('.estado-mesa') or elemento.select_one('td.estado')
            estado_text = estado_element.get_text().strip().lower() if estado_element else ""
            
            # Determinar si está ocupada basado en el texto
            ocupado = any(
                palabra in estado_text 
                for palabra in ["ocupada", "ocupado", "en uso", "reservada"]
            )
            
            # También verificar si hay una clase CSS que indique estado
            if elemento.get('class'):
                # El método get('class') puede devolver una lista o None
                class_attr = elemento.get('class')
                if class_attr and isinstance(class_attr, list):
                    classes = " ".join(class_attr)
                    if "ocupada" in classes or "ocupado" in classes:
                        ocupado = True
                    elif "libre" in classes or "disponible" in classes:
                        ocupado = False
            
            # Crear instancia de la mesa
            return MesaDomotica(
                identificador=identificador,
                zona=zona,
                ocupado=ocupado
            )
            
        except Exception as e:
            logger.error(f"Error al extraer datos de mesa: {str(e)}")
            return None


# Instancia global del scraper de mesas
mesa_scraper = MesaScraper()