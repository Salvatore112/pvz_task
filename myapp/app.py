from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
from fastapi.responses import PlainTextResponse
from prometheus_client import start_http_server
import uuid


app = FastAPI()
security = HTTPBearer()

# Prometheus metrics
REQUEST_COUNT = Counter(
    "request_count", "App Request Count", ["method", "endpoint", "http_status"]
)

REQUEST_LATENCY = Histogram(
    "request_latency_seconds", "Request latency", ["method", "endpoint"]
)

PVZ_CREATED = Counter("pvz_created_total", "Total number of PVZs created")

RECEPTIONS_CREATED = Counter(
    "receptions_created_total", "Total number of receptions created"
)

PRODUCTS_ADDED = Counter("products_added_total", "Total number of products added")

# In-memory database
db = {
    "users": {},
    "pvzs": {},
    "receptions": {},
    "products": {},
    "tokens": {},
}


# Models
class Token(BaseModel):
    token: str


class UserRegister(BaseModel):
    email: str
    password: str
    role: str


class UserLogin(BaseModel):
    email: str
    password: str


class DummyLogin(BaseModel):
    role: str


class PVZCreate(BaseModel):
    city: str


class PVZ(BaseModel):
    id: str
    registrationDate: str
    city: str


class ReceptionCreate(BaseModel):
    pvzId: str


class Reception(BaseModel):
    id: str
    dateTime: str
    pvzId: str
    status: str


class ProductCreate(BaseModel):
    type: str
    pvzId: str


class Product(BaseModel):
    id: str
    dateTime: str
    type: str
    receptionId: str


class PVZResponse(BaseModel):
    pvz: PVZ
    receptions: List[Dict]


