from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import httpx
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import json
import re


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class FoodSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 20

class NutritionInfo(BaseModel):
    energy_100g: Optional[float] = None
    fat_100g: Optional[float] = None
    saturated_fat_100g: Optional[float] = None
    carbohydrates_100g: Optional[float] = None
    sugars_100g: Optional[float] = None
    fiber_100g: Optional[float] = None
    proteins_100g: Optional[float] = None
    salt_100g: Optional[float] = None
    sodium_100g: Optional[float] = None

class FoodProduct(BaseModel):
    id: str
    product_name: str
    brand: Optional[str] = None
    image_url: Optional[str] = None
    barcode: Optional[str] = None
    nutriscore_grade: Optional[str] = None
    nova_group: Optional[int] = None
    nutrition: Optional[NutritionInfo] = None
    ingredients_text: Optional[str] = None
    health_score: Optional[float] = None
    health_rating: Optional[str] = None
    additives: Optional[List[str]] = None

class FoodTrackingEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    food_product: FoodProduct
    quantity: float = 100  # in grams
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class FoodTrackingCreate(BaseModel):
    user_id: str
    food_product: FoodProduct
    quantity: float = 100

class HealthScoreCalculator:
    @staticmethod
    def calculate_health_score(nutrition: NutritionInfo, nutriscore_grade: str = None, nova_group: int = None, additives: List[str] = None) -> tuple[float, str]:
        """Calculate health score from 0-100 and return rating"""
        score = 100  # Start with perfect score
        
        if nutrition:
            # Penalize high calories (above 300 kcal/100g)
            if nutrition.energy_100g and nutrition.energy_100g > 300:
                score -= min(30, (nutrition.energy_100g - 300) / 10)
            
            # Penalize high sugar (above 10g/100g)
            if nutrition.sugars_100g and nutrition.sugars_100g > 10:
                score -= min(25, (nutrition.sugars_100g - 10) * 2)
            
            # Penalize high sodium (above 1g/100g)
            if nutrition.sodium_100g and nutrition.sodium_100g > 1:
                score -= min(20, (nutrition.sodium_100g - 1) * 15)
            elif nutrition.salt_100g and nutrition.salt_100g > 2.5:
                score -= min(20, (nutrition.salt_100g - 2.5) * 6)
            
            # Penalize high saturated fat (above 5g/100g)
            if nutrition.saturated_fat_100g and nutrition.saturated_fat_100g > 5:
                score -= min(20, (nutrition.saturated_fat_100g - 5) * 2)
            
            # Reward high fiber (above 3g/100g)
            if nutrition.fiber_100g and nutrition.fiber_100g > 3:
                score += min(15, (nutrition.fiber_100g - 3) * 3)
            
            # Reward high protein (above 10g/100g)
            if nutrition.proteins_100g and nutrition.proteins_100g > 10:
                score += min(10, (nutrition.proteins_100g - 10) * 1)
        
        # Factor in Nutri-Score if available
        if nutriscore_grade:
            grade_penalties = {'a': 0, 'b': -5, 'c': -15, 'd': -25, 'e': -35}
            score += grade_penalties.get(nutriscore_grade.lower(), 0)
        
        # Factor in NOVA group (food processing level)
        if nova_group:
            nova_penalties = {1: 0, 2: -5, 3: -15, 4: -25}
            score += nova_penalties.get(nova_group, 0)
        
        # Penalize additives
        if additives:
            score -= min(15, len(additives) * 2)
        
        # Ensure score is within bounds
        score = max(0, min(100, score))
        
        # Convert to rating
        if score >= 80:
            rating = "Excellent"
        elif score >= 65:
            rating = "Good"
        elif score >= 50:
            rating = "Moderate"
        elif score >= 35:
            rating = "Poor"
        else:
            rating = "Very Poor"
        
        return round(score, 1), rating

