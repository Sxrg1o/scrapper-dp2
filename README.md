# Scraper de Domotica Perú

Un sistema de web scraping para la plataforma de Domotica Perú, implementado con una arquitectura en capas, utilizando Selenium y BeautifulSoup para la extracción de datos.

## Características

- 🚀 Extracción de datos de la plataforma Domotica Perú
- 📊 Arquitectura en capas bien definida
- 🔍 Trazabilidad completa de operaciones
- 🛡️ Gestión de configuración segura
- 📝 Documentación detallada
- 🧪 Pruebas unitarias

## Arquitectura

El proyecto sigue una arquitectura en capas:

```
scrapper-dp2/
├── src/
│   ├── api/            # Capa de API
│   ├── core/           # Configuración y funcionalidades transversales
│   ├── model/          # Modelos de datos
│   ├── repository/     # Acceso a datos externos (scraping)
│   ├── service/        # Lógica de negocio
│   └── main.py         # Punto de entrada de la aplicación
├── test/               # Pruebas unitarias e integración
└── examples/           # Ejemplos de uso
```

## Requisitos

- Python 3.10+
- Chrome/Chromium Browser
- ChromeDriver compatible con tu versión de Chrome

## Instalación

1. Clona el repositorio:
```bash
git clone https://github.com/dp2-eder/scrapper-dp2.git
cd scrapper-dp2
```

2. Crea un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instala las dependencias:
```bash
pip install -r requirements.txt
```

4. **Configura las variables de entorno**:

Crea un archivo `.env` en la raíz del proyecto (ya existe uno por defecto):

```bash
# .env
DOMOTICA_BASE_URL=https://domotica-peru.com/
DOMOTICA_USERNAME=tu_usuario
DOMOTICA_PASSWORD=tu_contraseña
SECRET_KEY=tu-clave-secreta-aqui
```

> **Nota**: Las credenciales por defecto (`USUARIO` / `CONTRASEÑA`) están configuradas en el archivo `.env`. 
> Puedes modificarlas directamente en `.env` o establecer variables de entorno en tu sistema.

**Prioridad de carga de configuración:**
1. Variables de entorno del sistema (mayor prioridad)
2. Archivo `.env`
3. Valores por defecto en `src/core/config.py` (menor prioridad)

3. Instala las dependencias:
```bash
pip install -r requirements.txt
```

## Configuración

El sistema utiliza un archivo `.env` para configurar credenciales y parámetros:

```bash
# Crear archivo .env en la raíz del proyecto
DOMOTICA_USERNAME=tu_usuario
DOMOTICA_PASSWORD=tu_contraseña
DOMOTICA_BASE_URL=https://url-de-domotica
DOMOTICA_TIMEOUT=10
```

## Uso

### Flujo Completo de Scraping

El ejemplo completo muestra cómo realizar todo el flujo de scraping:

```bash
python examples/complete_scraping_flow.py
```

Este script realiza:
1. Login en la plataforma
2. Navegación al panel principal
3. Navegación a la lista de mesas
4. Extracción de datos de las mesas
5. Navegación a la comanda de una mesa específica
6. Extracción de categorías de productos
7. Extracción de todos los productos de todas las categorías

### Ejemplo de código básico

```python
from src.repository.domotica_page import DomoticaPage

# Crear instancia del scraper con el contexto manager
with DomoticaPage() as page:
    # Iniciar sesión
    if page.login():
        # Navegar al panel
        page.navigate_to_panel()
        
        # Navegar a mesas
        if page.navigate_to_tables():
            # Obtener datos de las mesas
            mesas = page.scrape_tables_data()
            
            # Seleccionar la primera mesa disponible
            if mesas:
                mesa = mesas[0]
                print(f"Mesa: {mesa.identificador}, Zona: {mesa.zona}")
                
                # Navegar a la comanda de la mesa
                if page.navigate_to_mesa_comanda(mesa.identificador):
                    # Extraer productos
                    productos = page.scrape_productos()
                    
                    # Mostrar productos encontrados
                    for producto in productos:
                        print(f"{producto.nombre} - {producto.categoria} - S/.{producto.precio}")
```

4. Configura las variables de entorno:
```bash
cp .env.example .env
# Edita el archivo .env con tus credenciales y configuración
```

## Uso

### Como módulo

```python
from src.repository.domotica_page import DomoticaPage

# Usando el patrón "with" para gestión automática de recursos
with DomoticaPage() as scraper:
    # Login
    scraper.login()
    
    # Navegar a la sección de mesas
    scraper.navigate_to_tables()
    
    # Extraer datos
    mesas = scraper.scrape_tables_data()
    
    # Procesar los datos
    for mesa in mesas:
        print(f"Mesa: {mesa['nombre']} - Estado: {mesa['estado']}")
```

### Mediante el ejemplo incluido

```bash
python examples/use_domotica_scraper.py
```

## Configuración

La configuración se realiza a través de variables de entorno o un archivo `.env`. Las principales variables son:

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| DOMOTICA_BASE_URL | URL base de la plataforma | https://example.com/ |
| DOMOTICA_USERNAME | Nombre de usuario | your_username |
| DOMOTICA_PASSWORD | Contraseña | your_password |
| DOMOTICA_TIMEOUT | Timeout en segundos | 30 |
| DEBUG | Modo de depuración | False |

## Desarrollo

### Ejecutar pruebas

```bash
python -m unittest discover -s test
```

### Contribuir

1. Crea un fork del proyecto
2. Crea una rama para tu funcionalidad (`git checkout -b feature/amazing-feature`)
3. Realiza tus cambios y haz commit (`git commit -m 'Add some amazing feature'`)
4. Sube los cambios a tu repositorio (`git push origin feature/amazing-feature`)
5. Crea un Pull Request

## Licencia

Este proyecto está licenciado bajo [MIT License](LICENSE).