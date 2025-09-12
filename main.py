import json
import requests
from typing import List, Dict

from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from time import sleep


app = FastAPI(title="Little Caesars Menu API", description="API para obtener el menú de Little Caesars Perú y automatizar login", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Página principal con enlaces a las funciones disponibles."""
    return templates.TemplateResponse("index.html", {"request": request})


async def run_selenium_test():
    """Ejecuta el test de Selenium y retorna el resultado"""
    try:
        print("[SELENIUM] Iniciando test de Selenium...")
        
        # Configurar opciones para Chrome en entorno Docker
        print("[SELENIUM] Configurando opciones de Chrome...")
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Configurar el driver de Chrome usando webdriver_manager
        print("[SELENIUM] Instalando ChromeDriver... (puede tardar)")
        service = Service(ChromeDriverManager().install())
        print("[SELENIUM] Iniciando driver de Chrome...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        result = {"status": "success", "steps": []}
        
        try:
            result["steps"].append("Abriendo página de login...")
            print("[SELENIUM] Intentando acceder...")
            # Usar ruta absoluta con protocolo file://
            import os
            login_path = os.path.abspath("login.html")
            file_url = f"file://{login_path}"
            print(f"[SELENIUM] Intentando acceder a: {file_url}")
            driver.get(file_url)
            print("[SELENIUM] Página de login cargada con éxito")

            # Ingresar usuario
            result["steps"].append("Ingresando usuario: robot")
            print("[SELENIUM] Buscando campo de usuario...")
            username = driver.find_element(By.NAME, "username")
            print("[SELENIUM] Ingresando usuario")
            username.send_keys("robot")

            # Ingresar contraseña
            result["steps"].append("Ingresando contraseña: robot")
            print("[SELENIUM] Buscando campo de contraseña...")
            password = driver.find_element(By.NAME, "password")
            print("[SELENIUM] Ingresando contraseña")
            password.send_keys("robot")

            # Clic en login
            result["steps"].append("Haciendo clic en el botón de login...")
            print("[SELENIUM] Buscando botón de submit...")
            submit = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            print("[SELENIUM] Haciendo clic en botón de login...")
            submit.click()

            # Esperar mensaje de éxito
            result["steps"].append("Esperando mensaje de éxito...")
            print("[SELENIUM] Esperando mensaje de éxito (timeout: 10s)...")
            success_message = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".success-box"))
            )
            print("[SELENIUM] Mensaje de éxito encontrado")

            # Obtener hora
            print("[SELENIUM] Buscando elemento con la hora...")
            hora = driver.find_element(By.CLASS_NAME, "hora").text
            print(f"[SELENIUM] Hora obtenida: {hora}")
            result["steps"].append(f"Login exitoso. {hora}. {success_message.text}")
        finally:
            print("[SELENIUM] Cerrando el navegador...")
            driver.quit()
            print("[SELENIUM] Navegador cerrado correctamente")

        print("[SELENIUM] Test completado con éxito")
        return result
    except Exception as e:
        print(f"[SELENIUM] ERROR: {str(e)}")
        import traceback
        print(f"[SELENIUM] Traceback: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}

@app.get("/test-selenium", tags=["Automatización"])
async def test_selenium():
    """Ejecuta un test automatizado con Selenium que prueba el login."""
    print("[API] Iniciando endpoint /test-selenium")
    
    # Usar una variable para detectar si ya estamos en medio de una prueba
    import os
    test_running = os.environ.get("SELENIUM_TEST_RUNNING")
    
    if test_running == "1":
        print("[API] Se detectó una ejecución recursiva. Evitando bucle infinito.")
        return {
            "status": "skipped",
            "message": "Prueba omitida para evitar bucle infinito. Ya hay una prueba en ejecución."
        }
    
    try:
        # Marcar que estamos ejecutando la prueba
        os.environ["SELENIUM_TEST_RUNNING"] = "1"
        
        import time
        start_time = time.time()
        result = await run_selenium_test()
        elapsed_time = time.time() - start_time
        print(f"[API] Endpoint /test-selenium completado en {elapsed_time:.2f} segundos")
        return result
    finally:
        # Limpiar el indicador incluso si hay errores
        os.environ.pop("SELENIUM_TEST_RUNNING", None)

def fetch_menu() -> List[Dict[str, str]]:
    base_url = "https://pe.littlecaesars.com/page-data"
    menu_data_url = f"{base_url}/es-pe/menu/page-data.json"

    with requests.Session() as session:
        resp = session.get(menu_data_url)
        resp.raise_for_status()
        page_data = resp.json()

        hashes = page_data.get("staticQueryHashes", [])
        menu_items = []

        def find_items(obj):
            """Busca recursivamente objetos con name, price y description."""
            if isinstance(obj, dict):
                if {"name", "price", "description"} <= obj.keys():
                    menu_items.append({
                        "name": str(obj["name"]).strip(),
                        "price": str(obj["price"]).strip(),
                        "description": str(obj["description"]).strip()
                    })
                else:
                    for v in obj.values():
                        find_items(v)
            elif isinstance(obj, list):
                for item in obj:
                    find_items(item)

        # Recorremos cada hash y extraemos ítems
        for h in hashes:
            static_url = f"{base_url}/sq/d/{h}.json"
            try:
                data = session.get(static_url).json().get("data", {})
                find_items(data)
            except (requests.RequestException, json.JSONDecodeError):
                continue

    # Quitar duplicados
    unique_items = { (i["name"], i["price"]): i for i in menu_items }
    return list(unique_items.values())


@app.get("/PizzasLitleCesar", response_class=JSONResponse, tags=["Menú"])
def get_pizzas_little_cesar():
    """Devuelve el menú de Little Caesars Perú (nombre, precio y descripción de cada ítem)."""
    try:
        menu = fetch_menu()
        return menu
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
