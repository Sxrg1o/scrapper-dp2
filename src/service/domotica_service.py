"""
Servicio de scraping de Domotica.

Este módulo proporciona servicios de negocio para orquestar el scraping
de datos desde la plataforma Domotica INC.
"""

import logging
import time
from typing import List
import io
import sys

from src.repository.domotica_page import DomoticaPage
from src.model.schemas import ProductoDomotica, MesaDomotica, PlatoInsertRequest, PlatoInsertResponse

# Configurar logging
logger = logging.getLogger(__name__)


class LogCapture:
    """Clase para capturar logs y errores durante el proceso"""
    
    def __init__(self):
        self.logs = []
        self.errors = []
        
    def add_log(self, message: str):
        """Agregar un log informativo"""
        self.logs.append(message)
        logger.info(message)
        
    def add_warning(self, message: str):
        """Agregar un warning (también se considera log)"""
        self.logs.append(f"WARNING: {message}")
        logger.warning(message)
        
    def add_error(self, message: str):
        """Agregar un error"""
        self.errors.append(message)
        self.logs.append(f"ERROR: {message}")
        logger.error(message)


def scrape_and_get_productos() -> List[ProductoDomotica]:
    """
    Obtiene productos mediante scraping.

    Este servicio crea una instancia del repository DomoticaPage,
    ejecuta el scraping completo de productos y cierra el driver.

    Returns
    -------
    List[ProductoDomotica]
        Lista de productos extraídos
    """
    logger.info("Servicio: Iniciando obtención de productos")

    try:
        with DomoticaPage() as domotica:
            domotica.login()
            platos = domotica.scrap_productos()
            return platos

    except Exception as e:
        logger.error(f"Servicio: Error obteniendo productos: {str(e)}", exc_info=True)
        return []


def scrape_and_get_mesas() -> List[MesaDomotica]:
    """
    Obtiene mesas mediante scraping.

    Este servicio crea una instancia del repository DomoticaPage,
    ejecuta el scraping completo de mesas y cierra el driver.

    Returns
    -------
    List[MesaDomotica]
        Lista de mesas extraídas
    """
    logger.info("Servicio: Iniciando obtención de mesas")

    try:
        # Inicializar DomoticaPage y extraer mesas
        with DomoticaPage() as domotica:
            domotica.login()
            mesas = domotica.scrap_mesas()
            logger.info(f"Se extrajeron {len(mesas)} mesas para sincronización")
            return mesas

    except Exception as e:
        logger.error(f"Servicio: Error obteniendo mesas: {str(e)}", exc_info=True)
        return []


