# ruff: noqa: E402
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

# Setup page config for the main shell
st.set_page_config(
    page_title="Research PDF RAG Agent",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Render a sidebar connection status
with st.sidebar:
    st.image("https://img.icons8.com/color/96/artificial-intelligence.png", width=64)
    st.write("### Research PDF RAG Agent")
    st.caption("Grounded Academic Assistant")
    st.write("---")

# Define pages relative to this file
dashboard = st.Page("pages/dashboard.py", title="Dashboard", icon="📊", default=True)
library = st.Page("pages/library.py", title="PDF Library", icon="📚")
upload = st.Page("pages/upload.py", title="Upload Center", icon="📤")
ask = st.Page("pages/ask.py", title="Ask & Chat", icon="💬")
playground = st.Page("pages/playground.py", title="Retrieval Playground", icon="🛝")
summaries = st.Page("pages/summaries.py", title="Structured Summaries", icon="📝")
compare = st.Page("pages/compare.py", title="Paper Comparison", icon="⚖️")
gaps = st.Page("pages/gaps.py", title="Research Gap Finder", icon="🔍")
methodology = st.Page("pages/methodology.py", title="Methodology Extractor", icon="🧪")
lit_review = st.Page("pages/lit_review.py", title="Literature Review Builder", icon="📖")
notes = st.Page("pages/notes.py", title="Notes & Annotations", icon="📓")
history = st.Page("pages/history.py", title="Observability & History", icon="📜")
evals = st.Page("pages/evals.py", title="RAG Evaluation Lab", icon="🔬")
settings_page = st.Page("pages/settings.py", title="Provider Settings", icon="⚙️")

pages = {
    "Overview": [dashboard, library, upload],
    "Research Workspace": [ask, summaries, compare, gaps, methodology, lit_review],
    "Developer & Analytics": [playground, notes, history, evals, settings_page]
}

# Run navigation
pg = st.navigation(pages)
pg.run()
