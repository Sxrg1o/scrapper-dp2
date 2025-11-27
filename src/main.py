"""
Punto de entrada principal de la aplicación FastAPI para Domotica Scrapper.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.core.logging import configure_logging
from src.service.scheduler_service import SchedulerService
from src.core.rabbitmq_consumer import RabbitMQConsumer


# Configurar logger para este módulo
logger = logging.getLogger(__name__)

# Crear instancia del scheduler service
scheduler = SchedulerService()
rabbitmq_consumer = RabbitMQConsumer()


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

    # Iniciar el scheduler para sync_platos
    logger.info("Iniciando el servicio de sincronización de platos...")
    if scheduler.start("00:00"):  # Sincronizar cada día a medianoche
        logger.info("Servicio de sincronización iniciado correctamente")
    else:
        logger.error("No se pudo iniciar el servicio de sincronización")

    # Iniciar RabbitMQ Consumer
    logger.info("Iniciando RabbitMQ Consumer...")
    await rabbitmq_consumer.connect()

    logger.info("Domotica Scrapper API iniciada correctamente")

    yield  # Aplicación en funcionamiento

    # Fase de limpieza
    logger.info("Cerrando Domotica Scrapper API...")

    # Detener el scheduler
    if scheduler.is_running:
        logger.info("Deteniendo el servicio de sincronización...")
        scheduler.stop()

    # Cerrar RabbitMQ Consumer
    await rabbitmq_consumer.close()

    # Aquí se pueden cerrar otras conexiones y liberar recursos
    logger.info("Recursos liberados correctamente")


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
    configure_logging()

    # Crear la instancia de FastAPI
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        root_path="/scrapper",
    )

    # Agregar middleware CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=settings.allowed_methods,
        allow_headers=settings.allowed_headers,
    )

    from src.api.controllers.domotica_controller import router as domotica_router

    app.include_router(domotica_router, prefix="/v1")

    @app.post("/sync/platos", tags=["Sync"])
    async def sync_platos(response: Response):
        """
        Ejecuta una sincronización manual de platos.

        Returns:
        -------
        dict
            Resultado de la sincronización
        """
        result = scheduler.sync_platos()
        if not result:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {"status": "error", "message": "La sincronización falló"}
        return {"status": "success", "message": "Sincronización completada con éxito"}

    @app.get("/sync/mesas", tags=["Sync"])
    async def sync_mesas(response: Response):
        """
        Ejecuta una sincronización manual de mesas.

        Returns:
        -------
        dict
            Resultado de la sincronización
        """
        result = scheduler.sync_mesas()
        if not result:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {"status": "error", "message": "La sincronización falló"}
        return {"status": "success", "message": "Sincronización completada con éxito"}

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
