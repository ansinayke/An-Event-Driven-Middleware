import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.events.consumer import start_consumer
from app.routers.ws import router as ws_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Notification service starting...")
    consumer_task = asyncio.create_task(start_consumer())
    yield
    consumer_task.cancel()
    logger.info("Notification service shut down.")


app = FastAPI(title="SwiftTrack Notification Service", lifespan=lifespan)
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
