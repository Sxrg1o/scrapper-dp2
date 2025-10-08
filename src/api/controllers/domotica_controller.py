"""
Controlador para los endpoints de la API de domótica.

Este módulo implementa los endpoints para consumir datos de productos y mesas
obtenidos mediante web scraping desde el sistema Domotica INC.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List, Any

from src.model.schemas import ProductoDomotica, MesaDomotica, HealthResponse

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
        "data": {
            "status": "online",
            "timestamp": "2025-10-08T12:00:00Z"
        }
    }


@router.get("/productos", response_model=List[ProductoDomotica], tags=["Productos"])
async def obtener_productos() -> List[ProductoDomotica]:
    """
    Obtiene la lista de productos disponibles.
    
    Extrae datos de productos del sistema Domotica INC mediante web scraping.
    
    Returns:
        List[ProductoDomotica]: Lista de productos con su información
    """
    # En una implementación real, aquí se invocaría al servicio de scraping
    # Por ahora devolvemos datos de ejemplo
    return [
        ProductoDomotica(
            categoria="Entradas",
            nombre="Tequeños",
            stock=20,
            precio=12.50
        ),
        ProductoDomotica(
            categoria="Platos Fuertes",
            nombre="Lomo Saltado",
            stock=15,
            precio=25.50
        ),
        ProductoDomotica(
            categoria="Postres",
            nombre="Tres Leches",
            stock=8,
            precio=10.00
        )
    ]


@router.get("/mesas", response_model=List[MesaDomotica], tags=["Mesas"])
async def obtener_mesas() -> List[MesaDomotica]:
    """
    Obtiene la lista de mesas y su estado.
    
    Extrae datos de mesas del sistema Domotica INC mediante web scraping.
    
    Returns:
        List[MesaDomotica]: Lista de mesas con su información
    """
    # En una implementación real, aquí se invocaría al servicio de scraping
    # Por ahora devolvemos datos de ejemplo
    return [
        MesaDomotica(
            identificador="MESA-01",
            zona="Terraza",
            ocupado=False
        ),
        MesaDomotica(
            identificador="MESA-02",
            zona="Salón Principal",
            ocupado=True
        ),
        MesaDomotica(
            identificador="BARRA-01",
            zona="Barra",
            ocupado=False
        )
    ]


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