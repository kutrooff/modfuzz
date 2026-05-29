from typing import Dict
import random
import time

from fastapi import APIRouter, FastAPI, Header, HTTPException, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel


app = FastAPI(
    title="ModFuzz Demo Microservices API",
    version="2.0.0",
    description=(
        "Demo API that imitates a small microservice system for stateful "
        "fuzzing experiments: identity, catalog, inventory, orders, "
        "payments, and shipments."
    ),
)

auth_router = APIRouter(tags=["identity-service"])
users_router = APIRouter(tags=["identity-service"])
catalog_router = APIRouter(tags=["catalog-service"])
inventory_router = APIRouter(tags=["inventory-service"])
orders_router = APIRouter(tags=["orders-service"])
payments_router = APIRouter(tags=["payments-service"])
shipments_router = APIRouter(tags=["shipments-service"])


users: Dict[int, dict] = {
    1: {
        "id": 1,
        "name": "Seed User",
        "email": "seed@example.com",
        "role": "customer",
    }
}
products: Dict[int, dict] = {
    1: {
        "id": 1,
        "name": "Seed Laptop",
        "sku": "SKU-SEED-1",
        "price": 999.0,
        "active": True,
    }
}
inventory: Dict[int, dict] = {
    1: {
        "productId": 1,
        "stock": 10,
        "reserved": 0,
    }
}
orders: Dict[int, dict] = {
    1: {
        "id": 1,
        "userId": 1,
        "productId": 1,
        "quantity": 1,
        "status": "paid",
        "total": 999.0,
        "promoCode": None,
    }
}
payments: Dict[int, dict] = {}
shipments: Dict[int, dict] = {}

next_user_id = 2
next_product_id = 2
next_order_id = 2
next_payment_id = 1
next_shipment_id = 1


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    name: str
    email: str | None = None
    role: str = "customer"


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    role: str | None = None


class ProductCreate(BaseModel):
    name: str
    sku: str
    price: float
    stock: int = 0


class ProductUpdate(BaseModel):
    name: str | None = None
    sku: str | None = None
    price: float | None = None
    active: bool | None = None


class InventoryUpdate(BaseModel):
    stock: int | None = None
    reserved: int | None = None


class OrderCreate(BaseModel):
    userId: int
    productId: int
    quantity: int
    promoCode: str | None = None


class OrderUpdate(BaseModel):
    status: str | None = None
    quantity: int | None = None


class PaymentCreate(BaseModel):
    orderId: int
    amount: float
    method: str


class ShipmentCreate(BaseModel):
    orderId: int
    address: str


class ShipmentUpdate(BaseModel):
    status: str | None = None
    address: str | None = None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "services": [
            "identity",
            "catalog",
            "inventory",
            "orders",
            "payments",
            "shipments",
        ],
    }


@auth_router.post("/auth/login")
def login(credentials: LoginRequest):
    if credentials.username.lower() == "locked":
        raise HTTPException(status_code=423, detail="Account is locked")

    if credentials.password != "admin":
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {
        "access_token": f"demo-token-{credentials.username}",
        "token": f"demo-token-{credentials.username}",
        "userId": 1,
        "role": "admin" if credentials.username == "admin" else "customer",
    }


@users_router.post("/users", status_code=201)
def create_user(user: UserCreate, response: Response):
    global next_user_id

    if user.name.lower() == "error":
        return {
            "status": "error",
            "message": "identity database failure detected",
        }

    if user.name.lower() == "crash":
        raise Exception("simulated identity database crash")

    if user.name.lower() == "slow":
        time.sleep(3)

    if user.name.lower() == "empty":
        return {}

    if user.name.lower() == "invalid":
        return PlainTextResponse(
            content="INVALID_JSON_RESPONSE",
            status_code=200,
        )

    if user.name.lower() == "random" and random.choice([True, False]):
        raise HTTPException(status_code=503, detail="identity service unavailable")

    if user.name.lower() == "large":
        return {
            "payload": "A" * 100000,
        }

    user_id = next_user_id
    next_user_id += 1

    created_user = {
        "id": user_id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
    }

    users[user_id] = created_user
    response.headers["Location"] = f"/users/{user_id}"

    return created_user


