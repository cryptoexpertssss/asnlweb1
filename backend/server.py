from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt
from bson import ObjectId

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
SECRET_KEY = os.environ.get('SECRET_KEY', 'gobeauty-secret-key-change-in-production')
ALGORITHM = "HS256"

app = FastAPI()
api_router = APIRouter(prefix="/api")

# Models
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    created_at: datetime

class Salon(BaseModel):
    id: str
    name: str
    description: str
    address: str
    latitude: float
    longitude: float
    rating: float
    image: str
    phone: str
    opening_hours: str
    services_count: int

class Service(BaseModel):
    id: str
    salon_id: str
    name: str
    description: str
    category: str
    duration: int  # in minutes
    price: float
    image: str

class BookingCreate(BaseModel):
    service_id: str
    salon_id: str
    booking_date: str
    booking_time: str
    notes: Optional[str] = None

class Booking(BaseModel):
    id: str
    user_id: str
    service_id: str
    salon_id: str
    salon_name: str
    service_name: str
    booking_date: str
    booking_time: str
    status: str
    notes: Optional[str] = None
    created_at: datetime

class Category(BaseModel):
    id: str
    name: str
    icon: str
    color: str

# Helper functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Auth endpoints
@api_router.post("/auth/register")
async def register(user_data: UserRegister):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_dict = {
        "name": user_data.name,
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "phone": user_data.phone,
        "created_at": datetime.utcnow()
    }
    result = await db.users.insert_one(user_dict)
    user_id = str(result.inserted_id)
    
    # Create token
    token = create_access_token({"user_id": user_id, "email": user_data.email})
    
    return {
        "token": token,
        "user": {
            "id": user_id,
            "name": user_data.name,
            "email": user_data.email,
            "phone": user_data.phone
        }
    }

@api_router.post("/auth/login")
async def login(login_data: UserLogin):
    user = await db.users.find_one({"email": login_data.email})
    if not user or not verify_password(login_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    user_id = str(user["_id"])
    token = create_access_token({"user_id": user_id, "email": user["email"]})
    
    return {
        "token": token,
        "user": {
            "id": user_id,
            "name": user["name"],
            "email": user["email"],
            "phone": user.get("phone")
        }
    }

@api_router.get("/auth/me")
async def get_me(user_id: str = Depends(get_current_user)):
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "phone": user.get("phone")
    }

# Categories endpoint
@api_router.get("/categories")
async def get_categories():
    categories = [
        {"id": "1", "name": "Hair Salon", "icon": "cut", "color": "#FF1493"},
        {"id": "2", "name": "Makeup", "icon": "face", "color": "#FF69B4"},
        {"id": "3", "name": "Spa & Massage", "icon": "spa", "color": "#FFB6C1"},
        {"id": "4", "name": "Nails", "icon": "hand-left", "color": "#FFC0CB"},
        {"id": "5", "name": "Skincare", "icon": "heart", "color": "#FFD1DC"},
        {"id": "6", "name": "Bridal", "icon": "flower", "color": "#FF85B3"}
    ]
    return categories

# Salons endpoints
@api_router.get("/salons")
async def get_salons(latitude: Optional[float] = None, longitude: Optional[float] = None, category: Optional[str] = None):
    salons = await db.salons.find().to_list(100)
    result = []
    for salon in salons:
        salon_dict = {
            "id": str(salon["_id"]),
            "name": salon["name"],
            "description": salon["description"],
            "address": salon["address"],
            "latitude": salon["latitude"],
            "longitude": salon["longitude"],
            "rating": salon["rating"],
            "image": salon["image"],
            "phone": salon["phone"],
            "opening_hours": salon["opening_hours"],
            "services_count": salon.get("services_count", 0)
        }
        result.append(salon_dict)
    return result

@api_router.get("/salons/{salon_id}")
async def get_salon(salon_id: str):
    salon = await db.salons.find_one({"_id": ObjectId(salon_id)})
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    
    return {
        "id": str(salon["_id"]),
        "name": salon["name"],
        "description": salon["description"],
        "address": salon["address"],
        "latitude": salon["latitude"],
        "longitude": salon["longitude"],
        "rating": salon["rating"],
        "image": salon["image"],
        "phone": salon["phone"],
        "opening_hours": salon["opening_hours"],
        "services_count": salon.get("services_count", 0)
    }

# Services endpoints
@api_router.get("/services")
async def get_services(salon_id: Optional[str] = None, category: Optional[str] = None):
    query = {}
    if salon_id:
        query["salon_id"] = salon_id
    if category:
        query["category"] = category
    
    services = await db.services.find(query).to_list(100)
    result = []
    for service in services:
        service_dict = {
            "id": str(service["_id"]),
            "salon_id": service["salon_id"],
            "name": service["name"],
            "description": service["description"],
            "category": service["category"],
            "duration": service["duration"],
            "price": service["price"],
            "image": service["image"]
        }
        result.append(service_dict)
    return result

# Bookings endpoints
@api_router.post("/bookings")
async def create_booking(booking_data: BookingCreate, user_id: str = Depends(get_current_user)):
    # Get service and salon details
    service = await db.services.find_one({"_id": ObjectId(booking_data.service_id)})
    salon = await db.salons.find_one({"_id": ObjectId(booking_data.salon_id)})
    
    if not service or not salon:
        raise HTTPException(status_code=404, detail="Service or salon not found")
    
    booking_dict = {
        "user_id": user_id,
        "service_id": booking_data.service_id,
        "salon_id": booking_data.salon_id,
        "salon_name": salon["name"],
        "service_name": service["name"],
        "booking_date": booking_data.booking_date,
        "booking_time": booking_data.booking_time,
        "status": "confirmed",
        "notes": booking_data.notes,
        "created_at": datetime.utcnow()
    }
    
    result = await db.bookings.insert_one(booking_dict)
    booking_dict["id"] = str(result.inserted_id)
    
    return booking_dict

