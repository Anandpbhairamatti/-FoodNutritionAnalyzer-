"""Predictor using Gemini Vision AI with Auto-Key Rotation.

Behavior:
- Supports predicting via Gemini for advanced, highly accurate multimodal analysis.
- Automatically handles API key rotation if a key expires or runs out of quota.
- Outputs detections as [{'label':str,'confidence':float,'bbox':[x1,y1,x2,y2],'nutrition':{...}}, ...]
"""
import os
from typing import List, Dict, Optional
from PIL import Image
import numpy as np
from pydantic import BaseModel, Field
import google.generativeai as genai
import json

class FoodItem(BaseModel):
    label: str = Field(description="Name/label of the detected food item (e.g. White Rice, Roti, Dal, Mixed Vegetable Curry, Salad)")
    ymin: float = Field(description="Bounding box top coordinate (0 to 1000)")
    xmin: float = Field(description="Bounding box left coordinate (0 to 1000)")
    ymax: float = Field(description="Bounding box bottom coordinate (0 to 1000)")
    xmax: float = Field(description="Bounding box right coordinate (0 to 1000)")
    calories: float = Field(description="Estimated calories in kcal")
    protein_g: float = Field(description="Estimated protein in grams")
    fat_g: float = Field(description="Estimated fat in grams")
    carbs_g: float = Field(description="Estimated carbohydrates in grams")
    matched_food: str = Field(description="Canonical food name or description of matching food")

class FoodAnalysisResponse(BaseModel):
    predictions: List[FoodItem]

class DietitianFeedback(BaseModel):
    balance_rating: str = Field(description="Meal Balance Rating (e.g. Protein-deficient, Well-balanced, High fat, Carb-heavy)")
    insights: List[str] = Field(description="2-3 bullet points of dietary insights explaining the nutritional profile (e.g. glycemic impact, fiber, healthy fats)")
    recommendations: List[str] = Field(description="2-3 actionable tips to improve the meal/nutrition balance")

class ApiKeyRotator:
    def __init__(self):
        self.keys = []
        
        # Load from local .env file if it exists to avoid hardcoding secrets
        env_paths = [
            ".env",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        ]
        for path in env_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                k, v = line.split("=", 1)
                                k, v = k.strip(), v.strip()
                                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                                    v = v[1:-1]
                                if k and v and k not in os.environ:
                                    os.environ[k] = v
                except Exception:
                    pass
        
        # Check standard environment variables
        primary_key = os.getenv("GEMINI_API_KEY")
        if primary_key:
            self.keys.append(primary_key)
            
        # Check fallback/alternative environment variables (e.g., GEMINI_API_KEY_1, GEMINI_API_KEY_2)
        for i in range(1, 10):
            k = os.getenv(f"GEMINI_API_KEY_{i}")
            if k:
                self.keys.append(k)

        # Hardcoded backup pool in code (user can insert keys directly here)
        hardcoded_keys = []
        self.keys.extend(hardcoded_keys)
        
        # Remove duplicates while preserving order
        seen = set()
        self.keys = [x for x in self.keys if not (x in seen or seen.add(x))]
        
        self.current_idx = 0

    def get_key(self) -> Optional[str]:
        if not self.keys:
            return None
        return self.keys[self.current_idx]

    def rotate_key(self) -> bool:
        if not self.keys or len(self.keys) <= 1:
            return False
        self.current_idx = (self.current_idx + 1) % len(self.keys)
        return True

