"""
Paquete de servicios para la aplicación Domotica Scrapper.

Este paquete contiene los servicios que proporcionan la lógica de negocio
para la aplicación, como la extracción programada de datos y la sincronización
con APIs externas.
"""

from .scheduler_service import SchedulerService

__all__ = ["SchedulerService"]
