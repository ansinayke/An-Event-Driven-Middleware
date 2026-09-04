from fastapi import FastAPI, Depends, HTTPException
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.database import get_db
from app.models.user import User

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="ROS Mock Service")


@app.post("/routes/assign")
async def assign_route(payload: dict, db: AsyncSession = Depends(get_db)):
    logger.info(f"ROS Mock: received route assignment request for order {payload.get('order_id')}")
    driver_id = await db.execute(select(User).where(User.role == "DRIVER").order_by(func.random()).limit(1))
    driver_id = driver_id.scalars().first() 
    if not driver_id:
        raise HTTPException(status_code=503, detail="No drivers available")
    order_id = payload.get("order_id")
    destination = payload.get("destination", "unknown")
    logger.info(f"ROS: assigning route for order {order_id} to {destination}")
    return {
        "order_id": order_id,
        "route_id": f"ROUTE-{order_id[:8]}",
        "estimated_delivery": "2025-12-01T10:00:00Z",
        "driver_id": driver_id.id,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
