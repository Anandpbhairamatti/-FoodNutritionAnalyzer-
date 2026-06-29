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

class ApiKeyRotator:
    def __init__(self):
        self.keys = []
        
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
