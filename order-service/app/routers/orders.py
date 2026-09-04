import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.order import Order, OrderStatus
from app.schemas.order import CreateOrderRequest, OrderResponse
from app.core.security import require_role, get_current_user
from app.events.publisher import publish_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["orders"])


@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: CreateOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("CLIENT")),
):
    order = Order(
        client_id=current_user["user_id"],
        description=payload.description,
        destination=payload.destination,
        status=OrderStatus.CREATED,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    await publish_event("order.created", {
        "order_id": order.id,
        "client_id": order.client_id,
        "description": order.description,
        "destination": order.destination,
    })
    logger.info(f"Order created: {order.id}")
    return order

@router.get("/orders/my-orders/{client_id}", response_model=list[OrderResponse])
async def get_my_orders(
    client_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("CLIENT")),
):
    if current_user["user_id"] != client_id:
        raise HTTPException(status_code=403, detail="Access denied")
    result = await db.execute(select(Order).where(Order.client_id == client_id).order_by(Order.created_at.desc()))
    orders = result.scalars().all()
    return orders

@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("CLIENT")),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.client_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return order

@router.get("/drivers/{driver_id}/deliveries", response_model=list[OrderResponse])
async def get_driver_deliveries(
    driver_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("DRIVER")),
):
    if current_user["user_id"] != driver_id:
        raise HTTPException(status_code=403, detail="Driver ID mismatch")
    result = await db.execute(select(Order).where(Order.driver_id == driver_id).order_by(Order.created_at.desc()))
    orders = result.scalars().all()
    return orders

@router.post("/drivers/{driver_id}/deliveries/{order_id}/complete", response_model=OrderResponse)
async def complete_delivery(
    driver_id: str,
    order_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("DRIVER")),
):
    if current_user["user_id"] != driver_id:
        raise HTTPException(status_code=403, detail="Driver ID mismatch")

    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = OrderStatus.DELIVERED
    order.digital_signature_url = payload.get("digital_signature_url")
    order.pod_image_url = payload.get("pod_image_url")
    await db.commit()
    await db.refresh(order)

    await publish_event("order.delivered", {"order_id": order.id, "driver_id": driver_id})
    logger.info(f"Order {order.id} marked DELIVERED by driver {driver_id}")
    return order

@router.post("/drivers/{driver_id}/deliveries/{order_id}/fail", response_model=OrderResponse)
async def fail_delivery(
    driver_id: str,
    order_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("DRIVER")),
):
    if current_user["user_id"] != driver_id:
        raise HTTPException(status_code=403, detail="Driver ID mismatch")

    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = OrderStatus.FAILED
    order.failed_reason = payload.get("failed_reason")
    await db.commit()
    await db.refresh(order)

    await publish_event("order.failed", {"order_id": order.id, "driver_id": driver_id, "reason": order.failed_reason})
    logger.info(f"Order {order.id} marked FAILED by driver {driver_id} with reason: {order.failed_reason}")
    return order