"""
Esquemas de datos (data schemas) para la API de Domotica Scrapper.

Este módulo define los modelos Pydantic utilizados para la validación,
serialización y documentación de la API.
"""

from typing import Dict, Optional, Any
from pydantic import BaseModel, field_validator


class ProductoDomotica(BaseModel):
    """
    Modelo que representa un producto en el sistema Domotica INC.

    Este esquema es utilizado para la extracción y presentación de datos
    de productos obtenidos mediante web scraping.
    """

    categoria: str
    """Categoría del producto (ej. 'Entradas', 'Platos Fuertes', 'Postres')"""

    nombre: str
    """Nombre completo del producto"""

    cantidad: int = 1
    """Cantidad del producto pedido o disponible"""

    precio: float
    """Precio del producto en moneda local"""

    @field_validator("precio")
    @classmethod
    def precio_must_be_positive(cls, v: float) -> float:
        """Validar que el precio sea positivo."""
        if v <= 0:
            raise ValueError("El precio debe ser mayor que cero")
        return round(v, 2)  # Redondear a dos decimales

    @field_validator("cantidad")
    @classmethod
    def cantidad_must_be_positive(cls, v: int) -> int:
        """Validar que la cantidad sea positiva."""
        if v <= 0:
            raise ValueError("La cantidad debe ser mayor que cero")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "categoria": "Platos Fuertes",
                    "nombre": "Lomo Saltado",
                    "cantidad": 2,
                    "precio": 25.50,
                }
            ]
        }
    }


class MesaDomotica(BaseModel):
    """
    Modelo que representa una mesa en el sistema Domotica INC.

    Este esquema es utilizado para la extracción y presentación de datos
    de mesas obtenidos mediante web scraping.
    """

    identificador: str
    """Identificador único de la mesa"""

    zona: str
    """Zona o área del restaurante donde se ubica la mesa"""

    ocupado: bool
    """Estado de ocupación de la mesa"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"identificador": "MESA-01", "zona": "Terraza", "ocupado": False}
            ]
        }
    }

    def __str__(self) -> str:
        return f"Mesa {self.identificador} en zona {self.zona} - {'Ocupada' if self.ocupado else 'Libre'}"


class HealthResponse(BaseModel):
    """
    Modelo para la respuesta del endpoint de health check.
    """

    error: Optional[str] = None
    """Mensaje de error, si existe alguno"""

    status: int
    """Código de estado HTTP"""

    data: Dict[str, Any]
    """Datos del estado del servicio"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": None,
                    "status": 200,
                    "data": {"status": "online", "timestamp": "2025-10-08T12:00:00Z"},
                }
            ]
        }
    }


class WebSocketMessage(BaseModel):
    """
    Modelo para los mensajes enviados a través de WebSocket.
    """

    evento: str
    """Tipo de evento WebSocket"""

    payload: Dict[str, Any]
    """Contenido del mensaje"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "evento": "actualizacion_mesa",
                    "payload": {
                        "identificador": "MESA-05",
                        "zona": "Salón Principal",
                        "ocupado": True,
                    },
                }
            ]
        }
    }
