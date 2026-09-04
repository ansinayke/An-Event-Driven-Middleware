import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import init_db
from app.routers.orders import router as orders_router
from app.events.consumer import start_consumer
from app.events.publisher import close_publisher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Order service starting...")
    await init_db()
    consumer_task = asyncio.create_task(start_consumer())
    yield
    consumer_task.cancel()
    await close_publisher()
    logger.info("Order service shut down.")


app = FastAPI(title="SwiftTrack Order Service", lifespan=lifespan)
app.include_router(orders_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],  
)

@app.get("/health")
async def health():
    return {"status": "ok"}
