from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordRequestForm
from PIL import Image
import io
from model.predict import Predictor
import utils.db_manager as db
from utils.jwt_manager import create_access_token, verify_access_token

app = FastAPI(title='Food Nutrition Analyzer API')

# Initialize predictor
predictor = Predictor()

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    username = verify_access_token(token)
    if username is not None:
        return username
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token or token expired",
        headers={"WWW-Authenticate": "Bearer"},
    )

@app.post('/token')
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    username = form_data.username
    password = form_data.password
    if db.authenticate_user(username, password):
        token = create_access_token(username)
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

@app.post('/analyze')
async def analyze(
    file: UploadFile = File(...),
    username: str = Depends(get_current_user)
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
        'authenticated_user': username,
        'predictions': results
    })
