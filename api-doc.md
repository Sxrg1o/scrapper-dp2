# Catálogo de API - Proyecto Scrapper Domótica

Esta API permite interactuar con los datos de platos y mesas del sistema domotica.

-----

## **Modelos de Datos**

Estos son los modelos de datos principales utilizados en las respuestas de la API.

### `ProductoDomotica`

Representa un plato disponible en el menú.

```typescript
interface ProductoDomotica {
  categoria: string; // La categoría del plato (ej. "Entradas", "Platos Fuertes", "Postres").
  nombre: string;    // El nombre del plato.
  stock: number;     // La cantidad de unidades disponibles en el inventario.
  precio: number;    // El precio del plato en la moneda local.
}
```

### `MesaDomotica`

Representa el estado y la ubicación de una mesa en el restaurante.

```typescript
interface MesaDomotica {
  identificador: string; // Un ID único para la mesa (ej. "MESA-01", "BARRA-03").
  zona: string;          // La zona del restaurante donde se encuentra la mesa (ej. "Terraza", "Salón Principal").
  ocupado: boolean;      // `true` si la mesa está ocupada, `false` si está libre.
}
```

-----

## **Endpoints de la API REST**

A continuación se detallan los endpoints disponibles.

### **Salud del Servicio**

#### `GET /api/v1/health`

Este endpoint se utiliza para verificar el estado y la disponibilidad del servicio. Es ideal para monitoreo y health checks.

  - **Método:** `GET`
  - **Parámetros:** Ninguno.
  - **Respuesta Exitosa (200 OK):**
    ```json
    {
      "error": null,
      "status": 200,
      "data": {
        "status": "online",
        "timestamp": "2025-10-05T18:56:29Z"
      }
    }
    ```


## **API WebSocket** 🌐

Para obtener actualizaciones en tiempo real sobre el estado de las mesas, puedes conectarte a nuestro servidor WebSocket.

### **Conexión**

  - **URL:** `ws://<tu-dominio>/ws/v1/mesas`

### **Eventos del Servidor**

Una vez conectado, el servidor emitirá eventos automáticamente cuando el estado de una mesa cambie. No es necesario que el cliente emita ningún evento, solo debe escuchar.

#### Evento: `actualizacion_mesa`

Este evento se envía cada vez que el estado de una o más mesas es actualizado (por ejemplo, cuando una mesa se ocupa o se libera).

  - **Payload:** El payload del mensaje será un objeto `MesaDomotica` o un array de `MesaDomotica` con la información actualizada.

  - **Ejemplo de Payload:**

    ```json
    {
      "evento": "actualizacion_mesa",
      "payload": {
        "identificador": "MESA-05",
        "zona": "Salón Principal",
        "ocupado": true
      }
    }
    ```
