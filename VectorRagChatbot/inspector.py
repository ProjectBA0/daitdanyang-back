import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from sklearn.cluster import DBSCAN
try:
    from scipy.spatial import ConvexHull
except ImportError:
    ConvexHull = None

# Page Config
st.set_page_config(page_title="🦁 Nyang Native Inspector", layout="wide", page_icon="🦁")

# --- Custom CSS ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #fff; }
    .stMetric { background-color: #262730; padding: 10px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 1. Data Loading ---
@st.cache_data(ttl=2)
def load_logs(file_path):
    possible_paths = [file_path, os.path.join("chatbot_v3", file_path), os.path.join("..", file_path), os.path.abspath(file_path)]
    target_path = next((p for p in possible_paths if os.path.exists(p)), None)
    if not target_path: return pd.DataFrame()
    
    data = []
    try:
        with open(target_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    line = line.strip()
                    if line: data.append(json.loads(line))
                except: continue
    except: return pd.DataFrame()
    
    if not data: return pd.DataFrame()
    df = pd.DataFrame(data)
    if 'timestamp' in df.columns: df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    return df

# --- 2. Main UI ---
st.title("🦁 Nyang V3 Thinking Inspector")
LOG_FILE = "core/logs/nyang_blackbox.jsonl"
df = load_logs(LOG_FILE)

if df.empty:
    st.warning(f"Waiting for logs at {os.path.join(os.path.dirname(__file__), LOG_FILE)}... 🦁")

# Sidebar
st.sidebar.header("🔍 Filters")
if 'request_id' in df.columns:
    valid_df = df[(df['request_id'] != "SYSTEM") & (df['request_id'].notnull()) & (df['request_id'] != "unknown")]
    request_ids = valid_df['request_id'].unique().tolist()
    selected_rid = st.sidebar.selectbox("Select Request Trace", request_ids[::-1] if request_ids else ["No Valid Requests"])
else:
    selected_rid = None

trace_df = df[df['request_id'] == selected_rid].copy() if selected_rid else pd.DataFrame()

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 Overview", "🧠 Thinking Process", "🔬 Vector Deep Dive"])

with tab1:
    if not df.empty:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Logs", len(df))
        col2.metric("Last Active", df['timestamp'].max().strftime("%H:%M:%S"))
        metrics = df[df.get('type') == 'METRIC']
        avg_lat = metrics['latency_ms'].mean() if not metrics.empty else 0
        col3.metric("Avg Latency", f"{avg_lat:.1f} ms")
        col4.metric("Trace ID", str(selected_rid)[:8])

with tab2:
    if not trace_df.empty:
        for _, row in trace_df.sort_values('timestamp').iterrows():
            step = str(row.get('step', 'INFO'))
            msg = row.get('message', '')
            ts = row.get('timestamp').strftime("%H:%M:%S.%f")[:-3] if pd.notnull(row.get('timestamp')) else ""
            icon = {"PERCEPTION":"🧠","TOKENIZING":"🔑","RETRIEVAL_PHASE_1":"📡","CLUSTERING":"🌌","VECTOR_RANKING":"🎯","REFLECTION":"🤔","SYNTHESIS":"✨"}.get(step, "🔹")
            with st.expander(f"{icon} [{ts}] {step} - {msg}"):
                st.json(row.to_dict())

with tab3:
    st.subheader("Advanced Topological Analysis")
    st.caption("🎯 Red Circles: Keyword Centroids | 🌈 Background Areas: Result Similarity Groups | 🟡 Points: Final Recommend Scores")
    
    ranking_row = trace_df[trace_df['step'] == 'VECTOR_RANKING']
    cluster_row = trace_df[trace_df['step'] == 'CLUSTERING']
    fts_row = trace_df[trace_df['step'] == 'RETRIEVAL_PHASE_1']
    
    # Fallback for data completeness
    if ranking_row.empty:
        ranking_row = df[df['step'] == 'VECTOR_RANKING'].sort_values('timestamp', ascending=False).head(1)
        if not ranking_row.empty:
            rid = ranking_row['request_id'].iloc[0]
            cluster_row = df[(df['step'] == 'CLUSTERING') & (df['request_id'] == rid)]
            fts_row = df[(df['step'] == 'RETRIEVAL_PHASE_1') & (df['request_id'] == rid)]

    if not ranking_row.empty:
        details = ranking_row.iloc[0].get('details', [])
        if details:
            rdf = pd.DataFrame(details)
            fig_map = go.Figure()
            
            if 'coords' in rdf.columns:
                rdf['x'] = rdf['coords'].apply(lambda c: c[0])
                rdf['y'] = rdf['coords'].apply(lambda c: c[1])
                
                # --- 🟢 Layer 1: Similar Product Micro-Clustering (Background Hulls) ---
                coords_2d = rdf[['x', 'y']].values
                # Tight eps=300 to find closely related small groups among the 50 results
                micro_clusters = DBSCAN(eps=350, min_samples=2).fit(coords_2d)
                rdf['micro_cluster'] = micro_clusters.labels_
                
                if ConvexHull:
                    unique_micros = [c for c in rdf['micro_cluster'].unique() if c != -1]
                    area_colors = px.colors.qualitative.Alphabet # More colors for multiple small groups
                    for i, mcid in enumerate(unique_micros):
                        mc_pts = rdf[rdf['micro_cluster'] == mcid][['x', 'y']].values
                        if len(mc_pts) >= 3:
                            try:
                                hull = ConvexHull(mc_pts)
                                hull_pts = mc_pts[hull.vertices]
                                hull_pts = np.vstack([hull_pts, hull_pts[0]])
                                
                                fig_map.add_trace(go.Scatter(
                                    x=hull_pts[:, 0], y=hull_pts[:, 1],
                                    fill="toself",
                                    fillcolor=area_colors[i % len(area_colors)],
                                    opacity=0.15,
                                    line=dict(width=1, color=area_colors[i % len(area_colors)], dash='dot'),
                                    name=f"Sim-Group {i+1}",
                                    hoverinfo='skip'
                                ))
                            except: pass

                # --- 🔴 Layer 2: Original Keyword Centroids (Red Targets) ---
                if not cluster_row.empty:
                    centroids = cluster_row.iloc[0].get('centroids', {})
                    if centroids:
                        for cid, info in centroids.items():
                            center = info.get('center', [0,0,0])
                            fig_map.add_trace(go.Scatter(
                                x=[center[0]], y=[center[1]],
                                mode='markers+text',
                                marker=dict(size=28, color='rgba(255, 0, 0, 0.6)', symbol='circle-open', line=dict(width=3)),
                                text=[f"🎯 C{cid}"],
                                textposition="bottom center",
                                name=f"Keyword Cluster {cid}",
                                hovertext=f"Summary: {info.get('summary', '')}"
                            ))

                # --- 🔵 Layer 3: Final Scored Product Points ---
                fig_map.add_trace(go.Scatter(
                    x=rdf['x'], y=rdf['y'],
                    mode='markers',
                    marker=dict(
                        size=rdf['final'] * 22,
                        color=rdf['final'],
                        colorscale='Viridis',
                        showscale=True,
                        colorbar=dict(title="Recommend Score", thickness=15),
                        line=dict(width=1, color='white')
                    ),
                    text=rdf['title'],
                    name="Product Recommendation",
                    hoverinfo='text',
                    hovertext="<b>" + rdf['title'] + "</b><br>Final Score: " + rdf['final'].round(4).astype(str)
                ))

            # --- 🌟 Layer 4: Query Anchor ---
            if not fts_row.empty:
                q_center = fts_row.iloc[0].get('query_center', [0,0,0])
                fig_map.add_trace(go.Scatter(
                    x=[q_center[0]], y=[q_center[1]],
                    mode='markers',
                    marker=dict(size=30, color='white', symbol='star', line=dict(width=2, color='orange')),
                    name="Query Origin"
                ))

            fig_map.update_layout(
                title="Topo-Map: Result Clusters (Areas) vs Recommendation Power (Points)",
                xaxis_title="Semantic Space X", yaxis_title="Semantic Space Y",
                height=800, template="plotly_dark",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_map, use_container_width=True)

            # --- 📊 Traditional Stacked Bar ---
            st.markdown("### 📊 Factor Breakdown (Top 50)")
            if 'history' in rdf.columns:
                h_df = pd.json_normalize(rdf['history'])
                h_df = h_df.rename(columns={'s1': 'Similarity', 's2': 'Boost', 's3': 'FinalScore', 'src_boost': 'SourceBoost'})
                rdf_full = pd.concat([rdf.drop(columns=['history']), h_df], axis=1)
                
                col_a, col_b = st.columns([2, 1])
                with col_a:
                    plot_cols = [c for c in ['Similarity', 'Boost', 'SourceBoost'] if c in rdf_full.columns]
                    fig_bar = px.bar(rdf_full.head(50), x='title', y=plot_cols, height=600)
                    fig_bar.update_layout(barmode='stack', template="plotly_dark", xaxis={'categoryorder':'total descending'})
                    st.plotly_chart(fig_bar, use_container_width=True)
                with col_b:
                    st.dataframe(rdf_full[['title', 'final'] + plot_cols].head(50), height=600)
    else:
        st.error("No spatial data found in logs.")