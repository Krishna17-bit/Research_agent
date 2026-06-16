import streamlit as st
import pandas as pd
import json
from datetime import datetime

from app.core import database

st.set_page_config(layout="wide")

st.markdown("""
    <div style='background-color: #1e293b; padding: 20px; border-radius: 10px; margin-bottom: 25px;'>
        <h1 style='color: #f8fafc; margin: 0; font-size: 2.2rem;'>📜 Observability & Run History</h1>
        <p style='color: #94a3b8; margin: 5px 0 0 0; font-size: 1.1rem;'>
            Audit past retrieval queries, latency, tokens, cost estimates, and provide user alignment feedback.
        </p>
    </div>
""", unsafe_allow_html=True)

runs = database.get_runs()

if not runs:
    st.info("No queries logged in the system run history yet.")
else:
    # Sidebar filters
    with st.sidebar:
        st.header("Filters")
        search_q = st.text_input("Filter by Question", "")
        f_provider = st.selectbox("Filter by Provider", ["All"] + list(set(r["provider"] for r in runs)))
        f_feedback = st.selectbox("Filter by Feedback", ["All", "Thumbs Up", "Thumbs Down", "Unrated"])

    # Clear history button
    with st.expander("⚠️ System Administration"):
        st.write("Click below to clear all logged run history from the SQLite database. This does not affect index files.")
        if st.button("Reset Run History Logs", type="secondary"):
            with database.get_db_connection() as conn:
                conn.execute("DELETE FROM run_history")
                conn.commit()
            st.success("Run history logs cleared successfully!")
            st.rerun()

    filtered = []
    for r in runs:
        if search_q.lower() and search_q.lower() not in r["question"].lower():
            continue
        if f_provider != "All" and r["provider"] != f_provider:
            continue
        if f_feedback != "All":
            f_val = r["feedback"]
            if f_feedback == "Thumbs Up" and f_val != "thumbs_up":
                continue
            if f_feedback == "Thumbs Down" and f_val != "thumbs_down":
                continue
            if f_feedback == "Unrated" and f_val is not None:
                continue
        filtered.append(r)

    st.write(f"Showing **{len(filtered)}** history runs:")
    
    # Table view
    df_runs = pd.DataFrame([
        {
            "Timestamp": datetime.fromisoformat(r["timestamp"]).strftime("%Y-%m-%d %H:%M:%S"),
            "Question": r["question"],
            "Answer": r["answer"][:120] + "...",
            "Latency": f"{r['latency']:.2f}s",
            "Tokens": r["tokens"],
            "Cost": f"${r['cost']:.4f}",
            "Provider": r["provider"],
            "Feedback": "👍" if r["feedback"] == "thumbs_up" else "👎" if r["feedback"] == "thumbs_down" else "⏳"
        }
        for r in filtered
    ])
    st.dataframe(df_runs, use_container_width=True, hide_index=True)

    st.write("---")
    st.subheader("🔍 Detailed Run Inspector")
    
    # Selector for detailed inspection
    run_options = {r["id"]: f"{datetime.fromisoformat(r['timestamp']).strftime('%H:%M:%S')} - {r['question'][:60]}..." for r in filtered}
    selected_run_id = st.selectbox("Select run to inspect in-depth", options=list(run_options.keys()), format_func=lambda x: run_options[x])
    
    run_detail = next(r for r in filtered if r["id"] == selected_run_id)
    
    if run_detail:
        st.write(f"**Question:** {run_detail['question']}")
        st.write("**Answer Output:**")
        st.markdown(run_detail["answer"])
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Run ID", run_detail["id"])
        c2.metric("Latency / Performance", f"{run_detail['latency']:.3f} seconds")
        c3.metric("Cost Estimate", f"${run_detail['cost']:.5f}")
        c4.metric("Citation Coverage", run_detail["citation_quality"] or "N/A")

        # Feedback Buttons
        st.write("#### Align LLM Answering Quality")
        f_col1, f_col2, f_col3 = st.columns([1, 1, 8])
        current_fb = run_detail["feedback"]
        
        if f_col1.button("👍 Good Answer", key=f"up_{run_detail['id']}", type="primary" if current_fb == "thumbs_up" else "secondary"):
            database.update_run_feedback(run_detail["id"], "thumbs_up")
            st.success("Feedback saved as Good!")
            st.rerun()
            
        if f_col2.button("👎 Poor / Incorrect", key=f"down_{run_detail['id']}", type="primary" if current_fb == "thumbs_down" else "secondary"):
            database.update_run_feedback(run_detail["id"], "thumbs_down")
            st.warning("Feedback saved as Poor!")
            st.rerun()
            
        # Display Citations log
        st.write("#### 📌 Retrieved Citations Log")
        try:
            citations_data = json.loads(run_detail["citations_json"])
            if not citations_data:
                st.info("No citations recorded for this run.")
            else:
                for idx, cit in enumerate(citations_data):
                    st.write(f"**[{idx + 1}] {cit['source']} p.{cit['page']}** (score: {cit['score']:.3f})")
                    st.code(cit["text"])
        except Exception:
            st.info("Citation log formatting error.")
