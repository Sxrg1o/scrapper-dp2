"""
Módulo de acceso a la plataforma Domotica Perú.

Este módulo proporciona una interfaz para automatizar la navegación y scraping
del sitio web de Domotica Perú utilizando Selenium y BeautifulSoup.
"""

import logging
import re
import time
import urllib.parse
from typing import List, Optional, Type, Any

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from bs4.element import Tag

from src.core.config import get_settings
from src.model.schemas import MesaDomotica, ProductoDomotica

# Configurar logging para este módulo
logger = logging.getLogger(__name__)


class DomoticaPage:
    """
    Clase para automatizar la navegación y el scraping del sitio Domotica Perú.

    Esta clase utiliza Selenium para automatizar la navegación web y BeautifulSoup
    para extraer datos de las páginas de manera más eficiente. Implementa métodos
    para iniciar sesión, navegar por el sitio y extraer información relevante.

    Attributes
    ----------
    username : str
        Nombre de usuario para iniciar sesión
    password : str
        Contraseña para iniciar sesión
    driver : webdriver.Chrome
        Instancia del navegador Chrome controlado por Selenium
    base_url : str
        URL base del sitio web de Domotica Perú
    timeout : int
        Tiempo máximo de espera para operaciones en el navegador
    """

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Inicializa la clase DomoticaPage con credenciales y configura el driver.

        Parameters
        ----------
        username : str, opcional
            Nombre de usuario para iniciar sesión. Si no se proporciona, se usa el de la configuración.
        password : str, opcional
            Contraseña para iniciar sesión. Si no se proporciona, se usa la de la configuración.

        Notes
        -----
        Configura una instancia de Chrome WebDriver con opciones optimizadas
        para scraping en función del entorno.
        """
        settings = get_settings()

        self.username = username or settings.domotica_username
        self.password = password or settings.domotica_password
        self.base_url = settings.domotica_base_url
        self.timeout = settings.domotica_timeout

        # Configurar opciones de Chrome optimizadas para scraping
        chrome_options = Options()

        # Opciones recomendadas para scraping
        if not settings.debug:
            # chrome_options.add_argument("--headless")
            pass

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--start-maximized")

        # Inicializar el driver
        logger.info(f"Inicializando WebDriver para {self.base_url}")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(self.timeout)
        self.driver.get(self.base_url)
        logger.debug("WebDriver inicializado y página cargada")

    def build_url(self, path: str) -> str:
        """
        Construye una URL completa usando urllib.parse.urljoin.

        Parameters
        ----------
        path : str
            La ruta relativa a añadir a la base_url.

        Returns
        -------
        str
            La URL completa correctamente formateada.
        """
        return urllib.parse.urljoin(self.base_url, path)

    def check_url(self, expected_url: str) -> bool:
        """
        Verifica si la URL actual del navegador coincide con la URL esperada.

        Parameters
        ----------
        expected_url : str
            La URL que se espera que esté cargada en el navegador.

        Returns
        -------
        bool
            True si la URL actual coincide con la esperada, False en caso contrario.
        """
        current_url = self.driver.current_url
        if current_url == expected_url:
            logger.debug(f"La URL actual coincide con la esperada: {expected_url}")
            return True
        else:
            logger.warning(
                f"La URL actual ({current_url}) no coincide con la esperada ({expected_url})"
            )
            return False

    def login(self) -> bool:
        """
        Inicia sesión en el sitio web de Domotica Perú utilizando las credenciales proporcionadas.

        Returns
        -------
        bool
            True si el inicio de sesión es exitoso, False si hay algún error.

        Raises
        ------
        Exception
            Si no se pueden encontrar los elementos necesarios para iniciar sesión
            o si el inicio de sesión falla.
        """
        if not self.check_url(self.base_url):
            logger.error("No se encuentra en la página de inicio de sesion.")
            return False

        try:
            logger.debug("Esperando campos de inicio de sesión")
            user_input = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="text"]'))
            )

            logger.debug("Localizando campo de contraseña")
            password_input = self.driver.find_element(
                By.CSS_SELECTOR, 'input[type="password"]'
            )

            # Registrar acción - ocultar la contraseña real
            logger.debug(f"Introduciendo credenciales para usuario: {self.username}")
            user_input.send_keys(self.username)
            # Ingresar la contraseña real
            password_input.clear()
            password_input.send_keys(self.password)

            # Encuentra y haz clic en el botón de "INICIAR SESION"
            logger.debug("Buscando botón de inicio de sesión")
            login_button = self.driver.find_element(
                By.XPATH, '//button[contains(span, "INICIAR SESION")]'
            )

            logger.debug("Haciendo clic en botón de inicio de sesión")
            login_button.click()

            # Espera a que la URL cambie al panel después del login
            logger.debug("Esperando redirección al panel de control")
            WebDriverWait(self.driver, self.timeout).until(EC.url_contains("/panel"))

            # Verificar explícitamente que estamos en el panel
            panel_url = self.build_url("panel")
            if not self.check_url(panel_url):
                logger.error("Redirección al panel falló después del login")
                logger.debug(
                    f"URL actual: {self.driver.current_url}, URL esperada: {panel_url}"
                )
                return False
            logger.info("Inicio de sesión exitoso")

        except TimeoutException as e:
            logger.error(f"Timeout durante el inicio de sesión: {str(e)}")
            return False
        except NoSuchElementException as e:
            logger.error(
                f"Elemento no encontrado durante el inicio de sesión: {str(e)}"
            )
            return False
        except Exception as e:
            logger.error(f"Error durante el inicio de sesión: {str(e)}")
            return False

        return True

    def navigate_to_panel(self) -> bool:
        """
        Navega al panel de control después de iniciar sesión.

        Returns
        -------
        bool
            True si la navegación al panel es exitosa, False en caso contrario.
        """
        panel_url = self.build_url("panel")
        logger.info(f"Navegando al panel de control: {panel_url}")
        self.driver.get(panel_url)

        if not self.check_url(panel_url):
            logger.error("No se pudo navegar al panel de control.")
            logger.debug(
                f"URL actual: {self.driver.current_url}, URL esperada: {panel_url}"
            )
            return False

        logger.info("Navegación al panel de control exitosa.")
        return True

    def navigate_to_mesas(self) -> bool:
        """
        Navega a la sección de mesas de la plataforma.

        Si no estamos autenticados o no estamos en el panel, navega al panel primero.

        Returns
        -------
        bool
            True si la navegación es exitosa, False en caso contrario
        """
        try:
            self.navigate_to_panel()

            try:
                # Método 1: Buscar directamente por el texto "Mesas" en un h4
                mesa_option = WebDriverWait(self.driver, self.timeout).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//h4[contains(text(), 'Mesas')]")
                    )
                )
                logger.debug("Opción 'Mesas' encontrada por texto en h4")

            except TimeoutException:
                # Método 2: Intentar encontrar por la estructura de la tarjeta con imagen de mesa
                mesa_option = WebDriverWait(self.driver, self.timeout).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//div[contains(@class, 'v-card--link')]//div[contains(@class, 'v-image') and contains(@style, 'mesa.png')]/..",
                        )
                    )
                )
                logger.debug("Opción 'Mesas' encontrada por imagen de mesa")

            # Hacer clic en la opción de mesas
            logger.debug("Haciendo clic en la opción de Mesas")
            mesa_option.click()

            # Esperar a que cargue la página de mesas
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(@class, 'v-card')]//h2")
                )
            )
            mesas_url = self.build_url("lista_mesas")
            if not self.check_url(mesas_url):
                logger.error("No se pudo navegar al panel de mesas.")
                logger.debug(
                    f"URL actual: {self.driver.current_url}, URL esperada: {mesas_url}"
                )
                return False

        except TimeoutException as e:
            logger.error(f"Timeout durante la navegación a mesas: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error durante la navegación a mesas: {str(e)}")
            return False

        return True

    def scrap_mesas(self) -> List[MesaDomotica]:
        """
        Extrae la lista de mesas disponibles en la plataforma.

        Returns
        -------
        List[MesaDomotica]
            Lista de objetos MesaDomotica con la información extraída.
        """
        try:
            self.navigate_to_mesas()
        except Exception as e:
            logger.error(f"Error al navegar a mesas antes de scrapear: {str(e)}")
            return []

        logger.info("Extrayendo lista de mesas")
        mesas: List[MesaDomotica] = []

        start_time = time.time()
        try:
            # Obtener el HTML de la página
            logger.debug("Obteniendo código fuente de la página")
            page_source = self.driver.page_source

            # Parsear con BeautifulSoup
            logger.debug("Parseando HTML con BeautifulSoup")
            soup = BeautifulSoup(page_source, "html.parser")

            # Extracción de datos
            mesas: List[MesaDomotica] = []
            logger.debug("Buscando elementos de mesa en el DOM")

            # Buscar todas las tarjetas de mesas
            card_elements = soup.find_all("div", class_="v-card--link")
            logger.debug(f"Encontrados {len(card_elements)} tarjetas de mesa")

            for idx, card_element in enumerate(card_elements):
                try:
                    # Extraer datos específicos con trazabilidad
                    logger.debug(f"Procesando mesa #{idx+1}")

                    # Obtener el color de fondo (puede indicar el estado)
                    bg_color = str(card_element.get("style", ""))

                    # Obtener el texto dentro de la tarjeta
                    card_text_div = card_element.find("div", class_="v-card__text")
                    if not card_text_div:
                        logger.warning(
                            f"No se encontró el div de texto en la mesa #{idx+1}"
                        )
                        continue

                    # Extraer el número de mesa del h2
                    numero_element = card_text_div.find("h2", class_="black--text")
                    numero: str = (
                        numero_element.text.strip() if numero_element else "Desconocido"
                    )

                    # Extraer el estado (puede estar en el párrafo o determinarse por el color)
                    estado_element = card_text_div.find("p", class_="white--text")
                    estado_texto = (
                        estado_element.text.strip()
                        if estado_element and estado_element.text.strip()
                        else ""
                    )

                    # Determinar estado basado en el color si no hay texto explícito
                    if not estado_texto:
                        if "rgb(70, 255, 0)" in bg_color:  # Verde
                            estado_texto = "Disponible"
                        elif "rgb(255, 45, 0)" in bg_color:  # Rojo
                            estado_texto = "Ocupada"
                        elif "rgb(255, 241, 0)" in bg_color:  # Amarillo
                            estado_texto = "Reservada"
                        else:
                            estado_texto = "Estado desconocido"

                    mesas.append(
                        MesaDomotica(
                            identificador=numero,
                            zona="Desconocida",
                            ocupado=estado_texto == "Ocupada",
                        )
                    )
                    logger.debug(f"Mesa extraída: {numero} - Estado: {estado_texto}")

                except Exception as e:
                    logger.error(
                        f"Error al extraer datos de la mesa #{idx+1}: {str(e)}"
                    )

            # Registrar resultados y tiempo total
            elapsed_time = time.time() - start_time
            logger.info(
                f"Extracción completada: {len(mesas)} mesas en {elapsed_time:.2f} segundos"
            )

        except Exception as e:
            logger.error(f"Error durante la extracción de datos: {str(e)}")
            return []

        return mesas

    def navigate_to_mesa_comanda(self, mesa_id: Optional[str] = None) -> bool:
        """
        Navega a la página de comanda de una mesa específica.
        Si no se proporciona mesa_id, intentará encontrar una mesa libre automáticamente.

        Para acceder a la información de platos, es necesario que la mesa esté libre
        (con fondo verde en la interfaz).

        Parameters
        ----------
        mesa_id : str, opcional
            Identificador único de la mesa. Si no se proporciona, se buscará una mesa libre.

        Returns
        -------
        bool
            True si la navegación es exitosa, False en caso contrario
        """
        try:
            # Primero navegamos a la lista de mesas
            if not self.navigate_to_mesas():
                logger.error("No se pudo navegar a la lista de mesas")
                return False

            # Si no se proporcionó un ID específico, buscamos una mesa libre
            logger.info("Buscando una mesa libre automáticamente")
            try:
                # Buscar una mesa con fondo verde (disponible)
                mesa_libre = WebDriverWait(self.driver, self.timeout).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//div[contains(@class, 'v-card--link') and contains(@style, 'rgb(70, 255, 0)')]",
                        )
                    )
                )

                mesa_num_element = mesa_libre.find_element(
                    By.XPATH, ".//h2[contains(@class, 'black--text')]"
                )
                mesa_id = mesa_num_element.text.strip()
                logger.info(f"Mesa libre encontrada: {mesa_id}")
                # Clic en la mesa libre
                mesa_libre.click()
                return True

            except TimeoutException:
                logger.error("No se encontraron mesas libres disponibles")
                return False

        except TimeoutException as e:
            logger.error(
                f"Timeout durante la navegación a comanda de mesa {mesa_id}: {str(e)}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Error durante la navegación a comanda de mesa {mesa_id}: {str(e)}"
            )
            return False

    def scrap_platos(self) -> List[ProductoDomotica]:
        pass
    
    def close(self) -> None:
        """
        Cierra el navegador y libera los recursos.

        Esta función debe llamarse al finalizar el uso de la clase para
        asegurar que se liberan adecuadamente los recursos del navegador.
        """
        try:
            logger.info("Cerrando sesión del navegador")
            self.driver.quit()
            logger.debug("Navegador cerrado correctamente")
        except Exception as e:
            logger.error(f"Error al cerrar el navegador: {str(e)}")

    def __enter__(self):
        """
        Permite usar la clase con el patrón de contexto 'with'.

        Returns
        -------
        DomoticaPage
            La instancia actual
        """
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """
        Cierra automáticamente el navegador al salir del bloque 'with'.

        Parameters
        ----------
        exc_type : Optional[Type[BaseException]]
            Tipo de la excepción levantada, si la hay
        exc_val : Optional[BaseException]
            Instancia de la excepción levantada, si la hay
        exc_tb : Optional[Any]
            Traceback de la excepción, si la hay
        """
        self.close()
