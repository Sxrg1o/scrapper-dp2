# FastAPI Little Caesars Menu API

Este proyecto es una API construida con FastAPI que expone un endpoint `/PizzasLitleCesar` para obtener el menú de Little Caesars Perú. Incluye documentación Swagger por defecto.

## Uso rápido

1. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Ejecuta el servidor:
   ```bash
   uvicorn main:app --reload
   ```
3. Accede a la documentación interactiva en: [http://localhost:8000/docs](http://localhost:8000/docs)

## Estructura
- `main.py`: Código principal de la API.
- `requirements.txt`: Dependencias del proyecto.

## Endpoint
- `GET /PizzasLitleCesar`: Devuelve el menú de Little Caesars Perú (nombre, precio y descripción de cada ítem).