class OpenFoodFactsService:
    BASE_URL = "https://world.openfoodfacts.org/api/v2"
    INDIA_BASE_URL = "https://in.openfoodfacts.org/api/v2"
    
    # Indian food categories and terms for enhanced search
    INDIAN_FOOD_CATEGORIES = [
        "dal", "rice", "wheat", "atta", "roti", "chapati", "naan", "paratha",
        "curry", "masala", "spices", "ghee", "oil", "pickle", "chutney",
        "sweets", "mithai", "laddu", "gulab jamun", "rasgulla", "jalebi",
        "namkeen", "bhujia", "mixture", "sev", "papad", "poha", "upma",
        "samosa", "kachori", "biscuit", "rusk", "tea", "chai", "coffee",
        "lassi", "buttermilk", "yogurt", "curd", "paneer", "milk", "coconut"
    ]
    
    @staticmethod
    async def search_products(query: str, limit: int = 20) -> List[FoodProduct]:
        """Search for food products using OpenFoodFacts API with Indian preference"""
        async with httpx.AsyncClient() as client:
            try:
                # Enhanced search with Indian terms and global fallback
                indian_products = await OpenFoodFactsService._search_with_url(
                    client, OpenFoodFactsService.INDIA_BASE_URL, query, min(limit, 15)
                )
                
                # If we have good results from Indian database, use them
                if len(indian_products) >= 5:
                    return indian_products[:limit]
                
                # Otherwise, search globally but with Indian preference
                global_products = await OpenFoodFactsService._search_with_url(
                    client, OpenFoodFactsService.BASE_URL, query, limit
                )
                
                # Combine and prioritize Indian products
                all_products = indian_products + global_products
                
                # Remove duplicates and prioritize Indian brands
                seen_products = set()
                filtered_products = []
                indian_brands = ["amul", "britannia", "parle", "haldiram", "mdh", "everest", "tata", "nestle india", "itc", "dabur", "patanjali"]
                
                # First pass: Indian brands
                for product in all_products:
                    if product.id not in seen_products:
                        if product.brand and any(brand in product.brand.lower() for brand in indian_brands):
                            filtered_products.append(product)
                            seen_products.add(product.id)
                
                # Second pass: Other products
                for product in all_products:
                    if product.id not in seen_products and len(filtered_products) < limit:
                        filtered_products.append(product)
                        seen_products.add(product.id)
                
                return filtered_products[:limit]
                
            except Exception as e:
                logging.error(f"Error searching products: {str(e)}")
                return []
    
    @staticmethod
    async def _search_with_url(client: httpx.AsyncClient, base_url: str, query: str, limit: int) -> List[FoodProduct]:
        """Search with specific base URL"""
        try:
            # Enhance query with Indian context if it matches Indian food categories
            enhanced_query = OpenFoodFactsService._enhance_indian_query(query)
            
            response = await client.get(
                f"{base_url}/search",
                params={
                    "search_terms": enhanced_query,
                    "page_size": limit,
                    "countries": "India" if "in.openfoodfacts.org" in base_url else "",
                    "fields": "code,product_name,brands,image_url,nutriscore_grade,nova_group,nutriments,ingredients_text,additives_tags,countries_tags"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            products = []
            for product in data.get("products", []):
                food_product = OpenFoodFactsService._parse_product(product)
                products.append(food_product)
            
            return products
        except Exception as e:
            logging.error(f"Error searching with URL {base_url}: {str(e)}")
            return []
    
    @staticmethod
    def _enhance_indian_query(query: str) -> str:
        """Enhance search query with Indian context"""
        query_lower = query.lower()
        
        # Map common Indian food terms to better search terms
        indian_mappings = {
            "atta": "wheat flour atta",
            "dal": "lentils dal",
            "chawal": "rice basmati",
            "ghee": "clarified butter ghee",
            "masala": "spice masala mix",
            "namkeen": "savory snacks namkeen",
            "mithai": "indian sweets",
            "chai": "tea chai",
            "lassi": "yogurt drink lassi",
            "papad": "papadum crispy",
            "pickle": "indian pickle achar"
        }
        
        for indian_term, enhanced_term in indian_mappings.items():
            if indian_term in query_lower:
                return enhanced_term
        
        return query
    
    @staticmethod
    async def get_product_by_barcode(barcode: str) -> Optional[FoodProduct]:
        """Get product details by barcode with Indian preference"""
        async with httpx.AsyncClient() as client:
            try:
                # Try Indian database first
                product = await OpenFoodFactsService._get_product_from_url(
                    client, OpenFoodFactsService.INDIA_BASE_URL, barcode
                )
                
                if product:
                    return product
                
                # Fallback to global database
                return await OpenFoodFactsService._get_product_from_url(
                    client, OpenFoodFactsService.BASE_URL, barcode
                )
                
            except Exception as e:
                logging.error(f"Error getting product by barcode: {str(e)}")
                return None
    
    @staticmethod
    async def _get_product_from_url(client: httpx.AsyncClient, base_url: str, barcode: str) -> Optional[FoodProduct]:
        """Get product from specific URL"""
        try:
            response = await client.get(
                f"{base_url}/product/{barcode}",
                params={
                    "fields": "code,product_name,brands,image_url,nutriscore_grade,nova_group,nutriments,ingredients_text,additives_tags,countries_tags"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == 1 and "product" in data:
                return OpenFoodFactsService._parse_product(data["product"])
            return None
        except Exception as e:
            logging.error(f"Error getting product from {base_url}: {str(e)}")
            return None
    
    @staticmethod
    async def search_indian_categories() -> List[str]:
        """Get popular Indian food categories"""
        return OpenFoodFactsService.INDIAN_FOOD_CATEGORIES
    
    @staticmethod
    def _parse_product(product_data: Dict[str, Any]) -> FoodProduct:
        """Parse OpenFoodFacts product data into our model"""
        # Extract nutrition information
        nutriments = product_data.get("nutriments", {})
        nutrition = NutritionInfo(
            energy_100g=nutriments.get("energy-kcal_100g"),
            fat_100g=nutriments.get("fat_100g"),
            saturated_fat_100g=nutriments.get("saturated-fat_100g"),
            carbohydrates_100g=nutriments.get("carbohydrates_100g"),
            sugars_100g=nutriments.get("sugars_100g"),
            fiber_100g=nutriments.get("fiber_100g"),
            proteins_100g=nutriments.get("proteins_100g"),
            salt_100g=nutriments.get("salt_100g"),
            sodium_100g=nutriments.get("sodium_100g")
        )
        
        # Extract additives
        additives = product_data.get("additives_tags", [])
        additives = [additive.replace("en:", "") for additive in additives if additive.startswith("en:")]
        
        # Calculate health score
        health_score, health_rating = HealthScoreCalculator.calculate_health_score(
            nutrition=nutrition,
            nutriscore_grade=product_data.get("nutriscore_grade"),
            nova_group=product_data.get("nova_group"),
            additives=additives
        )
        
        return FoodProduct(
            id=product_data.get("code", str(uuid.uuid4())),
            product_name=product_data.get("product_name", "Unknown Product"),
            brand=product_data.get("brands"),
            image_url=product_data.get("image_url"),
            barcode=product_data.get("code"),
            nutriscore_grade=product_data.get("nutriscore_grade"),
            nova_group=product_data.get("nova_group"),
            nutrition=nutrition,
            ingredients_text=product_data.get("ingredients_text"),
            health_score=health_score,
            health_rating=health_rating,
            additives=additives
        )

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Food Health Tracker API"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

@api_router.post("/food/search", response_model=List[FoodProduct])
async def search_food_products(request: FoodSearchRequest):
    """Search for food products"""
    products = await OpenFoodFactsService.search_products(request.query, request.limit)
    return products

@api_router.get("/food/barcode/{barcode}", response_model=FoodProduct)
async def get_food_by_barcode(barcode: str):
    """Get food product by barcode"""
    product = await OpenFoodFactsService.get_product_by_barcode(barcode)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@api_router.post("/food/track", response_model=FoodTrackingEntry)
async def track_food(request: FoodTrackingCreate):
    """Track food consumption"""
    tracking_entry = FoodTrackingEntry(**request.dict())
    await db.food_tracking.insert_one(tracking_entry.dict())
    return tracking_entry

@api_router.get("/food/track/{user_id}", response_model=List[FoodTrackingEntry])
async def get_food_tracking(user_id: str, limit: int = 50):
    """Get food tracking history for a user"""
    entries = await db.food_tracking.find({"user_id": user_id}).sort("timestamp", -1).limit(limit).to_list(limit)
    return [FoodTrackingEntry(**entry) for entry in entries]

@api_router.delete("/food/track/{entry_id}")
async def delete_food_tracking(entry_id: str):
    """Delete a food tracking entry"""
    result = await db.food_tracking.delete_one({"id": entry_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tracking entry not found")
    return {"message": "Tracking entry deleted successfully"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()