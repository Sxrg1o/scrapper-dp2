"""
Script para iniciar el servicio de sincronización programada.

Este script inicia el servicio de programación de tareas que sincroniza
los datos extraídos con la API de forma automática a intervalos definidos.
"""

import logging
import time
import signal
import sys
from src.service.scheduler_service import SchedulerService
from src.core.config import get_settings

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Instancia global del servicio
scheduler_service = None

def signal_handler(sig, frame):
    """Manejador de señales para detener el servicio de forma limpia."""
    logger.info("Señal de terminación recibida, deteniendo servicio...")
    if scheduler_service:
        scheduler_service.stop()
    sys.exit(0)

def main():
    """Función principal que inicia el servicio de sincronización programada."""
    global scheduler_service
    
    try:
        settings = get_settings()
        
        logger.info(f"Iniciando servicio de sincronización programada de {settings.app_name} v{settings.app_version}")
        logger.info(f"Entorno: {settings.environment}")
        
        # Configuración del tiempo de ejecución (por defecto a las 00:00)
        sync_time = "00:00"
        
        # Iniciar el servicio
        scheduler_service = SchedulerService()
        if scheduler_service.start(sync_time):
            logger.info(f"Servicio iniciado correctamente. Sincronización diaria programada a las {sync_time}")
            
            # Mantener el proceso en ejecución
            while True:
                time.sleep(60)
        else:
            logger.error("No se pudo iniciar el servicio de sincronización")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Interrupción del teclado recibida, deteniendo servicio...")
        if scheduler_service:
            scheduler_service.stop()
    except Exception as e:
        logger.error(f"Error al iniciar el servicio: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Registrar manejadores de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Iniciar la aplicación
    main()