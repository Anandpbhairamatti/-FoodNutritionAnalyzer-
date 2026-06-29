import streamlit as st
from PIL import Image
import io
import pandas as pd
import os
import matplotlib.pyplot as plt
import importlib
import model.predict
importlib.reload(model.predict)
from model.predict import Predictor
from utils.image_processing import draw_predictions

st.set_page_config(page_title="Food Nutrition Analyzer", layout="centered")
st.title("🍽️ Multimodal Food Nutrition Analyzer")

# 1. Sidebar Configuration
st.sidebar.title("⚙️ Configuration")

st.sidebar.markdown(
    """
    ### About Gemini Vision AI
    * Recommended for complex or multi-item meals (like Indian Thalis, curries, mixed plates). 
    * It uses advanced vision-language understanding to detect arbitrary food items, estimate portions, and retrieve macronutrient values directly.
    """
)

# Initialize predictor
predictor = Predictor()

st.markdown("Upload a photo of your meal and get an estimated calorie and nutrition breakdown.")

uploaded = st.file_uploader("Upload food photo", type=['png', 'jpg', 'jpeg'])

if uploaded is not None:
    image = Image.open(io.BytesIO(uploaded.read())).convert('RGB')
    st.image(image, caption='Uploaded image', width='stretch')

    preds = []
    
    if len(predictor.rotator.keys) == 0:
        st.error("🔑 **No Gemini API Key found!** Please set the `GEMINI_API_KEY` environment variable in your terminal session, or add your key directly to the backup pool in [predict.py](file:///c:/Users/Administrator/OneDrive/Desktop/FA/model/predict.py#L42-L44).")
    else:
        with st.spinner('Analyzing image with Gemini Vision AI...'):
            try:
                preds = predictor.predict_gemini(image)
            except Exception as e:
                st.error(f"Error during Gemini analysis: {e}")

    if preds:
        # Normalize predictions into DataFrame
        df = pd.DataFrame(preds)
        st.subheader('Detected items')
        st.dataframe(df[['label','confidence']].rename(columns={'confidence':'confidence (0-1)'}))

        nutrition_rows = []
        for p in preds:
            label = p['label']
            nutr = p.get('nutrition', {})
            nutrition_rows.append({
                'label': label,
                'confidence': round(float(p.get('confidence', 0)), 3),
                'matched_food': nutr.get('name', label),
                'source': nutr.get('source', 'gemini'),
                'calories': nutr.get('calories'),
                'protein_g': nutr.get('protein_g'),
                'fat_g': nutr.get('fat_g'),
                'carbs_g': nutr.get('carbs_g'),
            })

        cols = ['label', 'confidence', 'matched_food', 'source', 'calories', 'protein_g', 'fat_g', 'carbs_g']
        nutr_df = pd.DataFrame(nutrition_rows)

        st.subheader('Estimated nutrition per detected item')
        display_df = nutr_df.fillna('N/A')
        st.table(display_df[cols])

        total = nutr_df[['calories','protein_g','fat_g','carbs_g']].apply(pd.to_numeric, errors='coerce').sum(skipna=True)
        total = total.round(1)
        st.subheader('Estimated total for meal')
        st.json({
            'calories': int(total.get('calories', 0)) if not pd.isna(total.get('calories', None)) else 0,
            'protein_g': float(total.get('protein_g', 0.0)),
            'fat_g': float(total.get('fat_g', 0.0)),
            'carbs_g': float(total.get('carbs_g', 0.0))
        })

        labels = ['protein_g','fat_g','carbs_g']
        vals = [float(total.get(c, 0.0)) for c in labels]
        if sum(vals) > 0:
            fig, ax = plt.subplots(figsize=(4,4))
            ax.pie(vals, labels=labels, autopct='%1.1f%%')
            ax.set_title('Macro-nutrient distribution (estimated)')
            st.pyplot(fig)
        else:
            st.info('Not enough numeric nutrition data to display macro distribution.')

        annotated = draw_predictions(image, preds)
        st.image(annotated, caption='Annotated detections', width='stretch')
else:
    st.info('Upload an image to get started.')
