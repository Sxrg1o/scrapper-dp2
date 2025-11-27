import json
import logging
import asyncio
import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from src.core.config import get_settings
from src.service import domotica_service
from src.service.scheduler_service import SchedulerService
from src.model.schemas import PlatoInsertRequest

logger = logging.getLogger(__name__)
settings = get_settings()

class RabbitMQConsumer:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.scheduler = SchedulerService()

    async def connect(self):
        """Conecta al cluster y configura la cola"""
        rabbitmq_url = f"amqp://{settings.rabbitmq_user}:{settings.rabbitmq_password}@{settings.rabbitmq_host}:{settings.rabbitmq_port}/{settings.rabbitmq_vhost}"
        
        try:
            self.connection = await aio_pika.connect_robust(rabbitmq_url)
            self.channel = await self.connection.channel()
            
            # Declarar Exchange
            exchange = await self.channel.declare_exchange(
                settings.rabbitmq_exchange, 
                type="topic", 
                durable=True
            )
            
            # Declarar Cola
            queue = await self.channel.declare_queue(
                settings.rabbitmq_queue, 
                durable=True
            )
            
            # Bindings
            await queue.bind(exchange, routing_key="#") 
            
            # Iniciar consumo
            await queue.consume(self.process_message)
            logger.info("Scrapper escuchando tareas de RabbitMQ...")
        except Exception as e:
            logger.error(f"Error conectando a RabbitMQ: {e}")

    async def process_message(self, message: AbstractIncomingMessage):
        """Procesa cada mensaje recibido"""
        async with message.process():
            try:
                body = json.loads(message.body)
                task_type = body.get("task_type")
                payload = body.get("payload")
                
                logger.info(f"📥 Tarea recibida: {task_type}")
                
                # --- ROUTER DE TAREAS ---
                if task_type == "pedido_creado":
                    logger.info("👨‍🍳 Enviando pedido a cocina...")
                    try:
                        # Convertir payload a modelo Pydantic
                        plato_request = PlatoInsertRequest(**payload)
                        
                        # Ejecutar en un hilo separado para no bloquear el loop async
                        response = await asyncio.to_thread(
                            domotica_service.insertar_plato, 
                            plato_request,
                            headless=True
                        )
                        
                        if response.success:
                            logger.info(f"✅ Pedido procesado: {response.message}")
                        else:
                            logger.error(f"⚠️ Error procesando pedido: {response.message}")
                            
                    except Exception as e:
                        logger.error(f"❌ Error validando/procesando pedido: {e}")
                    
                elif task_type == "sync":
                    logger.info("🔄 Ejecutando sincronización manual...")
                    # Ejecutar en hilo separado
                    await asyncio.to_thread(self.scheduler.sync_platos)
                    await asyncio.to_thread(self.scheduler.sync_mesas)
                    logger.info("✅ Sincronización completada")
                
                else:
                    logger.warning(f"Tarea desconocida: {task_type}")

            except Exception as e:
                logger.error(f"❌ Error procesando mensaje: {e}")

    async def close(self):
        if self.connection:
            await self.connection.close()
            logger.info("🐰 Conexión RabbitMQ cerrada")