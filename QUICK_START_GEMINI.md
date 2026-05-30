# Quick Start with Gemini

1. Open `.env` and paste your key:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-1.5-pro
```

2. Install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

3. Run the app:

```powershell
streamlit run app\streamlit_app.py
```

4. Upload a PDF from the sidebar, click **Build / Rebuild Index**, then use any mode.

The sidebar shows the active provider. If it says `Gemini (...)`, the key is loaded correctly.
