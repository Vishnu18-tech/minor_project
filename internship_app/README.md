# 🎯 InternMatch AI — Flask Application

AI-powered internship recommendation engine built with Flask + Claude AI.

## 📁 Project Structure

```
internship_app/
├── app.py                  ← Flask backend (routes + Claude API)
├── requirements.txt        ← Python dependencies
├── templates/
│   └── index.html          ← Main HTML page
└── static/
    ├── css/
    │   └── style.css       ← All styles
    └── js/
        └── main.js         ← Frontend logic
```

## 🚀 Setup & Run (Step-by-Step)

### Step 1 — Install Python
Make sure Python 3.8+ is installed:
```
python --version
```

### Step 2 — Install dependencies
Open terminal in the `internship_app` folder and run:
```
pip install flask anthropic
```

### Step 3 — Set your Anthropic API key
**Windows:**
```
set ANTHROPIC_API_KEY=your_api_key_here
```
**Mac / Linux:**
```
export ANTHROPIC_API_KEY=your_api_key_here
```
Get your API key from: https://console.anthropic.com

### Step 4 — Run the app
```
python app.py
```

### Step 5 — Open in browser
Go to: http://127.0.0.1:5000

---

## ✨ Features
- 🧠 AI profile analysis powered by Claude
- 🎯 Top 3 internship matches with reasoning
- 📈 Skill gap detection
- 🛣️ Personalized career path
- 💬 Live AI chat advisor
- 12 real-world AI/ML internships in the database

## 🔑 Getting an API Key
1. Go to https://console.anthropic.com
2. Sign up / log in
3. Click "API Keys" → "Create Key"
4. Copy and use in Step 3 above
