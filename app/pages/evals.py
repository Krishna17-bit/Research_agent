import streamlit as st
import pandas as pd
import json
from datetime import datetime

from app.core import database
from app.core.agent import ResearchAgent
from app.core.config import settings
from app.core.verifier import verify_citations

st.set_page_config(layout="wide")

st.markdown("""
    <div style='background-color: #1e293b; padding: 20px; border-radius: 10px; margin-bottom: 25px;'>
        <h1 style='color: #f8fafc; margin: 0; font-size: 2.2rem;'>🔬 RAG Evaluation Lab</h1>
        <p style='color: #94a3b8; margin: 5px 0 0 0; font-size: 1.1rem;'>
            Run diagnostic evaluations. Test answer faithfulness, term coverage, retrieval scores, and citation grounding.
        </p>
    </div>
""", unsafe_allow_html=True)

# Load evaluation dataset
EVAL_FILE = Path("app/evals/eval_questions.json")
eval_dataset = []
if EVAL_FILE.exists():
    try:
        eval_dataset = json.loads(EVAL_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass

st.subheader("📋 Evaluation Test Dataset")
st.write(f"The lab has loaded **{len(eval_dataset)}** test questions with expected scientific terms from `app/evals/eval_questions.json`:")

df_dataset = pd.DataFrame([
    {
        "Question": item["question"],
        "Expected Terms (Coverage Indicators)": ", ".join(item["expected_terms"])
    }
    for item in eval_dataset
])
st.dataframe(df_dataset, use_container_width=True, hide_index=True)

st.write("---")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🚀 Run Evaluation Suite")
    st.write(f"Evaluate using active provider settings: **{settings.llm_provider.upper()}** (Mock: {settings.mock_mode})")
    
    if st.button("Execute Evaluation Runs", type="primary"):
        if not eval_dataset:
            st.error("No test questions loaded.")
        else:
            results = []
            pass_count = 0
            fail_count = 0
            grounding_sum = 0.0
            term_coverage_sum = 0.0
            retrieval_score_sum = 0.0
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            agent = ResearchAgent()
            
            for idx, item in enumerate(eval_dataset):
                status_text.text(f"Running query {idx + 1}/{len(eval_dataset)}: '{item['question'][:40]}...'")
                
                # Ask Agent
                res = agent.ask(item["question"])
                answer_lower = res.answer.lower()
                
                # 1. Term Coverage Faithfulness
                hits = sum(1 for term in item["expected_terms"] if term.lower() in answer_lower)
                term_cov = hits / len(item["expected_terms"])
                term_coverage_sum += term_cov
                
                # 2. Citation Accuracy Grounding
                verify_res = verify_citations(res.answer, res.citations)
                g_score = verify_res["grounding_score"]
                grounding_sum += g_score
                
                # 3. Retrieval Score
                ret_score = res.citations[0].score if res.citations else 0.0
                retrieval_score_sum += ret_score
                
                # Define pass criteria (say, term coverage >= 50% and grounding >= 70%)
                is_passed = term_cov >= 0.5 and g_score >= 0.7
                if is_passed:
                    pass_count += 1
                else:
                    fail_count += 1
                    
                results.append({
                    "question": item["question"],
                    "answer": res.answer,
                    "term_coverage": term_cov,
                    "grounding_score": g_score,
                    "retrieval_score": ret_score,
                    "passed": is_passed
                })
                
                progress_bar.progress((idx + 1) / len(eval_dataset))
                
            progress_bar.empty()
            status_text.empty()
            
            # Aggregate stats
            avg_term_cov = term_coverage_sum / len(eval_dataset)
            avg_grounding = grounding_sum / len(eval_dataset)
            avg_retrieval = retrieval_score_sum / len(eval_dataset)
            overall_score = (avg_term_cov + avg_grounding + avg_retrieval) / 3.0
            
            # Save eval run to SQLite
            database.add_eval_run(
                timestamp=datetime.now().isoformat(),
                dataset="Standard scientific-rag-demo",
                provider=settings.llm_provider.upper(),
                model="mock" if settings.mock_mode else getattr(settings, f"{settings.llm_provider}_model", "default"),
                score=overall_score,
                pass_count=pass_count,
                fail_count=fail_count,
                results=results
            )
            
            st.success("Evaluation suite execution complete!")
            st.rerun()

with col2:
    st.subheader("📊 Evaluation History & Benchmark")
    evals_history = database.get_eval_runs()
    
    if not evals_history:
        st.info("No benchmark history runs logged in the database yet.")
    else:
        # Convert evals to dataframe
        df_hist = pd.DataFrame([
            {
                "Timestamp": datetime.fromisoformat(eh["timestamp"]).strftime("%Y-%m-%d %H:%M"),
                "Dataset": eh["dataset"],
                "Model Setup": f"{eh['provider']} ({eh['model']})",
                "Overall Score": f"{eh['score']:.1%}",
                "Passed": eh["pass_count"],
                "Failed": eh["fail_count"]
            }
            for eh in evals_history
        ])
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
        
        # Details of the latest evaluation run
        st.write("### 🔍 Latest Eval Run Details")
        latest = evals_history[0]
        results_data = json.loads(latest["results_json"])
        
        # Display aggregated scores
        c1, c2, c3 = st.columns(3)
        c1.metric("Eval Date", datetime.fromisoformat(latest["timestamp"]).strftime("%Y-%m-%d %H:%M"))
        c2.metric("Pass Rate", f"{(latest['pass_count'] / (latest['pass_count'] + latest['fail_count'])):.1%}")
        c3.metric("RAG Score", f"{latest['score']:.1%}")
        
        for idx, r in enumerate(results_data):
            status_symbol = "🟢 PASS" if r["passed"] else "🔴 FAIL"
            with st.expander(f"Question [{idx + 1}]: {r['question'][:60]}... ({status_symbol})"):
                st.write(f"**Answer:** {r['answer']}")
                st.write(f"- Term Faithfulness Coverage: **{r['term_coverage']:.1%}**")
                st.write(f"- Citation Grounding Accuracy: **{r['grounding_score']:.1%}**")
                st.write(f"- Retrieval Confidence Score: **{r['retrieval_score']:.3f}**")
