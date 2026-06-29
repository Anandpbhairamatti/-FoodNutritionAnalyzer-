from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
import io
from model.predict import Predictor

app = FastAPI(title='Food Nutrition Analyzer API')

# Initialize predictor
predictor = Predictor()

@app.post('/analyze')
async def analyze(
    file: UploadFile = File(...)
):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert('RGB')
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    try:
        preds = predictor.predict_gemini(image)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini analysis failed: {str(e)}")

    results = []
    for p in preds:
        results.append({
            'label': p['label'],
            'confidence': float(p.get('confidence', 1.0)),
            'bbox': p.get('bbox'),
            'nutrition': p.get('nutrition')
        })
        
    return JSONResponse({
        'engine': 'gemini',
        'predictions': results
    })