@api_router.get("/bookings")
async def get_bookings(user_id: str = Depends(get_current_user)):
    bookings = await db.bookings.find({"user_id": user_id}).to_list(100)
    result = []
    for booking in bookings:
        booking_dict = {
            "id": str(booking["_id"]),
            "user_id": booking["user_id"],
            "service_id": booking["service_id"],
            "salon_id": booking["salon_id"],
            "salon_name": booking["salon_name"],
            "service_name": booking["service_name"],
            "booking_date": booking["booking_date"],
            "booking_time": booking["booking_time"],
            "status": booking["status"],
            "notes": booking.get("notes"),
            "created_at": booking["created_at"]
        }
        result.append(booking_dict)
    return result

# Seed data endpoint (for testing)
@api_router.post("/seed-data")
async def seed_data():
    # Check if data already exists
    existing_salons = await db.salons.count_documents({})
    if existing_salons > 0:
        return {"message": "Data already seeded"}
    
    # Sample salons
    salons = [
        {
            "name": "Glamour Beauty Salon",
            "description": "Premium beauty services for modern women",
            "address": "123 Beauty Street, Downtown",
            "latitude": 33.6844,
            "longitude": 73.0479,
            "rating": 4.8,
            "image": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI0ZGNjlCNCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LXNpemU9IjIwIiBmaWxsPSJ3aGl0ZSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPlNhbG9uPC90ZXh0Pjwvc3ZnPg==",
            "phone": "+92 300 1234567",
            "opening_hours": "10:00 AM - 8:00 PM",
            "services_count": 12
        },
        {
            "name": "Pink Bliss Spa",
            "description": "Relax and rejuvenate with our spa treatments",
            "address": "456 Spa Avenue, City Center",
            "latitude": 33.6904,
            "longitude": 73.0551,
            "rating": 4.9,
            "image": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI0ZGQzBDQiIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LXNpemU9IjIwIiBmaWxsPSJ3aGl0ZSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPlNwYTwvdGV4dD48L3N2Zz4=",
            "phone": "+92 300 7654321",
            "opening_hours": "9:00 AM - 9:00 PM",
            "services_count": 8
        },
        {
            "name": "Elite Makeup Studio",
            "description": "Professional makeup for all occasions",
            "address": "789 Makeup Lane, Fashion District",
            "latitude": 33.6770,
            "longitude": 73.0415,
            "rating": 4.7,
            "image": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI0ZGMTQ5MyIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LXNpemU9IjIwIiBmaWxsPSJ3aGl0ZSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPk1ha2V1cDwvdGV4dD48L3N2Zz4=",
            "phone": "+92 300 9876543",
            "opening_hours": "11:00 AM - 7:00 PM",
            "services_count": 10
        }
    ]
    
    salon_results = await db.salons.insert_many(salons)
    salon_ids = [str(id) for id in salon_results.inserted_ids]
    
    # Sample services
    services = [
        # Salon 1 services
        {"salon_id": salon_ids[0], "name": "Haircut & Styling", "description": "Professional haircut with styling", "category": "Hair Salon", "duration": 60, "price": 1500, "image": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI0ZGNjlCNCIvPjwvc3ZnPg=="},
        {"salon_id": salon_ids[0], "name": "Hair Coloring", "description": "Full hair coloring service", "category": "Hair Salon", "duration": 120, "price": 3500, "image": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI0ZGNjlCNCIvPjwvc3ZnPg=="},
        {"salon_id": salon_ids[0], "name": "Keratin Treatment", "description": "Smooth and shiny hair treatment", "category": "Hair Salon", "duration": 180, "price": 8000, "image": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI0ZGNjlCNCIvPjwvc3ZnPg=="},
        # Salon 2 services
        {"salon_id": salon_ids[1], "name": "Full Body Massage", "description": "Relaxing full body massage", "category": "Spa & Massage", "duration": 90, "price": 4000, "image": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI0ZGQzBDQiIvPjwvc3ZnPg=="},
        {"salon_id": salon_ids[1], "name": "Facial Treatment", "description": "Deep cleansing facial", "category": "Skincare", "duration": 60, "price": 2500, "image": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI0ZGQzBDQiIvPjwvc3ZnPg=="},
        # Salon 3 services
        {"salon_id": salon_ids[2], "name": "Bridal Makeup", "description": "Complete bridal makeup package", "category": "Bridal", "duration": 120, "price": 15000, "image": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI0ZGMTQ5MyIvPjwvc3ZnPg=="},
        {"salon_id": salon_ids[2], "name": "Party Makeup", "description": "Glamorous party makeup", "category": "Makeup", "duration": 60, "price": 3500, "image": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI0ZGMTQ5MyIvPjwvc3ZnPg=="},
        {"salon_id": salon_ids[2], "name": "Manicure & Pedicure", "description": "Complete nail care", "category": "Nails", "duration": 90, "price": 2000, "image": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI0ZGMTQ5MyIvPjwvc3ZnPg=="}
    ]
    
    await db.services.insert_many(services)
    
    return {"message": "Sample data seeded successfully", "salons_count": len(salons), "services_count": len(services)}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()