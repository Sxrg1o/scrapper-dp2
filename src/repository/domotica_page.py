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

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None, headless: Optional[bool] = None):
        """
        Inicializa la clase DomoticaPage con credenciales y configura el driver.

        Parameters
        ----------
        username : str, opcional
            Nombre de usuario para iniciar sesión. Si no se proporciona, se usa el de la configuración.
        password : str, opcional
            Contraseña para iniciar sesión. Si no se proporciona, se usa la de la configuración.
        headless : bool, opcional
            Si es True, ejecuta en modo headless. Si es False, muestra el navegador. 
            Si es None, usa la configuración del debug.

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

        # Determinar si usar headless
        use_headless = headless if headless is not None else (not settings.debug)
        
        logger.info(f"Configurando Chrome - headless parameter: {headless}, use_headless: {use_headless}")
        
        # Opciones recomendadas para scraping
        if use_headless:
            chrome_options.add_argument("--headless")
            logger.info("Chrome configurado en modo headless")
        else:
            logger.info("Chrome configurado en modo visible (sin headless)")

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

    def select_mesa(self, mesa_nombre: str) -> bool:
        """
        Selecciona una mesa específica de la lista de mesas para acceder a sus platos.
        
        Args:
            mesa_nombre: Nombre de la mesa a seleccionar (ej: "J5", "P1", "1", etc.)
            
        Returns:
            bool: True si la mesa fue seleccionada exitosamente, False en caso contrario
        """
        try:
            logger.info(f"Buscando mesa '{mesa_nombre}' en la lista de mesas")
            
            # Método 1: Usar el selector específico basado en el HTML proporcionado
            # Buscar dentro del h2 que contiene el nombre de la mesa
            try:
                mesa_element = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"//div[contains(@class, 'v-card') and contains(@class, 'v-card--link') and contains(@class, 'v-sheet') and contains(@class, 'theme--light') and contains(@class, 'elevation-5')]//h2[contains(@class, 'black--text') and normalize-space(text())='{mesa_nombre}']/..")
                    )
                )
                logger.debug(f"Mesa '{mesa_nombre}' encontrada por selector específico de h2")
            except TimeoutException:
                # Método 2: Buscar directamente el div que contiene el h2 con el texto de la mesa
                try:
                    mesa_element = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, f"//div[contains(@class, 'v-card') and contains(@class, 'v-card--link')]//h2[text()='{mesa_nombre}']/ancestor::div[contains(@class, 'v-card')]")
                        )
                    )
                    logger.debug(f"Mesa '{mesa_nombre}' encontrada por selector de ancestro")
                except TimeoutException:
                    # Método 3: Buscar usando el texto directamente en el h2
                    try:
                        mesa_element = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable(
                                (By.XPATH, f"//h2[contains(@class, 'black--text') and text()='{mesa_nombre}']")
                            )
                        )
                        logger.debug(f"Mesa '{mesa_nombre}' encontrada por h2 directo")
                    except TimeoutException:
                        # Método 4: Buscar el card completo que contiene el texto de la mesa
                        mesa_element = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable(
                                (By.XPATH, f"//div[contains(@class, 'v-card--link') and .//h2[text()='{mesa_nombre}']]")
                            )
                        )
                        logger.debug(f"Mesa '{mesa_nombre}' encontrada por card que contiene h2")
            
            logger.info(f"Mesa '{mesa_nombre}' encontrada, haciendo clic...")
            mesa_element.click()
            
            # Esperar a que cargue la interfaz de la mesa (pueden ser categorías de productos)
            WebDriverWait(self.driver, self.timeout).until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'v-toolbar__title')]")),
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'v-card v-card--link')]")),
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'hoverable')]"))
                )
            )
            
            logger.info(f"Mesa '{mesa_nombre}' seleccionada exitosamente")
            return True
            
        except TimeoutException as e:
            logger.error(f"Timeout al seleccionar mesa '{mesa_nombre}': {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error al seleccionar mesa '{mesa_nombre}': {str(e)}")
            return False

    def insert_product_in_search(self, product_name: str) -> bool:
        """
        Inserta un nombre de producto en el campo de búsqueda de productos.
        
        Args:
            product_name: Nombre del producto a buscar e insertar
            
        Returns:
            bool: True si el producto fue insertado exitosamente, False en caso contrario
        """
        try:
            # Buscar campo de búsqueda
            search_input = None
            
            # Método 1: Por label "Buscar Productos"
            try:
                search_input = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//label[contains(text(), 'Buscar Productos')]/..//input[@type='text']")
                    )
                )
            except TimeoutException:
                # Método 2: Por v-select__slot
                try:
                    search_input = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, "//div[contains(@class, 'v-select__slot')]//input[@type='text' and @autocomplete='off']")
                        )
                    )
                except TimeoutException:
                    # Método 3: Por autofocus
                    search_input = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, "//input[@autofocus and @type='text']")
                        )
                    )
            
            # Llenar campo de búsqueda
            time.sleep(1)
            search_input.clear()
            time.sleep(0.5)
            search_input.send_keys(product_name)
            time.sleep(1)
            
            # Buscar y hacer clic en el primer resultado
            result_clicked = False
            
            for search_retry in range(3):
                try:
                    # Esperar menú de resultados
                    menu_content = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//div[contains(@class, 'v-menu__content') and contains(@class, 'menuable__content__active')]")
                        )
                    )
                    
                    # Hacer clic en primer resultado
                    first_result = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, "//div[contains(@class, 'v-menu__content') and contains(@class, 'menuable__content__active')]//div[@role='option' and contains(@class, 'v-list-item')][1]")
                        )
                    )
                    
                    time.sleep(0.5)
                    first_result.click()
                    result_clicked = True
                    break
                    
                except TimeoutException:
                    if search_retry < 2:
                        time.sleep(1)
                        try:
                            search_input.clear()
                            time.sleep(0.5)
                            search_input.send_keys(product_name)
                            time.sleep(1)
                        except Exception:
                            pass
                except Exception:
                    if search_retry < 2:
                        time.sleep(1)
            
            # Fallback: presionar Enter si no se pudo hacer clic
            if not result_clicked:
                try:
                    search_input.send_keys(Keys.RETURN)
                    time.sleep(1)
                except Exception:
                    pass
            
            # Cerrar popup si aparece
            try:
                # Esperar popup
                WebDriverWait(self.driver, 5).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'v-dialog') and contains(@class, 'v-dialog--active')]")),
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'v-overlay--active')]")),
                        EC.presence_of_element_located((By.XPATH, "//button[contains(@class, 'mdi-close')]"))
                    )
                )
                
                # Buscar botón OK
                ok_button = None
                ok_clicked = False
                
                try:
                    ok_button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, "//button[.//span[contains(@class, 'v-btn__content') and text()='OK']]")
                        )
                    )
                except TimeoutException:
                    try:
                        ok_button = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable(
                                (By.XPATH, "//span[contains(@class, 'v-btn__content') and text()='OK']")
                            )
                        )
                    except TimeoutException:
                        try:
                            ok_button = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable(
                                    (By.XPATH, "//*[contains(text(), 'OK') and (contains(@class, 'v-btn') or self::button)]")
                                )
                            )
                        except TimeoutException:
                            pass
                
                # Hacer clic en OK
                if ok_button:
                    for retry in range(3):
                        if ok_clicked:
                            break
                            
                        time.sleep(1)
                        
                        try:
                            ok_button.click()
                            ok_clicked = True
                            break
                        except Exception:
                            try:
                                time.sleep(0.5)
                                self.driver.execute_script("arguments[0].click();", ok_button)
                                ok_clicked = True
                                break
                            except Exception:
                                try:
                                    time.sleep(0.5)
                                    ok_button.send_keys(Keys.RETURN)
                                    ok_clicked = True
                                    break
                                except Exception:
                                    pass
                        
                        if not ok_clicked and retry < 2:
                            time.sleep(1)
                
                # Fallback: ESC si OK falla
                if not ok_clicked:
                    for esc_retry in range(2):
                        try:
                            time.sleep(1)
                            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                            break
                        except Exception:
                            pass
                
                time.sleep(0.5)
                
            except TimeoutException:
                pass
            except Exception:
                pass
            
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Error insertando producto '{product_name}': {str(e)}")
            return False

    def open_comprobante_modal(self) -> bool:
        """
        Hace clic en el botón mdi-account-plus para abrir el modal de comprobante electrónico.
        
        Este método debe llamarse después de insertar todos los platos para abrir 
        el modal donde se llenarán los datos del comprobante.
        
        Returns:
            bool: True si el modal se abrió exitosamente, False en caso contrario
        """
        try:
            
            # Buscar el botón con el ícono mdi-account-plus
            # Basado en el HTML: <button data-v-0e3622d2="" type="button" class="v-icon notranslate v-icon--link mdi mdi-account-plus theme--light black--text" style="font-size: 36px;"></button>
            comprobante_button = None
            
            # Método 1: Buscar directamente por las clases del botón
            try:
                comprobante_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(@class, 'mdi-account-plus') and contains(@class, 'v-icon')]")
                    )
                )
                logger.debug("Botón de comprobante encontrado por clases")
            except TimeoutException:
                # Método 2: Buscar solo por el ícono mdi-account-plus
                try:
                    comprobante_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, "//button[contains(@class, 'mdi-account-plus')]")
                        )
                    )
                    logger.debug("Botón de comprobante encontrado por ícono")
                except TimeoutException:
                    # Método 3: Buscar cualquier elemento con mdi-account-plus
                    comprobante_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, "//*[contains(@class, 'mdi-account-plus')]")
                        )
                    )
                    logger.debug("Botón de comprobante encontrado por elemento genérico")
            
            # Hacer clic en el botón con múltiples métodos y retries
            logger.info("Haciendo clic en botón para abrir modal de comprobante...")
            button_clicked = False
            
            # Retry loop: hasta 3 intentos con sleeps
            for retry in range(3):
                if button_clicked:
                    break
                    
                logger.info(f"Intento {retry + 1}/3 de hacer clic en botón comprobante")
                time.sleep(1)  # Pausa antes de cada intento
                
                # Método 1: Clic normal
                try:
                    comprobante_button.click()
                    button_clicked = True
                    logger.info("Botón de comprobante clickeado exitosamente (clic normal)")
                    break
                except Exception as click_error:
                    logger.warning(f"Clic normal falló (intento {retry + 1}): {click_error}")
                    
                    # Método 2: JavaScript click
                    try:
                        time.sleep(0.5)
                        self.driver.execute_script("arguments[0].click();", comprobante_button)
                        button_clicked = True
                        logger.info("Botón de comprobante clickeado exitosamente (JavaScript)")
                        break
                    except Exception as js_error:
                        logger.warning(f"JavaScript click falló (intento {retry + 1}): {js_error}")
                        
                        # Método 3: Enviar Enter
                        try:
                            time.sleep(0.5)
                            comprobante_button.send_keys(Keys.RETURN)
                            button_clicked = True
                            logger.info("Botón de comprobante activado exitosamente (Enter)")
                            break
                        except Exception as enter_error:
                            logger.warning(f"Enter falló (intento {retry + 1}): {enter_error}")
                
                # Pausa entre retries si no fue exitoso
                if not button_clicked and retry < 2:
                    logger.info(f"Esperando 1 segundo antes del siguiente intento...")
                    time.sleep(1)
            
            if not button_clicked:
                logger.error("No se pudo hacer clic en el botón de comprobante")
                return False
            
            # Verificar que el modal se haya abierto con retry
            logger.info("Verificando que el modal de comprobante se haya abierto...")
            modal_opened = False
            
            # Dar tiempo extra para que aparezca el modal
            time.sleep(0.5)
            
            for verify_retry in range(3):
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//h4[contains(text(), 'Datos para Comprobante Electronico')]")
                        )
                    )
                    modal_opened = True
                    logger.info("Modal de comprobante abierto exitosamente")
                    break
                except TimeoutException:
                    logger.warning(f"Modal no detectado (intento {verify_retry + 1}/3)")
                    if verify_retry < 2:
                        time.sleep(2)  # Esperar más tiempo entre intentos
                        
            if not modal_opened:
                logger.error("Modal de comprobante no se abrió después de múltiples intentos")
                return False
            
            return True
            
        except TimeoutException as e:
            logger.error(f"Timeout al abrir modal de comprobante: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error al abrir modal de comprobante: {str(e)}")
            return False

    def fill_comprobante_data(self, comprobante_data: dict) -> bool:
        """
        Llena los datos del comprobante electrónico en el modal
        
        Args:
            comprobante_data: Diccionario con los datos del comprobante
                
        Returns:
            bool: True si se llenan los datos correctamente, False en caso contrario
        """
        try:
            logger.info("✅ Verificando modal de comprobante...")
            
            # Verificar que el modal está presente
            modal = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h4[contains(text(), 'Datos para Comprobante Electronico')]")
                )
            )
            
            # 1. LLENAR TIPO DE DOCUMENTO (solo si no es DNI por defecto)
            tipo_documento = comprobante_data.get('tipo_documento', 'DNI')
            if tipo_documento != 'DNI':
                try:
                    # Buscar el dropdown de tipo documento en el modal y hacer clic
                    tipo_doc_dropdown = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'v-dialog')]//div[contains(@class, 'v-select__slot')]"))
                    )
                    self.driver.execute_script("arguments[0].click();", tipo_doc_dropdown)
                    time.sleep(1.5)
                    
                    # Seleccionar el tipo de documento correcto
                    option_xpath = f"//div[contains(@class, 'v-list-item__title') and text()='{tipo_documento}']"
                    option = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, option_xpath))
                    )
                    self.driver.execute_script("arguments[0].click();", option)
                    time.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error al seleccionar tipo documento: {str(e)}")
            
            # 2. LLENAR NÚMERO DE DOCUMENTO
            numero_documento = str(comprobante_data.get('numero_documento', ''))
            if numero_documento:
                try:
                    time.sleep(1)
                    
                    # Buscar inputs con autofocus y type="number" en el modal
                    numero_inputs = self.driver.find_elements(By.XPATH, "//div[@class='v-dialog v-dialog--active']//input[@autofocus and @type='number']")
                    
                    if not numero_inputs:
                        numero_inputs = self.driver.find_elements(By.XPATH, "//div[@class='v-dialog v-dialog--active']//input[@type='number']")
                    
                    if numero_inputs:
                        numero_input = numero_inputs[0]
                        
                        # Hacer scroll, focus y llenar
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", numero_input)
                        self.driver.execute_script("arguments[0].focus();", numero_input)
                        numero_input.click()
                        time.sleep(0.3)
                        
                        numero_input.clear()
                        self.driver.execute_script("arguments[0].value = '';", numero_input)
                        time.sleep(0.2)
                        numero_input.send_keys(numero_documento)
                        time.sleep(0.3)
                        
                        # Verificar
                        valor_actual = numero_input.get_attribute('value')
                        if valor_actual != numero_documento:
                            # Intentar con JavaScript
                            self.driver.execute_script(f"arguments[0].value = '{numero_documento}';", numero_input)
                            self.driver.execute_script("arguments[0].dispatchEvent(new Event('input'));", numero_input)
                            
                    else:
                        logger.warning("⚠️ Campo número no encontrado")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error al llenar número: {str(e)}")
            
            # 3-5. LLENAR CAMPOS DE TEXTO EN ORDEN CORRECTO
            try:
                # Obtener solo los campos de texto VISIBLES (excluir hidden y readonly)
                text_inputs = self.driver.find_elements(By.XPATH, 
                    "//div[@class='v-dialog v-dialog--active']//input[@type='text' and not(@readonly) and not(@hidden)]")
                
                # Si no encontramos suficientes, buscar por labels específicos
                if len(text_inputs) < 3:
                    nombres_input = None
                    direccion_input = None 
                    observacion_input = None
                    
                    try:
                        nombres_input = self.driver.find_element(By.XPATH, "//label[text()='Nombres Completos']/..//input[@type='text']")
                    except: pass
                    
                    try:
                        direccion_input = self.driver.find_element(By.XPATH, "//label[text()='Direccion']/..//input[@type='text']")
                    except: pass
                    
                    try:
                        observacion_input = self.driver.find_element(By.XPATH, "//label[text()='Observacion']/..//input[@type='text']")
                    except: pass
                    
                    # Crear lista con los campos encontrados
                    text_inputs = [inp for inp in [nombres_input, direccion_input, observacion_input] if inp is not None]
                
                # Mapeo de campos
                campos_data = [
                    ('nombres_completos', 0),
                    ('direccion', 1), 
                    ('observacion', 2)
                ]
                
                for campo_key, indice in campos_data:
                    valor = comprobante_data.get(campo_key, '')
                    if valor and len(text_inputs) > indice:
                        try:
                            campo_input = text_inputs[indice]
                            
                            # Hacer scroll y dar focus
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", campo_input)
                            self.driver.execute_script("arguments[0].focus();", campo_input)
                            self.driver.execute_script("arguments[0].click();", campo_input)
                            time.sleep(0.3)
                            
                            # Limpiar y llenar
                            self.driver.execute_script("arguments[0].value = '';", campo_input)
                            campo_input.clear()
                            time.sleep(0.2)
                            campo_input.send_keys(valor)
                            time.sleep(0.3)
                            
                        except Exception as e:
                            logger.warning(f"⚠️ Error al llenar {campo_key}: {str(e)}")
                        
            except Exception as e:
                logger.error(f"❌ Error obteniendo campos de texto: {str(e)}")
            
            # 6. SELECCIONAR TIPO DE COMPROBANTE
            tipo_comprobante = comprobante_data.get('tipo_comprobante', 'T')
            if tipo_comprobante:
                
                # Determinar el código correcto (T, B, F)
                if tipo_comprobante in ['Nota', 'Boleta', 'Factura']:
                    texto_to_value = {'Nota': 'T', 'Boleta': 'B', 'Factura': 'F'}
                    codigo_value = texto_to_value[tipo_comprobante]
                else:
                    codigo_value = tipo_comprobante
                    
                try:
                    time.sleep(1)
                    radio_seleccionado = False
                    
                    # Método principal: Por texto del label
                    try:
                        if tipo_comprobante in ['Nota', 'Boleta', 'Factura']:
                            texto_label = tipo_comprobante
                        else:
                            value_to_texto = {'T': 'Nota', 'B': 'Boleta', 'F': 'Factura'}
                            texto_label = value_to_texto.get(tipo_comprobante, 'Nota')
                            
                        radio_label = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, f"//div[@role='radiogroup']//label[text()='{texto_label}']"))
                        )
                        self.driver.execute_script("arguments[0].click();", radio_label)
                        radio_seleccionado = True
                    except Exception as e:
                        logger.warning(f"⚠️ Error al seleccionar tipo comprobante: {str(e)}")
                    
                    # Método de respaldo: JavaScript
                    if not radio_seleccionado:
                        try:
                            js_script = f"""
                            const radioGroup = document.querySelector('[role="radiogroup"]');
                            if (radioGroup) {{
                                const radio = radioGroup.querySelector('input[type="radio"][value="{codigo_value}"]');
                                if (radio) {{
                                    radio.checked = true;
                                    radio.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    return true;
                                }}
                            }}
                            return false;
                            """
                            result = self.driver.execute_script(js_script)
                            if result:
                                radio_seleccionado = True
                        except Exception as e_js:
                            logger.warning(f"⚠️ JavaScript falló: {str(e_js)}")
                    
                    if not radio_seleccionado:
                        logger.warning(f"⚠️ No se pudo seleccionar tipo comprobante")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error general al seleccionar tipo comprobante: {str(e)}")
            
            # 7. HACER CLIC EN GUARDAR (COMENTADO POR AHORA)
            # NOTA: Por ahora no queremos que guarde, solo llenar los datos para emular
            # try:
            #     guardar_button = WebDriverWait(self.driver, 5).until(
            #         EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'v-btn') and .//span[text()='Guardar']]"))
            #     )
            #     self.driver.execute_script("arguments[0].click();", guardar_button)
            #     time.sleep(3)
            # except Exception as e:
            #     logger.warning(f"⚠️ Error al hacer clic en Guardar: {str(e)}")
            
            # 8. EN SU LUGAR, HACER CLIC EN EL BOTÓN DE CERRAR (X) CON JAVASCRIPT
            try:
                logger.info("💾 Datos llenados, cerrando modal con JavaScript...")
                time.sleep(2)  # Pausa para que se vean los datos llenados
                
                # Script JavaScript para cerrar modal y overlays
                close_script = """
                // Función para cerrar modal del comprobante
                function closeComprobanteModal() {
                    // Método 1: Buscar y hacer clic en el botón X del modal
                    const closeButton = document.querySelector('.v-system-bar.theme--dark button.mdi-close');
                    if (closeButton && closeButton.offsetParent !== null) {
                        closeButton.click();
                        console.log('Modal cerrado con botón X');
                        return true;
                    }
                    
                    // Método 2: Cerrar cualquier dialog activo
                    const dialogs = document.querySelectorAll('.v-dialog--active');
                    dialogs.forEach(dialog => {
                        dialog.style.display = 'none';
                        dialog.classList.remove('v-dialog--active');
                    });
                    if (dialogs.length > 0) {
                        console.log('Dialogs cerrados manualmente');
                    }
                    
                    // Método 3: Remover overlays activos
                    const overlays = document.querySelectorAll('.v-overlay--active');
                    overlays.forEach(overlay => {
                        overlay.style.display = 'none';
                        overlay.classList.remove('v-overlay--active');
                    });
                    if (overlays.length > 0) {
                        console.log('Overlays removidos');
                    }
                    
                    // Método 4: Enviar evento ESC
                    const escEvent = new KeyboardEvent('keydown', {
                        key: 'Escape',
                        keyCode: 27,
                        which: 27,
                        bubbles: true
                    });
                    document.dispatchEvent(escEvent);
                    console.log('Evento ESC enviado');
                    
                    return true;
                }
                
                // Ejecutar cierre
                return closeComprobanteModal();
                """
                
                # Ejecutar el script JavaScript
                result = self.driver.execute_script(close_script)
                logger.info(f"Script ejecutado, resultado: {result}")
                
                # Dar tiempo para que se procese el cierre
                time.sleep(3)
                
                # Verificar que el modal se cerró
                modal_closed = False
                try:
                    modals = self.driver.find_elements(
                        By.XPATH, 
                        "//h4[contains(text(), 'Datos para Comprobante Electronico')]"
                    )
                    overlays = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'v-overlay--active')]")
                    
                    if not modals and not overlays:
                        modal_closed = True
                        logger.info("✅ Modal cerrado exitosamente con JavaScript")
                    else:
                        logger.warning(f"⚠️ Modal aún presente: {len(modals)} modals, {len(overlays)} overlays")
                        
                        # Script adicional para forzar limpieza
                        cleanup_script = """
                        // Limpieza forzada
                        const allDialogs = document.querySelectorAll('.v-dialog');
                        const allOverlays = document.querySelectorAll('.v-overlay');
                        
                        allDialogs.forEach(d => {
                            d.style.display = 'none';
                            d.remove();
                        });
                        
                        allOverlays.forEach(o => {
                            o.style.display = 'none';
                            o.remove();
                        });
                        
                        // Limpiar clases del body
                        document.body.classList.remove('v-overlay-scroll-blocked');
                        
                        return 'cleaned';
                        """
                        
                        cleanup_result = self.driver.execute_script(cleanup_script)
                        logger.info(f"Limpieza forzada ejecutada: {cleanup_result}")
                        modal_closed = True
                        
                except Exception as verify_err:
                    logger.warning(f"Error verificando cierre: {verify_err}")
                    modal_closed = True  # Asumir que se cerró
                
            except Exception as e:
                logger.warning(f"⚠️ Error con JavaScript: {str(e)}")
                # Fallback: ESC con Selenium
                try:
                    logger.info("Fallback: usando ESC con Selenium...")
                    for _ in range(5):
                        self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        time.sleep(1)
                    logger.info("✅ Fallback ESC ejecutado")
                except Exception as esc_err:
                    logger.warning(f"⚠️ Error con fallback ESC: {str(esc_err)}")
            
            # Pausa final para estabilizar la UI
            time.sleep(2)
            
            return True
            
        except TimeoutException as e:
            logger.error(f"❌ Timeout: Modal de comprobante no encontrado: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Error llenando datos del comprobante: {str(e)}")
            return False

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
            logger.info("Iniciando proceso de logout...")
            
            # PASO 1: Cerrar todos los overlays y modales que puedan estar abiertos
            overlay_closed = False
            for attempt in range(3):  # Hasta 3 intentos para cerrar overlays
                try:
                    # Verificar si hay overlays activos
                    overlays = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'v-overlay--active')]")
                    if not overlays:
                        logger.debug("No hay overlays activos")
                        overlay_closed = True
                        break
                        
                    logger.info(f"Overlay detectado (intento {attempt + 1}/3), intentando cerrarlo...")
                    
                    # Método 1: Buscar botón X/close en cualquier modal
                    close_buttons = self.driver.find_elements(By.XPATH, 
                        "//button[contains(@class, 'mdi-close')] | //i[contains(@class, 'mdi-close')] | //*[contains(@class, 'close')]")
                    
                    if close_buttons:
                        try:
                            close_buttons[0].click()
                            logger.debug("Botón de cerrar clickeado")
                            time.sleep(1)
                            continue
                        except Exception as close_err:
                            logger.warning(f"Error al hacer clic en botón cerrar: {close_err}")
                    
                    # Método 2: Presionar ESC múltiples veces
                    logger.debug("Presionando ESC para cerrar modales...")
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    for _ in range(3):
                        body.send_keys(Keys.ESCAPE)
                        time.sleep(0.5)
                    
                    # Método 3: Hacer clic fuera del modal (en el overlay)
                    try:
                        overlay_scrim = self.driver.find_element(By.XPATH, "//div[contains(@class, 'v-overlay__scrim')]")
                        self.driver.execute_script("arguments[0].click();", overlay_scrim)
                        logger.debug("Clic en overlay scrim")
                        time.sleep(1)
                    except Exception as scrim_err:
                        logger.warning(f"Error al hacer clic en overlay: {scrim_err}")
                    
                except Exception as overlay_err:
                    logger.warning(f"Error al cerrar overlay (intento {attempt + 1}): {overlay_err}")
                
                time.sleep(1)  # Esperar entre intentos
            
            # PASO 2: Esperar a que la interfaz se estabilice
            if not overlay_closed:
                logger.warning("No se pudieron cerrar todos los overlays, intentando logout de todos modos...")
            
            # Esperar a que no haya overlays activos o timeout después de 10 segundos (aumentado)
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda d: len(d.find_elements(By.XPATH, "//div[contains(@class, 'v-overlay--active')]")) == 0
                )
                logger.debug("Interfaz estabilizada sin overlays")
            except TimeoutException:
                logger.warning("Timeout esperando que se cierren los overlays, continuando...")
                # Último intento: hacer clic en el fondo para cerrar cualquier modal
                try:
                    self.driver.execute_script("document.body.click();")
                    time.sleep(2)
                except Exception:
                    pass
            
            # Ahora intentar hacer clic en el menú hamburguesa
            logger.debug("Buscando menú hamburguesa...")
            
            # Método 1: Buscar por el ícono mdi-menu
            try:
                menu_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//i[contains(@class, "mdi-menu")]')
                    )
                )
                menu_btn.click()
                logger.debug("Menú hamburguesa clickeado (método 1)")
            except TimeoutException:
                # Método 2: Usar JavaScript para hacer clic
                try:
                    menu_btn = self.driver.find_element(
                        By.XPATH, '//i[contains(@class, "mdi-menu")]'
                    )
                    self.driver.execute_script("arguments[0].click();", menu_btn)
                    logger.debug("Menú hamburguesa clickeado con JavaScript (método 2)")
                except Exception as js_err:
                    # Método 3: Buscar por el span padre
                    menu_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, '//span[contains(@class, "v-btn__content")]/i[contains(@class, "mdi-menu")]/..')
                        )
                    )
                    menu_btn.click()
                    logger.debug("Menú hamburguesa clickeado (método 3)")

            # Esperar a que aparezca el menú desplegable y hacer clic en "Cerrar Sesion"
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
