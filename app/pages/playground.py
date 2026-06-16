import streamlit as st
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

from app.core import database
from app.core.config import settings
from app.core.retriever import HybridRetriever, tokenize
from app.core.llm import generate_answer

st.set_page_config(layout="wide")

st.markdown("""
    <div style='background-color: #1e293b; padding: 20px; border-radius: 10px; margin-bottom: 25px;'>
        <h1 style='color: #f8fafc; margin: 0; font-size: 2.2rem;'>🛝 Retrieval Playground & Prompt Debugger</h1>
        <p style='color: #94a3b8; margin: 5px 0 0 0; font-size: 1.1rem;'>
            Test queries, analyze vector similarities, inspect lexical BM25 matching, and audit the raw context prompts sent to the LLM.
        </p>
    </div>
""", unsafe_allow_html=True)

# Select papers to test
docs = database.get_all_documents()
doc_options = {d["id"]: f"{d['title'] or d['file_name']} ({d['year'] or 'N/A'})" for d in docs if d["status"] == "indexed"}

if not doc_options:
    st.warning("No indexed papers found. Upload papers first!")
else:
    selected_docs = st.multiselect("Select papers to search over", options=list(doc_options.keys()), format_func=lambda x: doc_options[x])
    doc_filter_ids = selected_docs if selected_docs else list(doc_options.keys())

    q_input = st.text_input("Enter Search / RAG query", placeholder="e.g. baseline model parameters")
    
    col1, col2 = st.columns(2)
    with col1:
        top_k = st.slider("Top-K Chunks to Retrieve", 2, 25, settings.top_k)
        sim_threshold = st.slider("Similarity Limit (Threshold)", 0.0, 1.0, settings.similarity_threshold, step=0.05)
    with col2:
        semantic_weight = st.slider("Semantic Vector Weight", 0.0, 1.0, 0.62, step=0.05)
        bm25_weight = 1.0 - semantic_weight
        st.write(f"Lexical BM25 Weight (Auto-calculated): **{bm25_weight:.2f}**")

    if q_input.strip():
        retriever = HybridRetriever()
        
        # load subset
        if not retriever.load_active_index(doc_filter_ids):
            st.error("No valid chunks loaded for selected files.")
        else:
            # Re-implement search logic locally to display granular metrics
            q_emb = normalize(retriever.model.encode([q_input], convert_to_numpy=True))
            vec_scores = cosine_similarity(q_emb, retriever.embeddings)[0]
            
            bm25_raw = np.array(retriever.bm25.get_scores(tokenize(q_input)), dtype=float)
            bm25_scores = bm25_raw / (bm25_raw.max() + 1e-9) if bm25_raw.size else bm25_raw
            
            hybrid = semantic_weight * vec_scores + bm25_weight * bm25_scores
            
            # Filter and sort
            valid_indices = [idx for idx in np.argsort(hybrid)[::-1] if hybrid[idx] >= sim_threshold]
            idxs = valid_indices[:top_k]
            
            # Print stats
            st.subheader("📊 Retrieval Analysis")
            st.write(f"Total potential chunks in active index: **{len(retriever.chunks)}**")
            st.write(f"Chunks passing similarity threshold ({sim_threshold}): **{len(valid_indices)}**")
            
            if not idxs:
                st.warning("No chunks passed the similarity threshold for this query. Try lowering the threshold.")
            else:
                rows = []
                evidence_list = []
                for i in idxs:
                    c = retriever.chunks[i]
                    # Check matching keywords
                    q_toks = set(tokenize(q_input))
                    c_toks = set(tokenize(c.text))
                    overlapping_words = q_toks.intersection(c_toks)
                    
                    rows.append({
                        "Source Document": c.source,
                        "Page": c.page,
                        "Combined Score": f"{hybrid[i]:.3f}",
                        "Semantic Score": f"{vec_scores[i]:.3f}",
                        "BM25 Score": f"{bm25_scores[i]:.3f}",
                        "Matching Keywords": ", ".join(overlapping_words) or "None",
                        "Chunk Text Preview": c.text[:220].replace("\n", " ") + "..."
                    })
                    
                    from app.core.schemas import SourceEvidence
                    evidence_list.append(SourceEvidence(
                        chunk_id=c.chunk_id,
                        source=c.source,
                        page=c.page,
                        score=float(hybrid[i]),
                        text=c.text
                    ))
                    
                df_results = pd.DataFrame(rows)
                st.dataframe(df_results, use_container_width=True)

                # Show Prompt Preview
                st.subheader("📝 Raw Prompt Preview")
                system_p = "SYSTEM PROMPT\n=============\nYou are a scientific research assistant..."
                evidence_block = "\n\n".join(
                    f"[{i + 1}] Source: {e.source}, page {e.page}, score {e.score:.3f}\n{e.text}"
                    for i, e in enumerate(evidence_list)
                )
                user_p = f"Question:\n{q_input}\n\nEvidence:\n{evidence_block}\n\nWrite a research-grade answer..."
                
                with st.expander("Show complete prompt sent to LLM provider"):
                    st.text_area("System Instructions", system_p, height=80, disabled=True)
                    st.text_area("Context Prompt", user_p, height=250, disabled=True)

                # Generate Answer right here
                if st.button("Generate Answer from this Prompt", type="primary"):
                    with st.spinner("Calling active LLM provider..."):
                        answer, used_llm, warnings = generate_answer(q_input, evidence_list)
                    st.subheader("💡 Generated Answer")
                    st.markdown(answer)
                    if warnings:
                        st.warning("\n".join(warnings))