@users_router.get("/users/{userId}")
def get_user(userId: int):
    if userId < 0:
        return {
            "warning": "negative identifier accepted",
            "userId": userId,
        }

    user = users.get(userId)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@users_router.patch("/users/{userId}")
def update_user(userId: int, update: UserUpdate):
    if update.name == "timeout":
        time.sleep(5)

    user = users.get(userId)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if update.name == "hidden":
        return {
            "result": "update failed internally",
        }

    if update.name is not None:
        user["name"] = update.name

    if update.email is not None:
        user["email"] = update.email

    if update.role is not None:
        user["role"] = update.role

    return user


@users_router.delete("/users/{userId}", status_code=204)
def delete_user(userId: int):
    if random.randint(1, 10) == 5:
        raise HTTPException(status_code=500, detail="unexpected delete failure")

    if userId not in users:
        raise HTTPException(status_code=404, detail="User not found")

    del users[userId]
    return None


@catalog_router.post("/products", status_code=201)
def create_product(product: ProductCreate, response: Response, authorization: str | None = Header(None)):
    global next_product_id

    if product.name.lower() == "crash":
        raise Exception("simulated catalog service crash")

    if product.sku.lower() == "duplicate":
        raise HTTPException(status_code=409, detail="SKU already exists")

    if product.price < 0:
        return {
            "warning": "negative price accepted",
            "sku": product.sku,
            "price": product.price,
        }

    product_id = next_product_id
    next_product_id += 1

    created_product = {
        "id": product_id,
        "name": product.name,
        "sku": product.sku,
        "price": product.price,
        "active": True,
    }

    products[product_id] = created_product
    inventory[product_id] = {
        "productId": product_id,
        "stock": product.stock,
        "reserved": 0,
    }

    response.headers["Location"] = f"/products/{product_id}"
    return created_product


@catalog_router.get("/products/{productId}")
def get_product(productId: int):
    product = products.get(productId)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@catalog_router.patch("/products/{productId}")
def update_product(productId: int, update: ProductUpdate):
    product = products.get(productId)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    if update.name == "ghost":
        return {
            "result": "catalog index updated but product record is unchanged",
        }

    for field in ["name", "sku", "price", "active"]:
        value = getattr(update, field)
        if value is not None:
            product[field] = value

    return product


@catalog_router.delete("/products/{productId}", status_code=204)
def delete_product(productId: int):
    if any(order["productId"] == productId for order in orders.values()):
        raise HTTPException(status_code=409, detail="Product is referenced by orders")

    if productId not in products:
        raise HTTPException(status_code=404, detail="Product not found")

    del products[productId]
    inventory.pop(productId, None)
    return None


@inventory_router.get("/inventory/{productId}")
def get_inventory(productId: int):
    item = inventory.get(productId)

    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    return item


@inventory_router.patch("/inventory/{productId}")
def update_inventory(productId: int, update: InventoryUpdate):
    item = inventory.get(productId)

    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    if update.stock is not None:
        item["stock"] = update.stock

    if update.reserved is not None:
        item["reserved"] = update.reserved

    if item["reserved"] > item["stock"]:
        return {
            "warning": "reserved stock exceeds available stock",
            **item,
        }

    return item


@orders_router.post("/orders", status_code=201)
def create_order(order: OrderCreate, response: Response):
    global next_order_id

    if order.quantity == 13:
        raise Exception("unlucky quantity triggered order processor crash")

    if order.quantity > 1000:
        time.sleep(4)

    user = users.get(order.userId)
    product = products.get(order.productId)
    inventory_item = inventory.get(order.productId)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if product is None or inventory_item is None:
        raise HTTPException(status_code=404, detail="Product not found")

    if order.quantity <= 0:
        return {
            "warning": "non-positive quantity accepted",
            "userId": order.userId,
            "productId": order.productId,
            "quantity": order.quantity,
        }

    if inventory_item["stock"] < order.quantity:
        raise HTTPException(status_code=409, detail="Not enough stock")

    order_id = next_order_id
    next_order_id += 1
    total = round(product["price"] * order.quantity, 2)

    created_order = {
        "id": order_id,
        "userId": order.userId,
        "productId": order.productId,
        "quantity": order.quantity,
        "status": "created",
        "total": total,
        "promoCode": order.promoCode,
    }

    orders[order_id] = created_order
    inventory_item["stock"] -= order.quantity
    inventory_item["reserved"] += order.quantity

    response.headers["Location"] = f"/orders/{order_id}"
    return created_order


