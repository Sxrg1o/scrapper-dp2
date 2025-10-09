"""
Configuración de la aplicación Domotica Scrapper.
"""

import os
from typing import List, Optional, ClassVar, Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
        env_file=".env", case_sensitive=False, env_prefix="", extra="ignore"
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
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Domotica INC Scraping
    domotica_base_url: str
    domotica_username: str
    domotica_password: str
    domotica_timeout: int = 30  # Timeout en segundos
    domotica_scrape_interval: int = (
        300  # Intervalo de actualización en segundos (5 minutos)
    )

    # CORS
    allowed_origins: List[str] = ["http://localhost:3000"]
    allowed_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH"]
    allowed_headers: List[str] = ["*"]

    # File uploads
    max_file_size: int = 10485760  # 10MB
    upload_dir: str = "uploads"
    allowed_extensions: List[str] = ["jpg", "jpeg", "png", "gif", "webp"]

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

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str] | Any:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("allowed_methods", mode="before")
    @classmethod
    def parse_cors_methods(cls, v: Any) -> List[str] | Any:
        """Parse CORS methods from string or list."""
        if isinstance(v, str):
            return [method.strip() for method in v.split(",")]
        return v

    @field_validator("allowed_headers", mode="before")
    @classmethod
    def parse_cors_headers(cls, v: Any) -> List[str] | Any:
        """Parse CORS headers from string or list."""
        if isinstance(v, str):
            return [header.strip() for header in v.split(",")]
        return v

    @field_validator("allowed_extensions", mode="before")
    @classmethod
    def parse_allowed_extensions(cls, v: Any) -> List[str] | Any:
        """Parse allowed file extensions from string or list."""
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v


# Singleton instance
_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Obtiene o crea la instancia de configuración (patrón singleton).

    Esta función garantiza que solo exista una instancia de Settings
    en toda la aplicación, evitando cargar múltiples veces las
    configuraciones desde el entorno.

    Returns
    -------
    Settings
        Instancia única de configuración de la aplicación
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings(
            domotica_base_url=os.getenv("DOMOTICA_BASE_URL", "https://example.com/"),
            domotica_username=os.getenv("DOMOTICA_USERNAME", "your_username"),
            domotica_password=os.getenv("DOMOTICA_PASSWORD", "your_password"),
            secret_key=os.getenv("SECRET_KEY", "your-default-secret-key"),
        )
    return _settings_instance
