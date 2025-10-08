"""
Punto de entrada principal de la aplicación FastAPI para Domotica Scrapper.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.core.logging import configure_logging


# Configurar logger para este módulo
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestiona el ciclo de vida de la aplicación FastAPI.

    Controla eventos de inicio y apagado, configurando recursos necesarios
    al inicio y liberándolos al finalizar.

    Parameters
    ----------
    app : FastAPI
        Instancia de la aplicación FastAPI

    Notes
    -----
    Secuencia: inicialización → funcionamiento → limpieza
    """
    # Fase de inicialización
    logger.info("Iniciando Domotica Scrapper API...")
    
    # Configurar sistema de logging
    configure_logging()
    
    # Aquí se pueden inicializar más recursos (BD, conexiones, etc.)
    logger.info("Domotica Scrapper API iniciada correctamente")

    yield  # Aplicación en funcionamiento

    # Fase de limpieza
    logger.info("Cerrando Domotica Scrapper API...")
    
    # Aquí se pueden cerrar conexiones y liberar recursos
    logger.info("Recursos liberados correctamente")


def register_routers(app: FastAPI) -> None:
    """
    Registra todos los routers de la aplicación.

    Parameters
    ----------
    app : FastAPI
        La instancia de la aplicación FastAPI donde registrar los routers
    """
    from src.api.controllers.domotica_controller import router as domotica_router
    app.include_router(domotica_router, prefix="/api/v1")


def create_app() -> FastAPI:
    """
    Crea y configura la aplicación FastAPI.

    Configura todos los aspectos de la aplicación incluyendo
    middlewares, gestión de excepciones y registro de rutas.

    Returns
    -------
    FastAPI
        Instancia configurada de la aplicación
    """
    settings = get_settings()

    # Crear la instancia de FastAPI
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Agregar middleware CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=settings.allowed_methods,
        allow_headers=settings.allowed_headers,
    )

    # Registrar todos los routers disponibles
    register_routers(app)

    return app

# Crear la instancia de la aplicación
app = create_app()

# Punto de entrada para ejecución directa del script
if __name__ == "__main__":
    import uvicorn

    # Obtener configuración
    settings = get_settings()

    # Iniciar servidor uvicorn
    logger.info(f"Iniciando servidor en {settings.host}:{settings.port}")
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )