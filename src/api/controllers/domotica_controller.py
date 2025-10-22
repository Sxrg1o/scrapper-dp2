"""
Controlador para los endpoints de la API de domótica.

Este módulo implementa los endpoints para consumir datos de productos y mesas
obtenidos mediante web scraping desde el sistema Domotica INC.
"""

from fastapi import APIRouter, Response, WebSocket, WebSocketDisconnect, BackgroundTasks
from typing import Dict, List, Any

from src.model.schemas import ProductoDomotica, MesaDomotica, HealthResponse
from src.service import domotica_service
from src.service.scheduler_service import SchedulerService

# Crear router para este controlador
router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Sistema"])
async def health_check() -> Dict[str, Any]:
    """
    Verifica el estado del servicio.

    Este endpoint es utilizado para monitoreo y healthchecks.

    Returns:
        HealthResponse: Información sobre el estado del servicio
    """
    return {
        "error": None,
        "status": 200,
        "data": {"status": "online", "timestamp": "2025-10-08T12:00:00Z"},
    }


@router.get("/productos", response_model=List[ProductoDomotica], tags=["Productos"])
async def obtener_productos() -> List[ProductoDomotica]:
    """
    Obtiene la lista de productos mediante scraping en tiempo real.
    
    Este endpoint ejecuta el scraping SOLO de productos:
    1. Inicia sesión en Domotica INC
    2. Navega a la sección de mesas
    3. Extrae SOLO los productos de todas las categorías
    4. Cierra sesión
    5. Devuelve los productos
    
    NOTA: Este proceso puede tardar varios segundos.
    
    Returns:
        List[ProductoDomotica]: Lista de productos con su información
    """
    return domotica_service.scrape_and_get_productos()


@router.get("/mesas", response_model=List[MesaDomotica], tags=["Mesas"])
async def obtener_mesas() -> List[MesaDomotica]:
    """
    Obtiene la lista de mesas mediante scraping en tiempo real.

    Este endpoint ejecuta el scraping SOLO de mesas:
    1. Inicia sesión en Domotica INC
    2. Navega a la sección de mesas
    3. Extrae SOLO la información de mesas desde 'Gestionar Mesas'
    4. Cierra sesión
    5. Devuelve las mesas

    NOTA: Este proceso puede tardar varios segundos.

    Returns:
        List[MesaDomotica]: Lista de mesas con su información
    """
    return domotica_service.scrape_and_get_mesas()

# Conexiones WebSocket activas
connected_websockets: List[WebSocket] = []


@router.websocket("/ws/mesas")
async def websocket_mesas(websocket: WebSocket):
    """
    Endpoint WebSocket para actualizaciones en tiempo real del estado de mesas.

    Permite a los clientes recibir notificaciones instantáneas cuando cambia
    el estado de una mesa en el sistema.

    Args:
        websocket: Conexión WebSocket del cliente
    """
    await websocket.accept()
    connected_websockets.append(websocket)

    try:
        while True:
            # Esperar mensajes del cliente, aunque en este caso
            # no los procesamos, solo mantenemos la conexión abierta
            _ = await websocket.receive_text()

    except WebSocketDisconnect:
        # Remover el websocket de la lista cuando el cliente se desconecta
        connected_websockets.remove(websocket)
