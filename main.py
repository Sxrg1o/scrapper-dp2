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
@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == "robot" and password == "robot":
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return templates.TemplateResponse("success.html", {"request": request, "now": now})
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Credenciales incorrectas"})


async def run_selenium_test():
    """Ejecuta el test de Selenium y retorna el resultado"""
    try:
        # Configurar el driver de Chrome usando webdriver_manager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        result = {"status": "success", "steps": []}
        
        try:
            # Abrir la página de login
            result["steps"].append("Abriendo página de login...")
            driver.get("http://127.0.0.1:9000/login")
            sleep(2)

            # Ingresar usuario
            result["steps"].append("Ingresando usuario: robot")
            username = driver.find_element(By.NAME, "username")
            username.send_keys("robot")
            sleep(1)

            # Ingresar contraseña
            result["steps"].append("Ingresando contraseña: robot")
            password = driver.find_element(By.NAME, "password")
            password.send_keys("robot")
            sleep(1)

            # Clic en login
            result["steps"].append("Haciendo clic en el botón de login...")
            submit = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit.click()

            # Esperar mensaje de éxito
            result["steps"].append("Esperando mensaje de éxito...")
            success_message = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".success-box"))
            )

            # Obtener hora
            hora = driver.find_element(By.CLASS_NAME, "hora").text
            result["steps"].append(f"Login exitoso. {hora}")
            sleep(3)

        finally:
            driver.quit()

        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/test-selenium", tags=["Automatización"])
async def test_selenium():
    """Ejecuta un test automatizado con Selenium que prueba el login."""
    return await run_selenium_test()

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
