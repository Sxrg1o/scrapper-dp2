"""
Módulo de acceso a la plataforma Domotica Perú.

Este módulo proporciona una interfaz para automatizar la navegación y scraping
del sitio web de Domotica Perú utilizando Selenium y BeautifulSoup.
"""

import logging
import re
import time
import urllib.parse
from contextlib import contextmanager
from typing import Dict, Iterator, List, Optional, Type, Any

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
from src.model.schemas import MesaDomotica, MesaEstadoEnum, ProductoDomotica

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
        self.logged_in = False

        # Configurar opciones de Chrome optimizadas para scraping
        chrome_options = Options()

        # Opciones recomendadas para scraping
        if not settings.debug:
            chrome_options.add_argument("--headless")

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
        if self.logged_in:
            logger.debug("Ya se ha iniciado sesión previamente")
            return True

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
            self.logged_in = True
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
        if not self.logged_in:
            logger.warning("No se ha iniciado sesión.")
            return self.login()

        try:
            self.driver.refresh()
            logger.info("Navegación al panel de control exitosa.")
        except Exception as e:
            logger.error(f"Error durante la navegación al panel: {str(e)}")
            return False
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
        except TimeoutException as e:
            logger.error(f"Timeout durante la navegación a mesas: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error durante la navegación a mesas: {str(e)}")
            return False

        return True

    @contextmanager
    def _open_mesas_modal(self) -> Iterator[None]:
        """Contexto que abre el modal "Gestionar Mesas" y garantiza su cierre."""

        modal_open = False

        try:
            opciones_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//button[.//span[contains(text(), "OPCIONES")]]')
                )
            )
            opciones_btn.click()
            logger.debug("Botón OPCIONES clickeado")

            gestionar_mesas_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        '//div[contains(@class, "v-list-item__title") and contains(text(), "Gestionar Mesas")]',
                    )
                )
            )
            gestionar_mesas_btn.click()
            modal_open = True
            logger.debug("Gestionar Mesas clickeado")

            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[contains(@class, "v-data-table__wrapper")]/table')
                )
            )

            yield

        finally:
            if modal_open:
                try:
                    close_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable(
                            (
                                By.XPATH,
                                '//div[contains(@class, "v-system-bar") and contains(@class, "v-system-bar--window") and contains(@class, "theme--dark")]/button[contains(@class, "v-icon") and contains(@class, "mdi-close") and contains(@class, "theme--dark")]',
                            )
                        )
                    )
                    close_btn.click()
                    logger.debug("Modal de mesas cerrado")
                except Exception as close_err:
                    logger.warning("No se pudo cerrar el modal de mesas: %s", close_err)

                try:
                    WebDriverWait(self.driver, self.timeout).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//div[contains(@class, 'v-card--link')]")
                        )
                    )
                except Exception:
                    logger.debug(
                        "No se pudo confirmar la disponibilidad visual tras cerrar el modal"
                    )

    def scrap_mesas(self) -> List[MesaDomotica]:
        """
        Extrae la lista de mesas disponibles en la plataforma.

        Returns
        -------
        List[MesaDomotica]
            Lista de objetos MesaDomotica con la información extraída.
        """

        mesas_metadata: Dict[str, MesaDomotica] = {}

        try:
            self.navigate_to_mesas()
            mesas_metadata = self.scrap_mesas_metadata()
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

                    lookup_key = numero.strip().lower()
                    metadata = mesas_metadata.get(lookup_key)
                    mesas.append(
                        MesaDomotica(
                            nombre=metadata.nombre if metadata else numero,
                            zona=metadata.zona if metadata else "Desconocida",
                            nota=metadata.nota if metadata else None,
                            estado=MesaEstadoEnum.from_str(estado_texto),
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

    def scrap_mesas_metadata(self) -> Dict[str, MesaDomotica]:
        """Obtiene un diccionario de metadatos de mesas indexado por nombre normalizado."""

        metadata: Dict[str, MesaDomotica] = {}

        with self._open_mesas_modal():
            mesa_rows = self.driver.find_elements(
                By.XPATH,
                '//div[contains(@class, "v-data-table__wrapper")]/table/tbody/tr',
            )
            logger.debug("Encontradas %d filas de mesas", len(mesa_rows))

            for row in mesa_rows:
                columnas = row.find_elements(By.XPATH, "./td")
                if len(columnas) < 3:
                    continue

                nombre = columnas[0].text.strip()
                if not nombre:
                    continue

                zona = columnas[1].text.strip() or "Desconocida"
                nota = columnas[2].text.strip() or None

                metadata[nombre.lower()] = MesaDomotica(
                    nombre=nombre,
                    zona=zona,
                    nota=nota,
                    estado=MesaEstadoEnum.DESCONOCIDO,
                )

        logger.info("Extraídas %d mesas desde el modal", len(metadata))
        return metadata

    def get_only_products(self) -> dict:
        """
        Extrae SOLO los productos de todas las categorías.

        Este método es más ligero que get_full_category ya que no extrae
        información de mesas.

        Returns
        -------
        dict
            Diccionario con las siguientes claves:
            - category: Lista de categorías con sus productos
            - status: Estado de la operación
            - elapsed_seconds: Tiempo transcurrido
        """
        import time

        start_time = time.time()
        menu_data = []

        try:
            # Hacer clic en el primer card de categoría para acceder al menú
            try:
                first_card = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            '(//div[contains(@class, "v-card v-card--link v-sheet theme--light elevation-5")])[1]',
                        )
                    )
                )
                first_card.click()
                logger.debug("Primer card de categoría clickeado")
            except Exception as first_card_err:
                elapsed = time.time() - start_time
                logger.error(f"Error al hacer clic en primer card: {first_card_err}")
                return {
                    "category": [],
                    "status": f"first_card_error: {first_card_err}",
                    "elapsed_seconds": elapsed,
                }

            # Extraer categorías y productos
            # Obtener todos los cards de categoría (hoverable)
            category_cards = WebDriverWait(self.driver, 10).until(
                lambda d: d.find_elements(
                    By.XPATH,
                    '//div[contains(@class, "hoverable") and contains(@class, "v-card") and contains(@class, "v-card--link") and contains(@class, "v-sheet") and contains(@class, "theme--light")]',
                )
            )

            if not category_cards:
                elapsed = time.time() - start_time
                logger.warning("No se encontraron cards de categoría")
                return {
                    "category": [],
                    "status": "no_category_cards_found",
                    "elapsed_seconds": elapsed,
                }

            logger.info(f"Encontradas {len(category_cards)} categorías")

            for idx in range(len(category_cards)):
                # Refrescar la lista de cards en cada iteración
                category_cards = WebDriverWait(self.driver, 10).until(
                    lambda d: d.find_elements(
                        By.XPATH,
                        '//div[contains(@class, "hoverable") and contains(@class, "v-card") and contains(@class, "v-card--link") and contains(@class, "v-sheet") and contains(@class, "theme--light")]',
                    )
                )
                card = category_cards[idx]
                btn = card

                try:
                    category_name_elem = WebDriverWait(btn, 10).until(
                        lambda b: b.find_element(
                            By.XPATH,
                            './/div[contains(@class, "v-card__text") and contains(@class, "text-center")]',
                        )
                    )
                    category_name = category_name_elem.text
                    logger.debug(f"Procesando categoría: {category_name}")
                except Exception as cat_err:
                    category_name = f"category_error_{idx}: {cat_err}"
                    logger.warning(
                        f"Error obteniendo nombre de categoría {idx}: {cat_err}"
                    )

                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable(btn)
                    ).click()
                except Exception as btn_click_err:
                    elapsed = time.time() - start_time
                    logger.error(
                        f"Error al hacer clic en categoría {idx}: {btn_click_err}"
                    )
                    return {
                        "category": menu_data,
                        "status": f"btn_click_error_{idx}: {btn_click_err}",
                        "elapsed_seconds": elapsed,
                    }

                # Extraer productos de la tabla
                products = []
                try:
                    rows = WebDriverWait(self.driver, 10).until(
                        lambda d: d.find_elements(
                            By.XPATH,
                            '//div[contains(@class, "v-data-table__wrapper")]/table/tbody/tr',
                        )
                    )

                    for row in rows:
                        cols = row.find_elements(By.XPATH, "./td")
                        if len(cols) == 3:
                            name = cols[0].text
                            stock = cols[1].text
                            price = cols[2].text
                            products.append(
                                {"name": name, "stock": stock, "price": price}
                            )

                    logger.debug(
                        f"Extraídos {len(products)} productos de categoría {category_name}"
                    )

                except Exception as prod_err:
                    elapsed = time.time() - start_time
                    logger.error(
                        f"Error extrayendo productos de categoría {idx}: {prod_err}"
                    )
                    return {
                        "category": menu_data,
                        "status": f"products_error_{idx}: {prod_err}",
                        "elapsed_seconds": elapsed,
                    }

                # Volver atrás con el ícono de flecha roja
                try:
                    back_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable(
                            (
                                By.XPATH,
                                '//i[contains(@class, "mdi-arrow-left") and contains(@class, "red--text")]',
                            )
                        )
                    )
                    back_btn.click()
                except Exception as back_err:
                    elapsed = time.time() - start_time
                    logger.error(
                        f"Error al volver atrás desde categoría {idx}: {back_err}"
                    )
                    return {
                        "category": menu_data,
                        "status": f"back_btn_error_{idx}: {back_err}",
                        "elapsed_seconds": elapsed,
                    }

                menu_data.append({"category": category_name, "products": products})

            elapsed = time.time() - start_time
            logger.info(
                f"Extracción de productos completada en {elapsed:.2f} segundos: {len(menu_data)} categorías"
            )
            return {
                "category": menu_data,
                "status": "products_obtained",
                "elapsed_seconds": elapsed,
            }

        except Exception as menu_err:
            elapsed = time.time() - start_time
            logger.error(f"Error general extrayendo productos: {menu_err}")
            return {
                "category": [],
                "status": f"products_error: {menu_err}",
                "elapsed_seconds": elapsed,
            }

    def scrap_productos(self) -> List[ProductoDomotica]:
        """
        Ejecuta el proceso completo de scraping de productos (con login y logout).

        Este método:
        2. Navega a la sección de mesas
        3. Extrae SOLO los productos de todas las categorías
        4. Cierra sesión

        Returns
        -------
        List[ProductoDomotica]
            Lista de objetos ProductoDomotica extraídos
        """
        productos: List[ProductoDomotica] = []

        try:
            # 2. Navegar a mesas
            self.navigate_to_mesas()
            
            # 3. Extraer productos
            category_result = self.get_only_products()

            # 4. Convertir a objetos ProductoDomotica
            for category_item in category_result.get("category", []):
                category_name = category_item.get("category", "Sin categoría")
                products = category_item.get("products", [])

                for prod_dict in products:
                    try:
                        producto = ProductoDomotica(
                            categoria=category_name,
                            nombre=prod_dict.get("name", ""),
                            stock=prod_dict.get("stock", "0"),
                            precio=prod_dict.get("price", "0.00"),
                        )
                        productos.append(producto)
                    except Exception as e:
                        logger.error(f"Error convirtiendo producto: {e}")

            # 5. Logout
            self.logout()

            logger.info(
                f"Scraping completo de productos: {len(productos)} productos extraídos"
            )
            return productos

        except Exception as e:
            logger.error(f"Error en scrape_productos_complete: {str(e)}", exc_info=True)
            return []

    def logout(self) -> str:
        """
        Cierra sesión en la plataforma.

        Returns
        -------
        str
            Estado de la operación: "logout_success" si es exitoso, o mensaje de error.
        """
        try:
            menu_btn = WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        '//span[contains(@class, "v-btn__content")]/i[contains(@class, "mdi-menu")]',
                    )
                )
            )
            menu_btn.click()
            logger.debug("Menú hamburguesa clickeado")

            logout_btn = WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        '//div[contains(@class, "v-list-item__title") and contains(text(), "Cerrar Sesion")]',
                    )
                )
            )
            logout_btn.click()
            logger.info("Logout exitoso")
            return "logout_success"
        except Exception as logout_err:
            error_msg = f"logout_error: {logout_err}"
            logger.error(error_msg)
            return error_msg

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