class Predictor:
    def __init__(self):
        self.rotator = ApiKeyRotator()

    def predict_gemini(self, image: Image.Image) -> List[Dict]:
        attempts = max(1, len(self.rotator.keys))
        last_error = "No API keys found in pool or environment variables."
        
        for _ in range(attempts):
            api_key = self.rotator.get_key()
            if not api_key:
                break
                
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                prompt = (
                    "Analyze this food image. Detect all individual food items. For each item, "
                    "draw a bounding box around it (coordinates 0 to 1000 relative to the image size) "
                    "and estimate its macronutrients (calories, protein in grams, fat in grams, carbohydrates in grams)."
                )
                
                response = model.generate_content(
                    [prompt, image],
                    generation_config={
                        "response_mime_type": "application/json",
                        "response_schema": FoodAnalysisResponse,
                    }
                )
                
                data = json.loads(response.text)
                raw_preds = data.get("predictions", [])
                
                width, height = image.size
                out = []
                
                for item in raw_preds:
                    ymin = float(item.get('ymin', 0.0))
                    xmin = float(item.get('xmin', 0.0))
                    ymax = float(item.get('ymax', 0.0))
                    xmax = float(item.get('xmax', 0.0))
                    
                    x1 = float(xmin / 1000.0 * width)
                    y1 = float(ymin / 1000.0 * height)
                    x2 = float(xmax / 1000.0 * width)
                    y2 = float(ymax / 1000.0 * height)
                    
                    label = item.get('label', 'Unknown Food')
                    
                    out.append({
                        'label': label,
                        'confidence': 1.0,
                        'bbox': [x1, y1, x2, y2],
                        'nutrition': {
                            'name': item.get('matched_food', label),
                            'calories': item.get('calories'),
                            'protein_g': item.get('protein_g'),
                            'fat_g': item.get('fat_g'),
                            'carbs_g': item.get('carbs_g'),
                            'serving_size': 'Estimated portion',
                            'match': label,
                            'source': 'gemini'
                        }
                    })
                return out
                
            except Exception as e:
                last_error = str(e)
                # Rotate key and retry
                if not self.rotator.rotate_key():
                    break
                    
        raise RuntimeError(f"Gemini API request failed. Last error: {last_error}")

    def get_dietitian_feedback(self, items: List[Dict]) -> Dict:
        """Retrieve structured AI dietitian advice based on the active list of food items."""
        attempts = max(1, len(self.rotator.keys))
        last_error = "No API keys found in pool or environment variables."
        
        meal_description = []
        total_cal = 0.0
        total_protein = 0.0
        total_fat = 0.0
        total_carbs = 0.0
        
        for item in items:
            label = item.get('label', 'Unknown')
            # Extract nutr fields which might be nested in 'nutrition' or direct
            nutr = item.get('nutrition', {}) if isinstance(item.get('nutrition'), dict) else item
            
            cal = float(nutr.get('calories') or 0.0)
            prot = float(nutr.get('protein_g') or nutr.get('protein') or 0.0)
            fat = float(nutr.get('fat_g') or nutr.get('fat') or 0.0)
            carbs = float(nutr.get('carbs_g') or nutr.get('carbs') or 0.0)
            portion = float(item.get('portion', 1.0))
            
            # apply portion multiplier
            cal_eff = cal * portion
            prot_eff = prot * portion
            fat_eff = fat * portion
            carbs_eff = carbs * portion
            
            total_cal += cal_eff
            total_protein += prot_eff
            total_fat += fat_eff
            total_carbs += carbs_eff
            
            meal_description.append(
                f"- {label}: portion factor {portion:.1f}x, Calories: {cal_eff:.1f} kcal, "
                f"Protein: {prot_eff:.1f}g, Carbs: {carbs_eff:.1f}g, Fat: {fat_eff:.1f}g"
            )
            
        meal_summary = "\n".join(meal_description)
        prompt = (
            f"You are a professional registered dietitian. Analyze the following meal:\n\n"
            f"{meal_summary}\n\n"
            f"Total meal macros:\n"
            f"- Total Calories: {total_cal:.1f} kcal\n"
            f"- Total Protein: {total_protein:.1f}g\n"
            f"- Total Carbs: {total_carbs:.1f}g\n"
            f"- Total Fat: {total_fat:.1f}g\n\n"
            f"Provide a balance rating, key nutritional insights, and practical recommendations to optimize this meal."
        )
        
        for _ in range(attempts):
            api_key = self.rotator.get_key()
            if not api_key:
                break
                
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                response = model.generate_content(
                    prompt,
                    generation_config={
                        "response_mime_type": "application/json",
                        "response_schema": DietitianFeedback,
                    }
                )
                
                data = json.loads(response.text)
                return {
                    "balance_rating": data.get("balance_rating", "Unknown"),
                    "insights": data.get("insights", []),
                    "recommendations": data.get("recommendations", [])
                }
                
            except Exception as e:
                last_error = str(e)
                # Rotate key and retry
                if not self.rotator.rotate_key():
                    break
                    
        return {
            "balance_rating": "Unable to load analysis",
            "insights": [f"Error connecting to AI Coach: {last_error}"],
            "recommendations": ["Please check your internet connection or API Key rotation pool."]
        }