# Helper functions
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user_id = db["tokens"].get(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return db["users"][user_id]


def get_open_reception(pvz_id: str):
    for reception in db["receptions"].values():
        if reception["pvzId"] == pvz_id and reception["status"] == "in_progress":
            return reception
    return None


# Add middleware for metrics
@app.middleware("http")
async def monitor_requests(request, call_next):
    method = request.method
    endpoint = request.url.path

    if endpoint == "/metrics":
        return await call_next(request)

    with REQUEST_LATENCY.labels(method, endpoint).time():
        response = await call_next(request)
        REQUEST_COUNT.labels(method, endpoint, response.status_code).inc()

    return response


# Metrics endpoint
@app.get("/metrics")
async def metrics():
    return PlainTextResponse(generate_latest(REGISTRY))


# Auth endpoints
@app.post("/dummyLogin", response_model=Token)
def dummy_login(data: DummyLogin):
    if data.role not in ["employee", "moderator"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    token = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    db["users"][user_id] = {
        "id": user_id,
        "role": data.role,
    }
    db["tokens"][token] = user_id

    return {"token": token}


@app.post("/register", status_code=201)
def register(user: UserRegister):
    if user.role not in ["employee", "moderator"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    for existing_user in db["users"].values():
        if existing_user.get("email") == user.email:
            raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    db["users"][user_id] = {
        "id": user_id,
        "email": user.email,
        "password": user.password,
        "role": user.role,
    }

    return {"id": user_id, "email": user.email, "role": user.role}


@app.post("/login", response_model=Token)
def login(user: UserLogin):
    for existing_user in db["users"].values():
        if existing_user.get("email") == user.email:
            if existing_user.get("password") == user.password:
                token = str(uuid.uuid4())
                db["tokens"][token] = existing_user["id"]
                return {"token": token}

    raise HTTPException(status_code=401, detail="Invalid credentials")


# PVZ endpoints
@app.post("/pvz", response_model=PVZ, status_code=201)
def create_pvz(pvz: PVZCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "moderator":
        raise HTTPException(status_code=403, detail="Only moderators can create PVZs")

    if pvz.city not in ["Москва", "Санкт-Петербург", "Казань"]:
        raise HTTPException(
            status_code=400,
            detail="PVZ can only be created in Москва, Санкт-Петербург or Казань",
        )

    pvz_id = str(uuid.uuid4())
    db["pvzs"][pvz_id] = {
        "id": pvz_id,
        "registrationDate": datetime.now().isoformat(),
        "city": pvz.city,
    }

    PVZ_CREATED.inc()
    return db["pvzs"][pvz_id]


@app.get("/pvz", response_model=List[PVZResponse])
def get_pvz_list(
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=30),
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] not in ["employee", "moderator"]:
        raise HTTPException(status_code=403, detail="Access denied")

    result = []

    for pvz in db["pvzs"].values():
        receptions_data = []

        for reception in db["receptions"].values():
            if reception["pvzId"] == pvz["id"]:
                reception_date = datetime.fromisoformat(reception["dateTime"])
                if startDate and endDate:
                    start_date = datetime.fromisoformat(startDate)
                    end_date = datetime.fromisoformat(endDate)
                    if not (start_date <= reception_date <= end_date):
                        continue

                products = [
                    p
                    for p in db["products"].values()
                    if p["receptionId"] == reception["id"]
                ]

                receptions_data.append({"reception": reception, "products": products})

        result.append({"pvz": pvz, "receptions": receptions_data})

    start = (page - 1) * limit
    end = start + limit
    return result[start:end]


@app.post("/pvz/{pvzId}/close_last_reception", response_model=Reception)
def close_last_reception(pvzId: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "employee":
        raise HTTPException(
            status_code=403, detail="Only employees can close receptions"
        )

    if pvzId not in db["pvzs"]:
        raise HTTPException(status_code=404, detail="PVZ not found")

    open_reception = get_open_reception(pvzId)
    if not open_reception:
        raise HTTPException(status_code=400, detail="No open reception found")

    open_reception["status"] = "close"
    return open_reception


@app.post("/pvz/{pvzId}/delete_last_product")
def delete_last_product(pvzId: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "employee":
        raise HTTPException(
            status_code=403, detail="Only employees can delete products"
        )

    if pvzId not in db["pvzs"]:
        raise HTTPException(status_code=404, detail="PVZ not found")

    open_reception = get_open_reception(pvzId)
    if not open_reception:
        raise HTTPException(status_code=400, detail="No open reception found")

    products = [
        p for p in db["products"].values() if p["receptionId"] == open_reception["id"]
    ]

    if not products:
        raise HTTPException(status_code=400, detail="No products to delete")

    last_product = products[-1]
    del db["products"][last_product["id"]]

    return {"message": "Product deleted", "product": last_product}


# Reception endpoints
@app.post("/receptions", response_model=Reception, status_code=201)
def create_reception(
    reception: ReceptionCreate, current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "employee":
        raise HTTPException(
            status_code=403, detail="Only employees can create receptions"
        )

    if reception.pvzId not in db["pvzs"]:
        raise HTTPException(status_code=404, detail="PVZ not found")

    if get_open_reception(reception.pvzId):
        raise HTTPException(
            status_code=400, detail="There is already an open reception"
        )

    reception_id = str(uuid.uuid4())
    db["receptions"][reception_id] = {
        "id": reception_id,
        "dateTime": datetime.now().isoformat(),
        "pvzId": reception.pvzId,
        "status": "in_progress",
    }

    RECEPTIONS_CREATED.inc()
    return db["receptions"][reception_id]


# Product endpoints
@app.post("/products", response_model=Product, status_code=201)
def add_product(product: ProductCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "employee":
        raise HTTPException(status_code=403, detail="Only employees can add products")

    if product.pvzId not in db["pvzs"]:
        raise HTTPException(status_code=404, detail="PVZ not found")

    open_reception = get_open_reception(product.pvzId)
    if not open_reception:
        raise HTTPException(status_code=400, detail="No open reception found")

    if product.type not in ["электроника", "одежда", "обувь"]:
        raise HTTPException(status_code=400, detail="Invalid product type")

    product_id = str(uuid.uuid4())
    db["products"][product_id] = {
        "id": product_id,
        "dateTime": datetime.now().isoformat(),
        "type": product.type,
        "receptionId": open_reception["id"],
    }

    PRODUCTS_ADDED.inc()
    return db["products"][product_id]


start_http_server(9000)
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
