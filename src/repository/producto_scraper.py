"""
Scrapers para extraer datos de productos del sistema Domotica INC.

Este módulo contiene las clases y funciones específicas para extraer
información de productos mediante web scraping.
"""

import logging
import re
from typing import List, Optional
from bs4 import Tag

from src.model.schemas import ProductoDomotica
from src.repository.http_client import scraping_client

# Configurar logger para este módulo
logger = logging.getLogger(__name__)


class ProductoScraper:
    """
    Extractor de datos de productos mediante web scraping.
    
    Esta clase se encarga de navegar por el sistema Domotica INC,
    localizar los elementos HTML correspondientes a productos y
    extraer la información estructurada.
    """
    
    def __init__(self):
        """Inicializa el scraper de productos."""
        # Rutas de navegación
        self.productos_path = "/productos"
        self.categorias_path = "/productos/categorias"
    
    async def get_categorias(self) -> List[str]:
        """
        Obtiene la lista de categorías de productos disponibles.
        
        Returns:
            List[str]: Lista de nombres de categorías
            
        Raises:
            Exception: Si ocurre un error al extraer las categorías
        """
        try:
            html, _ = await scraping_client.get_page(self.categorias_path)
            soup = await scraping_client.parse_html(html)
            
            # Buscar los elementos HTML que contienen las categorías
            # (Ajustar estos selectores según la estructura real del sitio)
            categoria_elements = soup.select('ul.categorias li a') or soup.select('.categoria-item')
            
            if not categoria_elements:
                logger.warning("No se encontraron categorías en la página")
                return []
            
            # Extraer nombres de categorías
            categorias = [
                categoria.get_text().strip()
                for categoria in categoria_elements
                if categoria and categoria.get_text().strip()
            ]
            
            logger.info(f"Categorías extraídas: {len(categorias)}")
            return categorias
            
        except Exception as e:
            logger.error(f"Error al obtener categorías: {str(e)}")
            raise Exception(f"Error al obtener categorías de productos: {str(e)}")
    
    async def get_productos_por_categoria(self, categoria: str) -> List[ProductoDomotica]:
        """
        Obtiene la lista de productos para una categoría específica.
        
        Args:
            categoria: Nombre de la categoría a buscar
            
        Returns:
            List[ProductoDomotica]: Lista de productos de la categoría
            
        Raises:
            Exception: Si ocurre un error al extraer los productos
        """
        try:
            # Construir URL de productos filtrados por categoría
            # (Ajustar según cómo funcione el sitio real)
            path = f"{self.productos_path}?categoria={categoria}"
            html, _ = await scraping_client.get_page(path)
            soup = await scraping_client.parse_html(html)
            
            # Buscar los elementos que representan los productos
            # (Ajustar estos selectores según la estructura real del sitio)
            producto_elements = soup.select('.producto-item') or soup.select('table.productos tr')
            
            if not producto_elements:
                logger.warning(f"No se encontraron productos para la categoría '{categoria}'")
                return []

            productos: List[ProductoDomotica] = []

            for elemento in producto_elements:
                # Intentar extraer los datos del producto
                # (Ajustar según la estructura real del HTML)
                try:
                    producto = await self._extraer_datos_producto(elemento, categoria)
                    if producto:
                        productos.append(producto)
                except Exception as e:
                    logger.error(f"Error extrayendo datos de un producto: {str(e)}")
                    continue
            
            logger.info(f"Productos extraídos de la categoría '{categoria}': {len(productos)}")
            return productos
            
        except Exception as e:
            logger.error(f"Error al obtener productos de categoría '{categoria}': {str(e)}")
            raise Exception(f"Error al obtener productos de la categoría '{categoria}': {str(e)}")
    
    async def get_todos_productos(self) -> List[ProductoDomotica]:
        """
        Obtiene todos los productos disponibles en el sistema.
        
        Returns:
            List[ProductoDomotica]: Lista de todos los productos
            
        Raises:
            Exception: Si ocurre un error al extraer los productos
        """
        try:
            # 1. Obtener todas las categorías
            categorias = await self.get_categorias()
            
            # 2. Para cada categoría, obtener sus productos
            todos_productos: List[ProductoDomotica] = []
            for categoria in categorias:
                productos_categoria = await self.get_productos_por_categoria(categoria)
                todos_productos.extend(productos_categoria)
            
            logger.info(f"Total de productos extraídos: {len(todos_productos)}")
            return todos_productos
            
        except Exception as e:
            logger.error(f"Error al obtener todos los productos: {str(e)}")
            raise Exception(f"Error al obtener todos los productos: {str(e)}")
    
    async def _extraer_datos_producto(self, elemento: Tag, categoria: str) -> Optional[ProductoDomotica]:
        """
        Extrae los datos de un producto desde su elemento HTML.
        
        Args:
            elemento: Elemento HTML que contiene los datos del producto
            categoria: Categoría a la que pertenece el producto
            
        Returns:
            Optional[ProductoDomotica]: Datos del producto o None si no se pudo extraer
        """
        try:
            # Extraer nombre del producto
            # (Ajustar estos selectores según la estructura real del sitio)
            nombre_element = elemento.select_one('.nombre-producto') or elemento.select_one('td.nombre')
            nombre = nombre_element.get_text().strip() if nombre_element else None
            
            if not nombre:
                logger.warning("No se encontró el nombre del producto, omitiendo")
                return None
            
            # Extraer stock
            # (Ajustar estos selectores según la estructura real del sitio)
            stock_element = elemento.select_one('.stock') or elemento.select_one('td.stock')
            stock_text = stock_element.get_text().strip() if stock_element else "0"
            
            # Intentar extraer el número del texto (podría ser "10 unidades" o similar)
            stock_match = re.search(r'\d+', stock_text)
            stock = int(stock_match.group(0)) if stock_match else 0
            
            # Extraer precio
            # (Ajustar estos selectores según la estructura real del sitio)
            precio_element = elemento.select_one('.precio') or elemento.select_one('td.precio')
            precio_text = precio_element.get_text().strip() if precio_element else "0"
            
            # Limpiar e intentar extraer el número (podría ser "$25.50" o similar)
            precio_text = precio_text.replace('$', '').replace(',', '.').strip()
            precio_match = re.search(r'\d+(\.\d+)?', precio_text)
            precio = float(precio_match.group(0)) if precio_match else 0.0
            
            # Crear instancia del producto
            return ProductoDomotica(
                categoria=categoria,
                nombre=nombre,
                stock=stock,
                precio=precio
            )
            
        except Exception as e:
            logger.error(f"Error al extraer datos de producto: {str(e)}")
            return None


# Instancia global del scraper de productos
producto_scraper = ProductoScraper()