@orders_router.get("/orders/{orderId}")
def get_order(orderId: int):
    order = orders.get(orderId)

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    return order


@orders_router.patch("/orders/{orderId}")
def update_order(orderId: int, update: OrderUpdate):
    order = orders.get(orderId)

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if update.status == "corrupt":
        return {
            "status": "corrupt",
            "message": "order state machine accepted invalid transition",
        }

    if update.status is not None:
        order["status"] = update.status

    if update.quantity is not None:
        order["quantity"] = update.quantity

    return order


@orders_router.delete("/orders/{orderId}", status_code=204)
def cancel_order(orderId: int):
    order = orders.get(orderId)

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    order["status"] = "cancelled"
    return None


@payments_router.post("/payments", status_code=201)
def create_payment(payment: PaymentCreate, response: Response):
    global next_payment_id

    if payment.method == "timeout":
        time.sleep(5)

    if payment.method == "crash":
        raise Exception("payment gateway crashed")

    order = orders.get(payment.orderId)

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if payment.method == "card_declined":
        raise HTTPException(status_code=402, detail="Card was declined")

    if payment.amount < 0:
        return {
            "warning": "negative payment was accepted",
            "orderId": payment.orderId,
            "amount": payment.amount,
        }

    status = "paid"
    if round(payment.amount, 2) != round(order["total"], 2):
        status = "amount_mismatch_accepted"

    payment_id = next_payment_id
    next_payment_id += 1

    created_payment = {
        "id": payment_id,
        "orderId": payment.orderId,
        "amount": payment.amount,
        "method": payment.method,
        "status": status,
        "transactionId": f"tx-{payment_id:06d}",
    }

    payments[payment_id] = created_payment
    order["status"] = "paid" if status == "paid" else order["status"]

    response.headers["Location"] = f"/payments/{payment_id}"
    return created_payment


@payments_router.get("/payments/{paymentId}")
def get_payment(paymentId: int):
    payment = payments.get(paymentId)

    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    return payment


@shipments_router.post("/shipments", status_code=201)
def create_shipment(shipment: ShipmentCreate, response: Response):
    global next_shipment_id

    order = orders.get(shipment.orderId)

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if order["status"] != "paid":
        raise HTTPException(status_code=409, detail="Order must be paid before shipment")

    if shipment.address.lower() == "lost":
        return {
            "warning": "shipment created without tracking number",
            "orderId": shipment.orderId,
        }

    shipment_id = next_shipment_id
    next_shipment_id += 1

    created_shipment = {
        "id": shipment_id,
        "orderId": shipment.orderId,
        "address": shipment.address,
        "status": "created",
        "trackingNumber": f"TRK-{shipment_id:06d}",
    }

    shipments[shipment_id] = created_shipment
    order["status"] = "shipped"

    response.headers["Location"] = f"/shipments/{shipment_id}"
    return created_shipment


@shipments_router.get("/shipments/{shipmentId}")
def get_shipment(shipmentId: int):
    shipment = shipments.get(shipmentId)

    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")

    return shipment


@shipments_router.patch("/shipments/{shipmentId}")
def update_shipment(shipmentId: int, update: ShipmentUpdate):
    shipment = shipments.get(shipmentId)

    if shipment is None:
        raise HTTPException(status_code=404, detail="Shipment not found")

    if update.status == "teleport":
        return {
            "warning": "invalid shipment status accepted",
            "shipmentId": shipmentId,
            "status": update.status,
        }

    if update.status is not None:
        shipment["status"] = update.status

    if update.address is not None:
        shipment["address"] = update.address

    return shipment


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(catalog_router)
app.include_router(inventory_router)
app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(shipments_router)
