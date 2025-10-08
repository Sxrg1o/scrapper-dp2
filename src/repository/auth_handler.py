"""
Gestor de autenticación para web scraping.

Este módulo proporciona mecanismos para autenticarse en el sistema Domotica INC
y mantener las sesiones para las operaciones de web scraping.
"""

import aiohttp
import logging
from typing import Dict, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from dataclasses import dataclass

from src.core.config import get_settings

# Configurar logger para este módulo
logger = logging.getLogger(__name__)


@dataclass
class AuthSession:
    """Representa una sesión autenticada en el sistema."""
    
    session: aiohttp.ClientSession
    cookies: Dict[str, str]
    token: Optional[str] = None
    user_id: Optional[str] = None
    is_valid: bool = False


class AuthHandler:
    """
    Gestor de autenticación para interacciones con el sistema Domotica INC.
    
    Esta clase se encarga de realizar el proceso de login, mantener la sesión
    y gestionar la autenticación para las operaciones de scraping.
    """
    
    def __init__(self):
        """Inicializa el manejador de autenticación."""
        self.settings = get_settings()
        self.base_url = self.settings.domotica_base_url
        self.username = self.settings.domotica_username
        self.password = self.settings.domotica_password
        self.login_url = urljoin(self.base_url, "/login")
        self._session: Optional[AuthSession] = None
    
    async def get_session(self) -> AuthSession:
        """
        Obtiene una sesión autenticada.
        
        Si no existe una sesión válida, realiza el proceso de autenticación.
        Si la sesión existe pero ha expirado, renueva la autenticación.
        
        Returns:
            AuthSession: Sesión autenticada para realizar peticiones
        
        Raises:
            Exception: Si no se pudo autenticar
        """
        if not self._session or not self._session.is_valid:
            self._session = await self._authenticate()
            
        return self._session
    
    async def _authenticate(self) -> AuthSession:
        """
        Realiza el proceso de autenticación en el sistema Domotica INC.
        
        Returns:
            AuthSession: Objeto con la sesión autenticada
            
        Raises:
            Exception: Si la autenticación falla
        """
        logger.info(f"Iniciando autenticación en {self.base_url} con usuario {self.username}")
        
        # Crear una nueva sesión HTTP
        session = aiohttp.ClientSession()
        
        try:
            # 1. Obtener la página de login para extraer el token CSRF si es necesario
            async with session.get(self.login_url) as response:
                if response.status != 200:
                    logger.error(f"Error al acceder a la página de login: {response.status}")
                    raise Exception(f"No se pudo acceder a la página de login. Estado: {response.status}")
                
                html = await response.text()
                token = self._extract_csrf_token(html)
            
            # 2. Preparar datos de login
            login_data = {
                "username": self.username,
                "password": self.password
            }
            
            # Agregar token CSRF si existe
            if token:
                login_data["csrf_token"] = token
            
            # 3. Enviar petición de login
            async with session.post(
                self.login_url, 
                data=login_data,
                allow_redirects=False
            ) as response:
                # Verificar si el login fue exitoso (normalmente redirecciona tras login exitoso)
                if response.status not in (200, 302):
                    logger.error(f"Autenticación fallida: {response.status}")
                    raise Exception("Credenciales incorrectas o el sitio ha cambiado")
                
                # Verificar redirección o mensaje de éxito
                if response.status == 302:
                    location = response.headers.get("Location", "")
                    if "error" in location.lower():
                        raise Exception("Autenticación fallida: Redirección a página de error")
                
                # Guardar cookies de la sesión
                cookies = {
                    cookie.key: cookie.value 
                    for cookie in session.cookie_jar.filter_cookies(self.base_url)
                }
                
                # Verificar que tenemos las cookies necesarias
                if not cookies:
                    logger.warning("No se recibieron cookies después del login")
                
                # 4. Verificar que estamos autenticados intentando acceder a una página protegida
                is_authenticated = await self._verify_authentication(session)
                
                if not is_authenticated:
                    logger.error("Verificación de autenticación fallida")
                    raise Exception("La autenticación pareció exitosa pero la verificación falló")
                
                logger.info(f"Autenticación exitosa para usuario {self.username}")
                
                # 5. Crear y devolver la sesión autenticada
                return AuthSession(
                    session=session,
                    cookies=cookies,
                    token=token,
                    is_valid=True
                )
        
        except Exception as e:
            # Cerrar la sesión en caso de error
            await session.close()
            logger.error(f"Error durante la autenticación: {str(e)}")
            raise
    
    async def _verify_authentication(self, session: aiohttp.ClientSession) -> bool:
        """
        Verifica que la autenticación fue exitosa intentando acceder a una página protegida.
        
        Args:
            session: Sesión HTTP a verificar
            
        Returns:
            bool: True si la autenticación es válida, False en caso contrario
        """
        # Intentar acceder a una página que requiere autenticación
        dashboard_url = urljoin(self.base_url, "/dashboard")
        
        try:
            async with session.get(dashboard_url) as response:
                # Si obtenemos un código 200 y no hay redirección a login, estamos autenticados
                if response.status == 200:
                    html = await response.text()
                    
                    # Verificar que no es la página de login
                    if "login" in html.lower() and "password" in html.lower():
                        return False
                    
                    # Buscar algún indicador de autenticación exitosa (ej. nombre de usuario)
                    return self.username.lower() in html.lower() or "logout" in html.lower()
                    
                return False
        
        except Exception as e:
            logger.error(f"Error durante la verificación de autenticación: {str(e)}")
            return False
    
    def _extract_csrf_token(self, html: str) -> Optional[str]:
        """
        Extrae el token CSRF del HTML de la página de login.
        
        Args:
            html: Contenido HTML de la página
            
        Returns:
            Optional[str]: Token CSRF o None si no se encontró
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Buscar el token en un input hidden
            token_input = soup.find('input', {'name': ['csrf_token', '_token', 'csrf']})
            if token_input and 'value' in token_input.attrs:
                return token_input['value']
            
            # Buscar en meta tags
            meta_token = soup.find('meta', {'name': 'csrf-token'})
            if meta_token and 'content' in meta_token.attrs:
                return meta_token['content']
            
            return None
        
        except Exception as e:
            logger.error(f"Error extrayendo token CSRF: {str(e)}")
            return None
    
    async def close(self):
        """Cierra la sesión HTTP si existe."""
        if self._session and self._session.session:
            await self._session.session.close()
            self._session = None


# Instancia global del manejador de autenticación
auth_handler = AuthHandler()