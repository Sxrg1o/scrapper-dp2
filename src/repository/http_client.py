"""
Cliente HTTP para operaciones de web scraping.

Este módulo proporciona una capa abstracta sobre las operaciones HTTP
utilizadas para el web scraping del sistema Domotica INC.
"""

import logging
import aiohttp
from typing import Dict, Any, Tuple
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from src.repository.auth_handler import auth_handler, AuthSession
from src.core.config import get_settings

# Configurar logger para este módulo
logger = logging.getLogger(__name__)


class ScrapingClient:
    """
    Cliente HTTP para operaciones de web scraping.
    
    Esta clase proporciona métodos de alto nivel para realizar peticiones HTTP
    al sistema Domotica INC, manejar errores y procesar respuestas.
    """
    
    def __init__(self):
        """Inicializa el cliente HTTP."""
        self.settings = get_settings()
        self.base_url = self.settings.domotica_base_url
        self.timeout = self.settings.domotica_timeout
    
    async def get_page(self, path: str) -> Tuple[str, AuthSession]:
        """
        Obtiene el contenido HTML de una página.
        
        Args:
            path: Ruta relativa de la página a obtener
            
        Returns:
            Tuple[str, AuthSession]: Contenido HTML de la página y la sesión utilizada
            
        Raises:
            Exception: Si ocurre un error al obtener la página
        """
        session = await self._get_auth_session()
        url = urljoin(self.base_url, path)
        
        try:
            async with session.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=True
            ) as response:
                if response.status != 200:
                    logger.error(f"Error al obtener página {url}: {response.status}")
                    raise Exception(f"Error al obtener página {url}. Estado: {response.status}")
                
                html = await response.text()
                return html, session
        
        except aiohttp.ClientError as e:
            logger.error(f"Error de conexión al obtener página {url}: {str(e)}")
            raise Exception(f"Error de conexión al obtener página: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error inesperado al obtener página {url}: {str(e)}")
            raise
    
    async def post_form(self, path: str, data: Dict[str, Any]) -> Tuple[str, AuthSession]:
        """
        Envía un formulario mediante POST.
        
        Args:
            path: Ruta relativa donde enviar el formulario
            data: Datos del formulario a enviar
            
        Returns:
            Tuple[str, AuthSession]: Respuesta HTML y la sesión utilizada
            
        Raises:
            Exception: Si ocurre un error al enviar el formulario
        """
        session = await self._get_auth_session()
        url = urljoin(self.base_url, path)
        
        try:
            async with session.session.post(
                url,
                data=data,
                timeout=self.timeout,
                allow_redirects=True
            ) as response:
                if response.status not in (200, 201, 302):
                    logger.error(f"Error al enviar formulario a {url}: {response.status}")
                    raise Exception(f"Error al enviar formulario. Estado: {response.status}")
                
                html = await response.text()
                return html, session
        
        except aiohttp.ClientError as e:
            logger.error(f"Error de conexión al enviar formulario a {url}: {str(e)}")
            raise Exception(f"Error de conexión al enviar formulario: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error inesperado al enviar formulario a {url}: {str(e)}")
            raise
    
    async def parse_html(self, html: str) -> BeautifulSoup:
        """
        Analiza el contenido HTML utilizando BeautifulSoup.
        
        Args:
            html: Contenido HTML a analizar
            
        Returns:
            BeautifulSoup: Objeto BeautifulSoup para manipular el HTML
        """
        return BeautifulSoup(html, 'html.parser')
    
    async def _get_auth_session(self) -> AuthSession:
        """
        Obtiene una sesión autenticada para realizar peticiones.
        
        Returns:
            AuthSession: Sesión autenticada
        """
        return await auth_handler.get_session()


# Instancia global del cliente HTTP para scraping
scraping_client = ScrapingClient()