"""
Módulo para gestionar tareas programadas.

Este módulo proporciona funcionalidades para ejecutar tareas programadas
como sincronización de datos con APIs externas.
"""

import logging
import requests
import schedule
import time
import threading
from typing import Dict, Any, List, Optional

from src.repository.domotica_page import DomoticaPage
from src.core.config import get_settings
from src.model.schemas import ProductoDomotica

# Configurar logging para este módulo
logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Servicio para gestionar tareas programadas.

    Esta clase proporciona métodos para programar tareas recurrentes
    como sincronización de datos con APIs externas.
    """

    def __init__(self):
        """
        Inicializa el servicio de programación de tareas.
        """
        self.settings = get_settings()
        self.sync_platos_url = f"{self.settings.api_base_url}/api/v1/sync/platos"
        self.sync_mesas_url = f"{self.settings.api_base_url}/api/v1/sync/mesas"
        self.scheduler_thread = None
        self.is_running = False

    def sync_mesas(self) -> bool:
        """
        Sincroniza las mesas extraídas con el endpoint de la API.

        Este método extrae las mesas usando DomoticaPage.scrap_mesas()
        y las envía al endpoint de sincronización.

        Returns:
            bool: True si la sincronización fue exitosa, False en caso contrario.
        """
        logger.info("Iniciando sincronización de mesas con la API")

        try:
            # Inicializar DomoticaPage y extraer mesas
            with DomoticaPage() as domotica:
                if not domotica.login():
                    logger.error("No se pudo iniciar sesión en Domotica Peru")
                    return False

                mesas = domotica.scrap_mesas()

                if not mesas:
                    logger.warning("No se encontraron mesas para sincronizar")
                    return False

                logger.info(f"Se extrajeron {len(mesas)} mesas para sincronización")

                # Enviar datos al endpoint de sincronización
                headers = {
                    "Content-Type": "application/json",
                }

                response = requests.post(
                    self.sync_mesas_url,
                    json=[m.model_dump() for m in mesas],
                    headers=headers,
                    timeout=180,
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Sincronización exitosa. Respuesta: {result}")
                    return True
                else:
                    logger.error(
                        f"Error en sincronización: {response.status_code} - {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error durante la sincronización de mesas: {str(e)}")
            return False

    def sync_platos(self) -> bool:
        """
        Sincroniza los platos/productos extraídos con el endpoint de la API.

        Este método extrae los platos/productos usando DomoticaPage.scrap_platos()
        y los envía al endpoint de sincronización.

        Returns:
            bool: True si la sincronización fue exitosa, False en caso contrario.
        """
        logger.info("Iniciando sincronización de platos con la API")

        try:
            # Inicializar DomoticaPage y extraer platos
            with DomoticaPage() as domotica:
                if not domotica.login():
                    logger.error("No se pudo iniciar sesión en Domotica Peru")
                    return False

                # Extraer platos
                platos = domotica.scrap_productos()

                if not platos:
                    logger.warning("No se encontraron platos para sincronizar")
                    return False

                logger.info(f"Se extrajeron {len(platos)} platos para sincronización")

                # Enviar datos al endpoint de sincronización
                headers = {
                    "Content-Type": "application/json",
                }

                # Usar model_dump() en lugar de model_dump_json() para obtener diccionarios Python
                platos_data: List[Dict[str, str]] = [p.model_dump() for p in platos]
                logger.info(f"Datos de platos a sincronizar: {len(platos_data)} items")
                for p in platos_data:
                    logger.info(p)

                response = requests.post(
                    self.sync_platos_url,
                    json=platos_data,
                    headers=headers,
                    timeout=180,
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Sincronización exitosa. Respuesta: {result}")
                    return True
                else:
                    logger.error(
                        f"Error en sincronización: {response.status_code} - {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error durante la sincronización de platos: {str(e)}")
            return False

    def schedule_daily_sync(self, time_str: str = "00:00") -> bool:
        """
        Programa una sincronización diaria de platos a la hora especificada.

        Args:
            time_str: Hora de ejecución en formato "HH:MM". Por defecto "00:00" (medianoche).

        Returns:
            bool: True si se programó correctamente, False en caso contrario.
        """
        try:
            logger.info(f"Programando sincronización diaria a las {time_str}")
            schedule.clear()
            schedule.every().day.at(time_str).do(self.sync_platos)

            # Ejecutar inmediatamente la primera sincronización
            # if self.sync_platos():
            #     logger.info("Primera sincronización completada con éxito")
            # else:
            #     logger.warning(
            #         "La primera sincronización falló, se reintentará según programación"
            #     )

            return True

        except Exception as e:
            logger.error(f"Error al programar la sincronización diaria: {str(e)}")
            return False

    def _run_scheduler(self):
        """
        Método interno para ejecutar el bucle del programador en un hilo separado.
        """
        self.is_running = True
        logger.info("Iniciando bucle del programador de tareas")

        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # Comprobar cada minuto

    def start(self, time_str: str = "00:00") -> bool:
        """
        Inicia el servicio de programación en un hilo separado.

        Args:
            time_str: Hora de ejecución en formato "HH:MM". Por defecto "00:00" (medianoche).

        Returns:
            bool: True si el servicio se inició correctamente, False en caso contrario.
        """
        if self.is_running:
            logger.warning("El servicio de programación ya está en ejecución")
            return False

        if not self.schedule_daily_sync(time_str):
            logger.error("No se pudo programar la tarea de sincronización")
            return False

        # Iniciar el programador en un hilo separado
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = (
            True  # El hilo terminará cuando el programa principal termine
        )
        self.scheduler_thread.start()

        logger.info(
            f"Servicio de programación iniciado. Sincronización diaria a las {time_str}"
        )
        return True

    def stop(self) -> bool:
        """
        Detiene el servicio de programación.

        Returns:
            bool: True si el servicio se detuvo correctamente, False en caso contrario.
        """
        if not self.is_running:
            logger.warning("El servicio de programación no está en ejecución")
            return False

        self.is_running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(5)  # Esperar hasta 5 segundos a que termine

        logger.info("Servicio de programación detenido")
        return True
