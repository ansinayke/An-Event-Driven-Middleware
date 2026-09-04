import asyncio
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    logger.info(f"WMS Mock accepted connection from {addr}")
    
    try:
        data = await reader.read(4096)
        message = data.decode()
        logger.info(f"WMS Mock received: {message}")
        
        try:
            payload = json.loads(message)
            action = payload.get("action")
            order_id = payload.get("order_id", "unknown")
            
            if action == "register":
                response = {"status": "success", "warehouse_ref": f"WH-REF-{order_id}"}
                logger.info(f"WMS Mock simulating registration for {order_id}")
            elif action == "compensate":
                response = {"status": "success", "message": f"Rolled back {order_id}"}
                logger.info(f"WMS Mock simulating rollback for {order_id}")
            else:
                response = {"status": "error", "message": "Unknown action"}
                
        except json.JSONDecodeError:
            response = {"status": "error", "message": "Invalid JSON"}
            
        logger.info(f"WMS Mock sending: {response}")
        writer.write(json.dumps(response).encode())
        await writer.drain()
        
    except Exception as e:
        logger.error(f"Error handling connection: {e}")
    finally:
        logger.info("WMS Mock closing connection")
        writer.close()
        await writer.wait_closed()

async def main():
    server = await asyncio.start_server(handle_client, '0.0.0.0', 9000)
    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    logger.info(f"WMS Mock Server serving on {addrs}")

    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())