def insertar_plato(plato_data: PlatoInsertRequest, headless: bool = True) -> PlatoInsertResponse:
    """
    Inserta platos en una mesa del sistema Domotica.
    
    Este endpoint ejecuta el proceso completo de inserción:
    1. Hace login en Domotica INC
    2. Navega a la sección de Mesas
    3. Selecciona la mesa específica usando el nombre proporcionado
    4. Inserta los platos en la mesa
    5. Llena el comprobante electrónico
    6. Hace logout
    7. Devuelve logs completos y errores acumulados
    
    Args:
        plato_data: Datos de la mesa y platos a insertar
        headless: Si True (por defecto), ejecuta sin mostrar navegador. 
                 Si False, muestra el navegador para debugging
        
    Returns:
        PlatoInsertResponse: Resultado de la operación con logs y errores
    """
    mesa_nombre = plato_data.mesa.nombre
    num_platos = len(plato_data.platos)
    
    # Crear capturador de logs
    log_capture = LogCapture()
    log_capture.add_log(f"Iniciando inserción de {num_platos} platos en mesa '{mesa_nombre}' (headless: {headless})")
    
    try:
        # Crear instancia de DomoticaPage con el modo headless especificado
        with DomoticaPage(headless=headless) as domotica:
            # Hacer login
            log_capture.add_log("Iniciando proceso de login...")
            login_success = domotica.login()
            
            if not login_success:
                log_capture.add_error("Error al hacer login en Domotica")
                return PlatoInsertResponse(
                    success=False,
                    message="Error al hacer login en Domotica",
                    logs=log_capture.logs,
                    errors=log_capture.errors
                )
            
            log_capture.add_log("Login exitoso, navegando a sección de Mesas...")
            mesas_success = domotica.navigate_to_mesas()
            
            if not mesas_success:
                log_capture.add_error("Error al navegar a la sección de Mesas")
                return PlatoInsertResponse(
                    success=False,
                    message="Error al navegar a la sección de Mesas",
                    logs=log_capture.logs,
                    errors=log_capture.errors
                )
            
            log_capture.add_log(f"Seleccionando mesa '{mesa_nombre}'...")
            mesa_select_success = domotica.select_mesa(mesa_nombre)
            
            if not mesa_select_success:
                log_capture.add_error(f"Error al seleccionar la mesa '{mesa_nombre}'")
                return PlatoInsertResponse(
                    success=False,
                    message=f"Error al seleccionar la mesa '{mesa_nombre}'",
                    logs=log_capture.logs,
                    errors=log_capture.errors
                )
            
            log_capture.add_log(f"Mesa '{mesa_nombre}' seleccionada. Iniciando inserción de {num_platos} platos...")
            # Insertar cada plato en el campo de búsqueda
            platos_insertados = 0
            for plato in plato_data.platos:
                try:
                    # Insertar el producto en el campo de búsqueda con su cantidad (stock) y comentario
                    cantidad_str = str(plato.stock) if hasattr(plato, 'stock') and plato.stock else "1"
                    comentario_str = plato.comentario if hasattr(plato, 'comentario') and plato.comentario else ""
                    insert_success = domotica.insert_product_in_search(plato.nombre, cantidad_str, comentario_str)
                    
                    if insert_success:
                        platos_insertados += 1
                        log_msg = f"Plato '{plato.nombre}' insertado exitosamente con cantidad {cantidad_str}"
                        if comentario_str:
                            log_msg += f" y comentario '{comentario_str}'"
                        log_msg += f" ({platos_insertados}/{num_platos})"
                        log_capture.add_log(log_msg)
                    else:
                        log_capture.add_warning(f"Error al insertar plato '{plato.nombre}'")
                        
                except Exception as e:
                    log_capture.add_warning(f"Excepción al insertar plato '{plato.nombre}': {str(e)}")
                
                # Pausa entre inserción de platos para estabilidad
                if platos_insertados < num_platos:
                    time.sleep(0.5)
            
            log_capture.add_log(f"Proceso de inserción de platos completado: {platos_insertados}/{num_platos} insertados")
            
            try:
                log_capture.add_log("Abriendo modal de comprobante electrónico...")
                comprobante_button_success = domotica.open_comprobante_modal()
                
                if not comprobante_button_success:
                    log_capture.add_warning("No se pudo abrir el modal de comprobante")
                    comprobante_success = False
                else:
                    log_capture.add_log("Modal de comprobante abierto, llenando datos...")
                    
                    # Solo intentar llenar el comprobante si el modal se abrió
                    comprobante_data = {
                        'tipo_documento': plato_data.comprobante.tipo_documento.value,
                        'numero_documento': plato_data.comprobante.numero_documento,
                        'nombres_completos': plato_data.comprobante.nombres_completos,
                        'direccion': plato_data.comprobante.direccion,
                        'observacion': plato_data.comprobante.observacion,
                        'tipo_comprobante': plato_data.comprobante.tipo_comprobante.value
                    }
                    
                    comprobante_success = domotica.fill_comprobante_data(comprobante_data)
                    
                    if comprobante_success:
                        log_capture.add_log("Datos del comprobante llenados exitosamente")
                    else:
                        log_capture.add_warning("No se pudieron llenar los datos del comprobante")
                        
            except AttributeError as attr_ex:
                log_capture.add_warning(f"Error de atributo en comprobante: {str(attr_ex)}")
                comprobante_success = False
            except Exception as comp_ex:
                log_capture.add_warning(f"Excepción general al manejar comprobante: {str(comp_ex)}")
                comprobante_success = False
            
            time.sleep(0.5)
            
            log_capture.add_log("Iniciando proceso de logout...")
            try:
                logout_result = domotica.logout()
                
                if logout_result == "logout_success":
                    log_capture.add_log("Logout completado exitosamente")
                else:
                    log_capture.add_warning(f"Problema durante el logout: {logout_result}")
            except Exception as logout_ex:
                log_capture.add_warning(f"Excepción durante el logout: {str(logout_ex)}")
                logout_result = "logout_exception"
            
            # Determinar el mensaje final y si hubo errores
            comprobante_msg = "Comprobante llenado exitosamente" if comprobante_success else "Error al llenar comprobante"
            logout_msg = "Logout exitoso" if logout_result == "logout_success" else "Error en logout"
            
            log_capture.add_log(f"Proceso completado - {platos_insertados}/{num_platos} platos insertados")
            
            # Si hay errores, retornar como fallo
            if log_capture.errors:
                return PlatoInsertResponse(
                    success=False,
                    message=f"Proceso completado con errores - {platos_insertados}/{num_platos} platos insertados en mesa '{mesa_nombre}' - {comprobante_msg} - {logout_msg}",
                    mesa_nombre=mesa_nombre,
                    platos_insertados=platos_insertados,
                    logs=log_capture.logs,
                    errors=log_capture.errors
                )
            
            return PlatoInsertResponse(
                success=True,
                message=f"Proceso completado exitosamente - {platos_insertados}/{num_platos} platos insertados en mesa '{mesa_nombre}' - {comprobante_msg} - {logout_msg}",
                mesa_nombre=mesa_nombre,
                platos_insertados=platos_insertados,
                logs=log_capture.logs,
                errors=log_capture.errors
            )
            
    except Exception as e:
        error_msg = f"Error crítico durante la inserción: {str(e)}"
        logger.error(error_msg)
        return PlatoInsertResponse(
            success=False,
            message=error_msg,
            logs=[f"Iniciando inserción de {num_platos} platos en mesa '{mesa_nombre}'", f"ERROR: {error_msg}"],
            errors=[error_msg]
        )
