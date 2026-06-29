# 🍽️ Multimodal Food Nutrition Analyzer (Gemini Powered)

A clean, lightweight, and highly accurate Food Nutrition Analyzer powered entirely by **Google Gemini Vision AI** (`gemini-2.5-flash`). It analyzes food images, estimates calorie and macronutrient breakdowns, detects individual food items with bounding boxes, and visualizes macro-nutrient distributions.

---

## ✨ Features

- **Advanced Multimodal Vision AI:** Detects arbitrary, complex, and mixed food items (like Indian Thalis, curries, mixed salads, and custom meals) that traditional local object detectors fail to recognize.
- **Backend API Key Rotation Pool:** Automatically manages multiple API keys in the backend. If a key expires or runs out of quota, the engine instantly rotates to a backup key in the pool, ensuring zero downtime.
- **Clean UI & Zero Configurations:** Streamlit interface is kept clean and free of API key input fields. All configurations and key management occur securely in the backend.
- **Lightweight Architecture:** Removed heavy PyTorch, torchvision, ultralytics, and transformers dependencies, allowing the application to run smoothly and boot instantly even on low-end machines.
- **API Endpoint:** Includes a FastAPI backend endpoint to run analysis programmatically.

---

## 📁 Project Structure

```
├── model/
│   └── predict.py          # Gemini Model inference & API Key Rotation logic
├── utils/
│   ├── image_processing.py # Image bounding box annotation drawing utility
│   └── __init__.py
├── assets/
│   └── logo.png            # Application logo
├── examples/
│   └── sample.jpg          # Test image for food detection
├── app_streamlit.py        # Streamlit web application frontend
├── api_fastapi.py          # FastAPI service backend endpoint
├── requirements.txt        # Project dependencies
└── README.md               # Project documentation
```

---

## 🚀 Setup & Installation

### 1. Prerequisite: Add Gemini API Keys
The application expects Gemini API keys in your environment variables or configured directly in the backend code pool. 

You can set them in your terminal session before starting the apps:
*   **PowerShell:**
    ```powershell
    $env:GEMINI_API_KEY="your_primary_key"
    $env:GEMINI_API_KEY_1="your_backup_key_1"
    ```
*   **Command Prompt:**
    ```cmd
    set GEMINI_API_KEY=your_primary_key
    set GEMINI_API_KEY_1=your_backup_key_1
    ```
*   **In-Code Fallback:** Alternatively, you can add your keys directly to the `hardcoded_keys` list inside `model/predict.py`.

### 2. Install Dependencies
```bash
# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

---

## 🏃 Running the Application

### Streamlit Web App (Frontend)
Starts the interactive user interface where you can upload food images and view visual breakdowns:
```bash
python -m streamlit run app_streamlit.py
```
Open your browser at `http://localhost:8501`.

### FastAPI Endpoint (Backend Service)
Starts the REST API backend endpoint for programmatic analysis requests:
```bash
python -m uvicorn api_fastapi:app --host 127.0.0.1 --port 8000
```
- Interactive API docs (Swagger UI) are available at: `http://127.0.0.1:8000/docs`
- Send requests to: `POST http://127.0.0.1:8000/analyze`
