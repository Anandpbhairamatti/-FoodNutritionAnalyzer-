import streamlit as st
from PIL import Image
import io
import pandas as pd
import os
import matplotlib.pyplot as plt
import numpy as np
import importlib
import uuid

import model.predict
importlib.reload(model.predict)
from model.predict import Predictor
from utils.image_processing import draw_predictions

# Custom tracking utilities
import utils.db_manager as db
import utils.pdf_generator as pdf

# Set premium layout page configuration
st.set_page_config(page_title="Food Nutrition Analyzer", layout="wide")

# Helper function to trigger a Streamlit page reload
def force_rerun():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

# Load custom CSS styling for premium look
def load_css(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("assets/custom_style.css")

# Initialize global prediction model
predictor = Predictor()

# ----------------- SESSION STATE SETUP -----------------
# Authentication state
if 'user' not in st.session_state:
    if "user" in st.query_params:
        st.session_state['user'] = st.query_params["user"]
    else:
        st.session_state['user'] = None

# Registration verification states
if 'reg_pending_verification' not in st.session_state:
    st.session_state['reg_pending_verification'] = False
if 'reg_username_pending' not in st.session_state:
    st.session_state['reg_username_pending'] = None
if 'reg_email_pending' not in st.session_state:
    st.session_state['reg_email_pending'] = None
if 'reg_otp_code' not in st.session_state:
    st.session_state['reg_otp_code'] = None
if 'reg_smtp_msg' not in st.session_state:
    st.session_state['reg_smtp_msg'] = None

# Single Meal analysis states
if 'active_items' not in st.session_state:
    st.session_state['active_items'] = []
if 'current_image' not in st.session_state:
    st.session_state['current_image'] = None
if 'annotated_image' not in st.session_state:
    st.session_state['annotated_image'] = None
if 'dietitian_feedback' not in st.session_state:
    st.session_state['dietitian_feedback'] = None
if 'analyzed_image_key' not in st.session_state:
    st.session_state['analyzed_image_key'] = None

# Comparison states
if 'comp_a_file_key' not in st.session_state:
    st.session_state['comp_a_file_key'] = None
if 'comp_a_items' not in st.session_state:
    st.session_state['comp_a_items'] = []
if 'comp_a_image' not in st.session_state:
    st.session_state['comp_a_image'] = None
if 'comp_a_feedback' not in st.session_state:
    st.session_state['comp_a_feedback'] = None

if 'comp_b_file_key' not in st.session_state:
    st.session_state['comp_b_file_key'] = None
if 'comp_b_items' not in st.session_state:
    st.session_state['comp_b_items'] = []
if 'comp_b_image' not in st.session_state:
    st.session_state['comp_b_image'] = None
if 'comp_b_feedback' not in st.session_state:
    st.session_state['comp_b_feedback'] = None


# ----------------- AUTHENTICATION UI -----------------
def render_login_signup():
    st.markdown("<h2 style='text-align: center; color: #a78bfa; margin-top: 50px;'>🍽️ Multimodal Food Nutrition Analyzer</h2>", unsafe_allow_html=True)
    
    col_l, col_c, col_r = st.columns([1, 1.5, 1])
    with col_c:
        st.markdown("""
        <div class="food-card" style="padding: 24px;">
        """, unsafe_allow_html=True)
        
        if st.session_state.get('reg_pending_verification'):
            st.markdown("<h3 style='color: #f3f4f6;'>Verify Your Email</h3>", unsafe_allow_html=True)
            st.markdown(f"We've sent a 6-digit verification code to **{st.session_state['reg_email_pending']}**.")
            
            email_sent = st.session_state.get('reg_smtp_msg') == "Verification email sent successfully."
            if email_sent:
                st.success("📬 Please check your Gmail inbox (and Spam folder) for the verification code.")
            else:
                st.error(f"⚠️ Could not send verification email. Error details: {st.session_state.get('reg_smtp_msg')}")
                
            otp_input = st.text_input("Enter 6-digit Verification Code", max_chars=6, placeholder="e.g. 123456")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("Verify & Activate", use_container_width=True):
                    verified, msg = db.verify_user_otp(st.session_state['reg_username_pending'], otp_input)
                    if verified:
                        st.success(msg)
                        st.session_state['reg_pending_verification'] = False
                        st.session_state['reg_username_pending'] = None
                        st.session_state['reg_email_pending'] = None
                        st.session_state['reg_otp_code'] = None
                        st.session_state['reg_smtp_msg'] = None
                        force_rerun()
                    else:
                        st.error(msg)
            with col_btn2:
                if st.button("Cancel & Go Back", use_container_width=True):
                    st.session_state['reg_pending_verification'] = False
                    st.session_state['reg_username_pending'] = None
                    st.session_state['reg_email_pending'] = None
                    st.session_state['reg_otp_code'] = None
                    st.session_state['reg_smtp_msg'] = None
                    force_rerun()
        else:
            st.markdown("<p style='text-align: center; color: #9ca3af; margin-bottom: 20px;'>Securely sign in or register to log meals, configure daily target goals, and get AI dietitian coaching.</p>", unsafe_allow_html=True)
            auth_tab1, auth_tab2 = st.tabs(["🔑 Sign In", "📝 Register Account"])
            
            with auth_tab1:
                st.markdown("<h4 style='color: #f3f4f6; margin-top: 10px;'>Sign In</h4>", unsafe_allow_html=True)
                st.info("💡 **Demo Account:** Username: `guest` | Password: `guest`")
                login_username = st.text_input("Username", key="login_username", placeholder="Enter username")
                login_password = st.text_input("Password", type="password", key="login_password", placeholder="Enter password")
                if st.button("Log In", use_container_width=True):
                    if not login_username.strip() or not login_password:
                        st.error("Please fill in both username and password.")
                    else:
                        if db.authenticate_user(login_username, login_password):
                            username = login_username.strip().lower()
                            st.session_state['user'] = username
                            st.query_params["user"] = username
                            st.success(f"Welcome back, {login_username}!")
                            force_rerun()
                        else:
                            st.error("Invalid credentials or account is unverified.")
                            
            with auth_tab2:
                st.markdown("<h4 style='color: #f3f4f6; margin-top: 10px;'>Create Account</h4>", unsafe_allow_html=True)
                reg_username = st.text_input("Username", key="reg_username", placeholder="Choose username")
                reg_email = st.text_input("Gmail Address", key="reg_email", placeholder="username@gmail.com")
                reg_password = st.text_input("Password", type="password", key="reg_password", placeholder="Choose password")
                reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm", placeholder="Confirm password")
                if st.button("Register", use_container_width=True):
                    if not reg_username.strip() or not reg_password or not reg_confirm or not reg_email.strip():
                        st.error("Please fill in all fields.")
                    elif not reg_email.strip().lower().endswith("@gmail.com"):
                        st.error("Registration must be with a valid Gmail address (@gmail.com).")
                    elif reg_password != reg_confirm:
                        st.error("Passwords do not match.")
                    elif len(reg_password) < 4:
                        st.error("Password must be at least 4 characters long.")
                    else:
                        success, generated_otp, smtp_msg = db.create_user(reg_username, reg_password, reg_email)
                        if success:
                            st.session_state['reg_pending_verification'] = True
                            st.session_state['reg_username_pending'] = reg_username.strip().lower()
                            st.session_state['reg_email_pending'] = reg_email.strip().lower()
                            st.session_state['reg_otp_code'] = generated_otp
                            st.session_state['reg_smtp_msg'] = smtp_msg
                            st.success("Registration initiated!")
                            force_rerun()
                        else:
                            st.error(f"Registration failed: {smtp_msg}")
                            
        st.markdown("</div>", unsafe_allow_html=True)

if st.session_state['user'] is None:
    render_login_signup()
    st.stop()



# ----------------- SIDEBAR PROFILE & TARGETS -----------------
st.sidebar.title(f"👤 User: {st.session_state['user']}")

if st.sidebar.button("🚪 Sign Out"):
    st.session_state['user'] = None
    st.query_params.pop("user", None)
    # Clear local session states
    st.session_state['active_items'] = []
    st.session_state['current_image'] = None
    st.session_state['annotated_image'] = None
    st.session_state['dietitian_feedback'] = None
    st.session_state['analyzed_image_key'] = None
    st.session_state['comp_a_file_key'] = None
    st.session_state['comp_a_items'] = []
    st.session_state['comp_a_image'] = None
    st.session_state['comp_a_feedback'] = None
    st.session_state['comp_b_file_key'] = None
    st.session_state['comp_b_items'] = []
    st.session_state['comp_b_image'] = None
    st.session_state['comp_b_feedback'] = None
    force_rerun()

st.sidebar.markdown("---")

# Use single Default profile name behind the scenes
selected_profile = "Default"

# Retrieve daily target settings
targets = db.get_targets(st.session_state['user'], selected_profile)

st.sidebar.subheader("⚙️ Configure Daily Goals")
target_cal = st.sidebar.number_input("Calories (kcal)", min_value=100.0, max_value=10000.0, value=float(targets["calories"]), step=50.0)
target_prot = st.sidebar.number_input("Protein (g)", min_value=0.0, max_value=500.0, value=float(targets["protein"]), step=5.0)
target_carb = st.sidebar.number_input("Carbs (g)", min_value=0.0, max_value=1000.0, value=float(targets["carbs"]), step=5.0)
target_fat = st.sidebar.number_input("Fat (g)", min_value=0.0, max_value=500.0, value=float(targets["fat"]), step=5.0)

if st.sidebar.button("💾 Save Settings"):
    db.save_targets(st.session_state['user'], selected_profile, target_cal, target_prot, target_fat, target_carb)
    st.sidebar.success("Targets updated!")
    force_rerun()

st.sidebar.markdown(
    """
    ---
    ### Gemini Vision AI
    Using advanced vision-language model `gemini-2.5-flash` to recognize foods, portions, and calculate macros in real-time.
    """
)


# ----------------- MAIN UI ROUTING -----------------
st.title("🍽️ Multimodal Food Nutrition Analyzer & Tracker")

tab_single, tab_compare, tab_dashboard = st.tabs([
    "🔍 Analyze Single Meal", 
    "⚖️ Compare Meals", 
    "📊 Daily Progress & History"
])

# ----------------- TAB 1: SINGLE MEAL ANALYSIS -----------------
with tab_single:
    st.markdown("Upload a photo or capture a live image of your meal to get a macronutrient and calorie breakdown.")
    
    input_method = st.radio("Choose Input Method", ["Upload Image", "Take Photo via Camera"], horizontal=True, key="single_input")
    
    image_file = None
    if input_method == "Upload Image":
        image_file = st.file_uploader("Upload meal image", type=['png', 'jpg', 'jpeg'], key="single_upload")
    else:
        image_file = st.camera_input("Take photo of your food", key="single_camera")
        
    if image_file is not None:
        file_key = f"{image_file.name}_{image_file.size}" if hasattr(image_file, 'name') else "camera_input"
        
        # Analyze ONLY if it's a new image
        if st.session_state['analyzed_image_key'] != file_key:
            image = Image.open(io.BytesIO(image_file.read())).convert('RGB')
            st.session_state['current_image'] = image
            st.session_state['analyzed_image_key'] = file_key
            st.session_state['active_items'] = []
            st.session_state['dietitian_feedback'] = None
            
            if len(predictor.rotator.keys) == 0:
                st.error("🔑 **No Gemini API Key found!** Please set the `GEMINI_API_KEY` environment variable.")
            else:
                with st.spinner('Analyzing food items with Gemini Vision AI...'):
                    try:
                        preds = predictor.predict_gemini(image)
                        active_items = []
                        for p in preds:
                            nutr = p.get('nutrition', {})
                            active_items.append({
                                'id': str(uuid.uuid4()),
                                'label': p['label'],
                                'calories': float(nutr.get('calories') or 0.0),
                                'protein_g': float(nutr.get('protein_g') or 0.0),
                                'fat_g': float(nutr.get('fat_g') or 0.0),
                                'carbs_g': float(nutr.get('carbs_g') or 0.0),
                                'portion': 1.0,
                                'bbox': p.get('bbox')
                            })
                        st.session_state['active_items'] = active_items
                        st.session_state['annotated_image'] = draw_predictions(image, preds)
                        st.session_state['dietitian_feedback'] = predictor.get_dietitian_feedback(active_items)
                    except Exception as e:
                        st.error(f"Error during Gemini analysis: {e}")
        
        # Main single-meal workspace layout
        if st.session_state['active_items']:
            # Render premium visual cards of food items
            st.subheader("🌟 Detections & Micro-Nutrients")
            
            # Glassmorphic Visual Cards Renderer
            cards_html = "<div style='display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; margin-bottom: 20px;'>"
            for item in st.session_state['active_items']:
                p = item['portion']
                cards_html += f"""<div class="food-card">
<div class="food-card-title">
<span>{item['label']}</span>
<span class="food-card-portion">{p:.1f}x portion</span>
</div>
<div class="macro-tags">
<span class="tag tag-cal">🔥 {item['calories'] * p:.0f} kcal</span>
<span class="tag tag-protein">💪 {item['protein_g'] * p:.1f}g P</span>
<span class="tag tag-carbs">🍞 {item['carbs_g'] * p:.1f}g C</span>
<span class="tag tag-fat">🥑 {item['fat_g'] * p:.1f}g F</span>
</div>
</div>"""
            cards_html += "</div>"
            st.markdown(cards_html, unsafe_allow_html=True)
            
            # Layout divided into details adjustments and visual metrics
            col_left, col_right = st.columns([1.2, 0.8])
            
            with col_left:
                st.subheader("✏️ Portion Adjuster & Item Editor")
                
                # Interactive sliders/inputs per item
                to_delete = []
                for item in st.session_state['active_items']:
                    with st.container():
                        st.markdown(f"**Edit: {item['label']}**")
                        sub_cols = st.columns([1.5, 1, 1, 1, 1, 0.5])
                        with sub_cols[0]:
                            item['label'] = st.text_input("Name", value=item['label'], key=f"lbl_{item['id']}")
                        with sub_cols[1]:
                            item['portion'] = st.slider("Portion Scale", min_value=0.1, max_value=5.0, value=float(item['portion']), step=0.1, key=f"prt_{item['id']}")
                        with sub_cols[2]:
                            item['calories'] = st.number_input("Calories (kcal)", min_value=0.0, value=float(item['calories']), key=f"cal_{item['id']}")
                        with sub_cols[3]:
                            item['protein_g'] = st.number_input("Protein (g)", min_value=0.0, value=float(item['protein_g']), key=f"prg_{item['id']}")
                        with sub_cols[4]:
                            item['carbs_g'] = st.number_input("Carbs (g)", min_value=0.0, value=float(item['carbs_g']), key=f"crg_{item['id']}")
                        with sub_cols[5]:
                            st.write("") # spacing
                            st.write("") # spacing
                            if st.button("❌", key=f"del_{item['id']}"):
                                to_delete.append(item)
                        st.markdown("---")
                
                # Execute items deletion
                if to_delete:
                    for item in to_delete:
                        st.session_state['active_items'].remove(item)
                    # Recompute annotated bounding boxes from remaining items
                    re_preds = [{'label': i['label'], 'confidence': 1.0, 'bbox': i['bbox']} for i in st.session_state['active_items'] if i.get('bbox') is not None]
                    st.session_state['annotated_image'] = draw_predictions(st.session_state['current_image'], re_preds)
                    force_rerun()
                
                # Form to manually add missing items
                with st.expander("➕ Add Custom Food Item"):
                    add_cols = st.columns([2, 1, 1, 1, 1])
                    with add_cols[0]:
                        add_label = st.text_input("Food Name", placeholder="e.g. Rice Pilaf", key="add_lbl")
                    with add_cols[1]:
                        add_cal = st.number_input("Calories", min_value=0.0, value=0.0, step=10.0, key="add_cal")
                    with add_cols[2]:
                        add_prot = st.number_input("Protein", min_value=0.0, value=0.0, step=1.0, key="add_prg")
                    with add_cols[3]:
                        add_carbs = st.number_input("Carbs", min_value=0.0, value=0.0, step=1.0, key="add_crg")
                    with add_cols[4]:
                        add_fat = st.number_input("Fat", min_value=0.0, value=0.0, step=1.0, key="add_ftg")
                        
                    if st.button("Add Item to Meal"):
                        if add_label.strip():
                            st.session_state['active_items'].append({
                                'id': str(uuid.uuid4()),
                                'label': add_label.strip(),
                                'calories': add_cal,
                                'protein_g': add_prot,
                                'fat_g': add_fat,
                                'carbs_g': add_carbs,
                                'portion': 1.0,
                                'bbox': None
                            })
                            st.success(f"Added '{add_label.strip()}' successfully!")
                            force_rerun()
                
                # Recalculate values based on changes
                tot_cal = sum(item['calories'] * item['portion'] for item in st.session_state['active_items'])
                tot_prot = sum(item['protein_g'] * item['portion'] for item in st.session_state['active_items'])
                tot_carb = sum(item['carbs_g'] * item['portion'] for item in st.session_state['active_items'])
                tot_fat = sum(item['fat_g'] * item['portion'] for item in st.session_state['active_items'])
                
                totals_dict = {
                    'calories': tot_cal,
                    'protein_g': tot_prot,
                    'carbs_g': tot_carb,
                    'fat_g': tot_fat
                }
                
                # Actions (Log and Export buttons)
                st.subheader("💾 Actions")
                meal_name_input = st.text_input("Name this Meal", value="My Meal", key="meal_name")
                
                col_act1, col_act2, col_act3 = st.columns(3)
                
                with col_act1:
                    if st.button("📝 Log Meal to DB", use_container_width=True):
                        db.log_meal(
                            st.session_state['user'],
                            selected_profile, 
                            meal_name_input, 
                            tot_cal, 
                            tot_prot, 
                            tot_fat, 
                            tot_carb, 
                            st.session_state['active_items']
                        )
                        st.success(f"Logged '{meal_name_input}' for {selected_profile}!")
                        
                with col_act2:
                    feedback_or_blank = st.session_state['dietitian_feedback'] or {"balance_rating": "N/A", "insights": [], "recommendations": []}
                    pdf_buf = pdf.generate_meal_pdf(
                        st.session_state['current_image'],
                        st.session_state['annotated_image'],
                        st.session_state['active_items'],
                        totals_dict,
                        targets,
                        feedback_or_blank,
                        selected_profile,
                        meal_name_input
                    )
                    st.download_button(
                        label="📄 Export PDF Report",
                        data=pdf_buf,
                        file_name=f"Nutrition_Report_{meal_name_input.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                with col_act3:
                    csv_items = []
                    for item in st.session_state['active_items']:
                        p = item['portion']
                        csv_items.append({
                            'Food': item['label'],
                            'Portion Factor': p,
                            'Calories (kcal)': item['calories'] * p,
                            'Protein (g)': item['protein_g'] * p,
                            'Carbs (g)': item['carbs_g'] * p,
                            'Fat (g)': item['fat_g'] * p
                        })
                    csv_data = pd.DataFrame(csv_items).to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Export CSV Log",
                        data=csv_data,
                        file_name=f"Nutrition_Log_{meal_name_input.replace(' ', '_')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            
            with col_right:
                # Detections boxes drawing
                st.subheader("📷 Detections Bounding Boxes")
                if st.session_state['annotated_image']:
                    st.image(st.session_state['annotated_image'], use_container_width=True)
                
                # Total nutrients breakdown pie chart
                st.subheader("📊 Macros Breakdown")
                st.markdown(f"**Total Calories**: `{tot_cal:.0f} kcal`")
                
                labels = ['Protein', 'Fat', 'Carbs']
                values = [tot_prot, tot_fat, tot_carb]
                if sum(values) > 0:
                    fig, ax = plt.subplots(figsize=(4, 4))
                    colors_list = ['#818cf8', '#34d399', '#fbbf24']
                    ax.pie(values, labels=labels, autopct='%1.1f%%', colors=colors_list, textprops={'color': 'white', 'weight': 'bold'})
                    fig.patch.set_alpha(0.0)
                    ax.patch.set_alpha(0.0)
                    st.pyplot(fig)
                else:
                    st.info("Log items with numeric macro values to see chart.")
                    
            # Render dietitian feedback card under workspace
            st.markdown("---")
            if st.session_state['dietitian_feedback']:
                fb = st.session_state['dietitian_feedback']
                st.markdown(
                    f"""<div class="dietitian-card">
<div class="dietitian-header">
<span class="dietitian-title">💡 AI Dietitian Coaching</span>
<span class="dietitian-rating">{fb.get('balance_rating')}</span>
</div>
<div style="margin-top: 12px; color: #e5e7eb;">
<strong style="color: #a78bfa;">Insights:</strong>
<ul style="margin: 6px 0 12px 18px; padding: 0; color: #d1d5db;">
{"".join(f"<li>{ins}</li>" for ins in fb.get('insights', []))}
</ul>
<strong style="color: #a78bfa;">Dietary Recommendations:</strong>
<ul style="margin: 6px 0 0 18px; padding: 0; color: #d1d5db;">
{"".join(f"<li>{rec}</li>" for rec in fb.get('recommendations', []))}
</ul>
</div>
</div>""",
                    unsafe_allow_html=True
                )
                
                # Option to recalculate dietitian recommendations
                if st.button("🔄 Re-evaluate Nutrition Coaching"):
                    with st.spinner("Re-analyzing nutrition profile..."):
                        st.session_state['dietitian_feedback'] = predictor.get_dietitian_feedback(st.session_state['active_items'])
                        force_rerun()
        else:
            st.info("Provide an image to begin analyzing nutrition profile.")
            

# ----------------- TAB 2: MEAL COMPARISON -----------------
with tab_compare:
    st.subheader("⚖️ Compare Meal Detections")
    st.markdown("Upload two meals side-by-side to compare overall nutrition ratios, caloric densities, and AI ratings.")
    
    col_comp_a, col_comp_b = st.columns(2)
    
    with col_comp_a:
        st.markdown("### 🟢 Meal A")
        file_a = st.file_uploader("Upload Meal A image", type=['png', 'jpg', 'jpeg'], key="comp_a_file")
        if file_a:
            key_a = f"{file_a.name}_{file_a.size}"
            if st.session_state['comp_a_file_key'] != key_a:
                img = Image.open(io.BytesIO(file_a.read())).convert('RGB')
                st.session_state['comp_a_image'] = img
                st.session_state['comp_a_file_key'] = key_a
                with st.spinner("Analyzing Meal A..."):
                    try:
                        preds = predictor.predict_gemini(img)
                        items = []
                        for p in preds:
                            nutr = p.get('nutrition', {})
                            items.append({
                                'label': p['label'],
                                'calories': float(nutr.get('calories') or 0.0),
                                'protein_g': float(nutr.get('protein_g') or 0.0),
                                'fat_g': float(nutr.get('fat_g') or 0.0),
                                'carbs_g': float(nutr.get('carbs_g') or 0.0),
                                'portion': 1.0
                            })
                        st.session_state['comp_a_items'] = items
                        st.session_state['comp_a_feedback'] = predictor.get_dietitian_feedback(items)
                    except Exception as e:
                        st.error(f"Error Meal A: {e}")
                        
            # Show Meal A Summary Card
            if st.session_state['comp_a_items']:
                st.image(st.session_state['comp_a_image'], use_container_width=True)
                items_a = st.session_state['comp_a_items']
                cal_a = sum(i['calories'] * i['portion'] for i in items_a)
                prot_a = sum(i['protein_g'] * i['portion'] for i in items_a)
                carb_a = sum(i['carbs_g'] * i['portion'] for i in items_a)
                fat_a = sum(i['fat_g'] * i['portion'] for i in items_a)
                
                st.markdown(f"**Calories**: `{cal_a:.0f} kcal`  \n**Protein**: `{prot_a:.1f}g` | **Carbs**: `{carb_a:.1f}g` | **Fat**: `{fat_a:.1f}g`")
                if st.session_state['comp_a_feedback']:
                    st.info(f"**AI Coaching Rating**: {st.session_state['comp_a_feedback'].get('balance_rating')}")

    with col_comp_b:
        st.markdown("### 🟣 Meal B")
        file_b = st.file_uploader("Upload Meal B image", type=['png', 'jpg', 'jpeg'], key="comp_b_file")
        if file_b:
            key_b = f"{file_b.name}_{file_b.size}"
            if st.session_state['comp_b_file_key'] != key_b:
                img = Image.open(io.BytesIO(file_b.read())).convert('RGB')
                st.session_state['comp_b_image'] = img
                st.session_state['comp_b_file_key'] = key_b
                with st.spinner("Analyzing Meal B..."):
                    try:
                        preds = predictor.predict_gemini(img)
                        items = []
                        for p in preds:
                            nutr = p.get('nutrition', {})
                            items.append({
                                'label': p['label'],
                                'calories': float(nutr.get('calories') or 0.0),
                                'protein_g': float(nutr.get('protein_g') or 0.0),
                                'fat_g': float(nutr.get('fat_g') or 0.0),
                                'carbs_g': float(nutr.get('carbs_g') or 0.0),
                                'portion': 1.0
                            })
                        st.session_state['comp_b_items'] = items
                        st.session_state['comp_b_feedback'] = predictor.get_dietitian_feedback(items)
                    except Exception as e:
                        st.error(f"Error Meal B: {e}")
                        
            # Show Meal B Summary Card
            if st.session_state['comp_b_items']:
                st.image(st.session_state['comp_b_image'], use_container_width=True)
                items_b = st.session_state['comp_b_items']
                cal_b = sum(i['calories'] * i['portion'] for i in items_b)
                prot_b = sum(i['protein_g'] * i['portion'] for i in items_b)
                carb_b = sum(i['carbs_g'] * i['portion'] for i in items_b)
                fat_b = sum(i['fat_g'] * i['portion'] for i in items_b)
                
                st.markdown(f"**Calories**: `{cal_b:.0f} kcal`  \n**Protein**: `{prot_b:.1f}g` | **Carbs**: `{carb_b:.1f}g` | **Fat**: `{fat_b:.1f}g`")
                if st.session_state['comp_b_feedback']:
                    st.info(f"**AI Coaching Rating**: {st.session_state['comp_b_feedback'].get('balance_rating')}")

    # Generate comparison metrics graphs if both are available
    if st.session_state['comp_a_items'] and st.session_state['comp_b_items']:
        st.markdown("---")
        st.subheader("📊 side-by-side Comparative Analytics")
        
        totals_a = {
            'calories': sum(i['calories'] * i['portion'] for i in st.session_state['comp_a_items']),
            'protein': sum(i['protein_g'] * i['portion'] for i in st.session_state['comp_a_items']),
            'carbs': sum(i['carbs_g'] * i['portion'] for i in st.session_state['comp_a_items']),
            'fat': sum(i['fat_g'] * i['portion'] for i in st.session_state['comp_a_items'])
        }
        
        totals_b = {
            'calories': sum(i['calories'] * i['portion'] for i in st.session_state['comp_b_items']),
            'protein': sum(i['protein_g'] * i['portion'] for i in st.session_state['comp_b_items']),
            'carbs': sum(i['carbs_g'] * i['portion'] for i in st.session_state['comp_b_items']),
            'fat': sum(i['fat_g'] * i['portion'] for i in st.session_state['comp_b_items'])
        }
        
        labels = ['Calories (/10 kcal)', 'Protein (g)', 'Carbs (g)', 'Fat (g)']
        vals_a = [totals_a['calories']/10.0, totals_a['protein'], totals_a['carbs'], totals_a['fat']]
        vals_b = [totals_b['calories']/10.0, totals_b['protein'], totals_b['carbs'], totals_b['fat']]
        
        x = np.arange(len(labels))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(x - width/2, vals_a, width, label='Meal A (Green)', color='#10b981')
        ax.bar(x + width/2, vals_b, width, label='Meal B (Purple)', color='#8b5cf6')
        
        ax.set_ylabel('Values', color='white', weight='bold')
        ax.set_title('Macro and Calorie Comparison (Calories scaled by 1/10 for visibility)', color='white', weight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, color='white', weight='bold')
        ax.legend()
        ax.tick_params(colors='white')
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)
        
        col_c1, col_c2 = st.columns([1.5, 1])
        with col_c1:
            st.pyplot(fig)
        with col_c2:
            # Comparative analysis table
            compare_data = {
                'Nutrient': ['Calories', 'Protein', 'Carbs', 'Fat', 'AI Rating'],
                'Meal A': [f"{totals_a['calories']:.0f} kcal", f"{totals_a['protein']:.1f}g", f"{totals_a['carbs']:.1f}g", f"{totals_a['fat']:.1f}g", st.session_state['comp_a_feedback'].get('balance_rating', 'N/A')],
                'Meal B': [f"{totals_b['calories']:.0f} kcal", f"{totals_b['protein']:.1f}g", f"{totals_b['carbs']:.1f}g", f"{totals_b['fat']:.1f}g", st.session_state['comp_b_feedback'].get('balance_rating', 'N/A')]
            }
            st.markdown("### Detailed Comparison Metrics")
            st.table(pd.DataFrame(compare_data))


# ----------------- TAB 3: DAILY PROGRESS & HISTORY -----------------
with tab_dashboard:
    st.subheader("📅 Your Daily Progress")
    
    # Custom HTML styling for progress meter
    def draw_progress(label, cur, max_val, unit):
        pct = min(100.0, (cur / max_val) * 100.0) if max_val > 0 else 0.0
        
        # Color coding: Red if exceeded, Amber if >90%, Green otherwise
        if cur > max_val:
            color_class = "bg-red"
        elif cur >= max_val * 0.9:
            color_class = "bg-amber"
        else:
            color_class = "bg-green"
            
        st.markdown(
            f"""
            <div class="progress-container">
                <div class="progress-header">
                    <span>{label}</span>
                    <span>{cur:.1f} / {max_val:.0f} {unit} ({pct:.1f}%)</span>
                </div>
                <div class="progress-track">
                    <div class="progress-fill {color_class}" style="width: {pct}%;"></div>
                </div>
            </div>
            """, 
            unsafe_allow_html=True
        )

    # Get accumulated totals and progress targets
    today_totals = db.get_today_totals(st.session_state['user'], selected_profile)
    
    col_prog_left, col_prog_right = st.columns(2)
    with col_prog_left:
        draw_progress("🔥 Calories", today_totals["calories"], targets["calories"], "kcal")
        draw_progress("💪 Protein", today_totals["protein"], targets["protein"], "g")
    with col_prog_right:
        draw_progress("🍞 Carbohydrates", today_totals["carbs"], targets["carbs"], "g")
        draw_progress("🥑 Fat", today_totals["fat"], targets["fat"], "g")
        
    st.markdown("---")
    st.subheader("📜 Meal Intake Logs History")
    
    # Retrieve logged meal records from DB
    hist = db.get_meal_history(st.session_state['user'], selected_profile)
    if not hist:
        st.info("No meals logged yet. Once you analyze a meal, use 'Log Meal' to save details here.")
    else:
        for meal in hist:
            header_str = f"🍽️ {meal['meal_name']} - {meal['timestamp']} | {meal['calories']:.0f} kcal"
            with st.expander(header_str):
                st.markdown(f"**Intake Summary**: Protein: `{meal['protein']:.1f}g` | Carbs: `{meal['carbs']:.1f}g` | Fat: `{meal['fat']:.1f}g`")
                
                # Format individual items as dataframe
                items_rows = []
                for item in meal['items']:
                    p = item.get('portion', 1.0)
                    nutr = item.get('nutrition', {}) if isinstance(item.get('nutrition'), dict) else item
                    items_rows.append({
                        'Food': item.get('label'),
                        'Portion Scale': f"{p:.1f}x",
                        'Calories (kcal)': (nutr.get('calories') or 0.0) * p,
                        'Protein (g)': (nutr.get('protein_g') or nutr.get('protein') or 0.0) * p,
                        'Carbs (g)': (nutr.get('carbs_g') or nutr.get('carbs') or 0.0) * p,
                        'Fat (g)': (nutr.get('fat_g') or nutr.get('fat') or 0.0) * p
                    })
                st.dataframe(pd.DataFrame(items_rows), use_container_width=True)
                
                # Delete meal option
                if st.button("🗑️ Delete Meal Record", key=f"del_meal_{meal['id']}"):
                    db.delete_meal(st.session_state['user'], meal['id'])
                    st.success("Meal record deleted from database!")
                    force_rerun()
