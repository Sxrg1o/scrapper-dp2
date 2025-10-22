"""
Esquemas de datos (data schemas) para la API de Domotica Scrapper.

Este módulo define los modelos Pydantic utilizados para la validación,
serialización y documentación de la API.
"""

from enum import Enum
from typing import Dict, Optional, Any, Union

from pydantic import BaseModel, field_validator


class MesaEstadoEnum(str, Enum):
    """Enumeración de estados posibles para una mesa."""

    DISPONIBLE = "disponible"
    OCUPADA = "ocupada"
    RESERVADA = "reservada"
    DESCONOCIDO = "desconocido"

    @classmethod
    def from_str(cls, raw_value: Optional[str]) -> "MesaEstadoEnum":
        """Normaliza distintos textos o estilos para mapearlos a un estado."""

        if not raw_value:
            return cls.DESCONOCIDO

        normalized = raw_value.strip().lower()
        mapping = {
            "disponible": cls.DISPONIBLE,
            "libre": cls.DISPONIBLE,
            "mesa libre": cls.DISPONIBLE,
            "ocupada": cls.OCUPADA,
            "reservada": cls.RESERVADA,
            "reservado": cls.RESERVADA,
        }

        return mapping.get(normalized, cls.DESCONOCIDO)


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

    stock: str
    """Stock disponible del producto (puede ser número o texto como 'Agotado')"""

    precio: str
    """Precio del producto en moneda local (formato string desde el scraping)"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "categoria": "Platos Fuertes",
                    "nombre": "Lomo Saltado",
                    "stock": "15",
                    "precio": "25.50",
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

    nombre: str
    """Nombre/identificador de la mesa"""

    zona: str
    """Zona o área del restaurante donde se ubica la mesa"""

    nota: Optional[str] = None
    """Notas adicionales sobre la mesa"""

    estado: MesaEstadoEnum = MesaEstadoEnum.DISPONIBLE
    """Estado de la mesa (disponible, ocupada, reservada, etc.)"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "nombre": "P4",
                    "zona": "ZONA 3",
                    "nota": "PULPO",
                    "estado": "disponible",
                },
                {
                    "nombre": "Z LLEVAR 1",
                    "zona": "ZONA 1",
                    "nota": None,
                    "estado": "disponible",
                },
            ]
        }
    }

    def __str__(self) -> str:
        return f"Mesa {self.nombre} en zona {self.zona}"

    @field_validator("estado", mode="before")
    @classmethod
    def _ensure_enum(cls, value: Union[str, MesaEstadoEnum]) -> MesaEstadoEnum:
        """Permite recibir cadenas y las convierte al enum correspondiente."""

        if isinstance(value, MesaEstadoEnum):
            return value

        return MesaEstadoEnum.from_str(str(value))


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
