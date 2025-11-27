"""
Configuración de la aplicación Domotica Scrapper.
"""

import os
from pathlib import Path
from typing import Optional, ClassVar
from pydantic_settings import BaseSettings, SettingsConfigDict

# Obtener el directorio raíz del proyecto (donde está el .env)
# src/core/config.py -> src -> scrapper-dp2
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """
    Configuración de la aplicación con soporte para diferentes entornos.

    Esta clase define todas las configuraciones disponibles para la aplicación,
    incluyendo valores por defecto y validaciones. Los valores se pueden sobrescribir
    con variables de entorno o archivos .env.

    Attributes
    ----------
    app_name : str
        Nombre de la aplicación
    app_version : str
        Versión actual de la aplicación
    secret_key : str
        Clave secreta para encriptación y tokens
    ... y más configuraciones
    """

    # Model configuration
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=str(ENV_FILE), case_sensitive=False, env_prefix="", extra="ignore"
    )

    # Application info
    app_name: str = "Domotica Scrapper"
    app_version: str = "1.0.0"
    app_description: str = (
        "Sistema de web scraping para domótica con arquitectura en capas"
    )
    debug: bool = False
    environment: str = "production"

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # Security
    secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Domotica INC Scraping
    api_base_url: str
    domotica_base_url: str
    domotica_username: str
    domotica_password: str
    domotica_timeout: int = 30  # Timeout en segundos
    domotica_scrape_interval: int = (
        300  # Intervalo de actualización en segundos (5 minutos)
    )

    # CORS
    allowed_origins: str = "*"
    allowed_methods: str = "GET,POST,PUT,DELETE,PATCH"
    allowed_headers: str = "*"

    # File uploads
    max_file_size: int = 10485760  # 10MB
    upload_dir: str = "uploads"
    allowed_extensions: str = "jpg,jpeg,png,gif,webp"

    # Email configuration (optional)
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None

    # WebSocket
    ws_heartbeat_interval: int = 30

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100

    # RabbitMQ
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "prod_user"
    rabbitmq_password: str = "prod_password"
    rabbitmq_vhost: str = "prod_vhost"
    rabbitmq_exchange: str = "domotica_exchange"
    rabbitmq_queue: str = "domotica_queue"

    # Eliminamos los field_validators que estaban causando problemas


# Singleton instance
_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Obtiene o crea la instancia de configuración (patrón singleton).

    Esta función garantiza que solo exista una instancia de Settings
    en toda la aplicación, evitando cargar múltiples veces las
    configuraciones desde el entorno.

    Las configuraciones se cargan automáticamente desde:
    1. Archivo .env (si existe)
    2. Variables de entorno del sistema
    3. Valores por defecto definidos en la clase Settings

    Returns
    -------
    Settings
        Instancia única de configuración de la aplicación
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
