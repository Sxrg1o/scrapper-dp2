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

-----

## **Inserción de Platos**

### `POST /api/v1/platos`

Este endpoint permite insertar platos en una mesa específica y generar un comprobante electrónico.

  - **Método:** `POST`
  - **Content-Type:** `application/json`

#### **Estructura del Request Body**

⚠️ **IMPORTANTE:** El payload DEBE incluir estos 3 campos principales:

1. **`mesa`** (obligatorio): Información de la mesa
2. **`platos`** (obligatorio): Array de platos a insertar  
3. **`comprobante`** (obligatorio): Datos para el comprobante electrónico

```json
{
  "mesa": {
    "nombre": "J5",
    "zona": "ZONA 2",
    "nota": "JARDIN", 
    "estado": "ocupada"
  },
  "platos": [
    {
      "categoria": "CEVICHES",
      "nombre": "CEVICHE NORTENO",
      "stock": "1",
      "precio": "35.00"
    },
    {
      "categoria": "PIQUEOS",
      "nombre": "CHOROS A LA CHALACA", 
      "stock": "1",
      "precio": "30.00"
    }
  ],
  "comprobante": {
    "tipo_documento": "RUC",
    "numero_documento": "20123456789",
    "nombres_completos": "EMPRESA DEMO SAC",
    "direccion": "AV. LIMA 123 - LIMA",
    "observacion": "Pedido para mesa J5",
    "tipo_comprobante": "Factura"
  }
}
```

#### **Campos del Comprobante**

- **`tipo_documento`**: `"RUC"` o `"DNI"`
- **`numero_documento`**: Número del documento (RUC: 11 dígitos, DNI: 8 dígitos)
- **`nombres_completos`**: Nombre completo o razón social
- **`direccion`**: Dirección del cliente
- **`observacion`**: Observaciones adicionales
- **`tipo_comprobante`**: `"Factura"` (para RUC) o `"Boleta"` (para DNI)

#### **Respuesta Exitosa (200 OK)**

```json
{
  "success": true,
  "message": "Proceso completado - 2/2 platos insertados en mesa 'J5' - Comprobante llenado exitosamente - Logout exitoso",
  "mesa_nombre": "J5", 
  "platos_insertados": 2
}
```

#### **Respuesta de Error (400 Bad Request)**

```json
{
  "success": false,
  "message": "Error durante la inserción: [detalle del error]"
}
```
