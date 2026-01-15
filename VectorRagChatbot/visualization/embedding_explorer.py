import streamlit as st
import pandas as pd
import numpy as np
import pickle
import plotly.express as px
import plotly.graph_objects as go
import os
import json
import torch
from langchain_huggingface import HuggingFaceEmbeddings
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline, BitsAndBytesConfig
import chromadb

# 경로 설정
import sys
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(BASE_DIR)
from scripts.utils.config import EMBEDDING_PKL_PATH, VECTOR_DB_DIR, MODEL_LLM_LATEST

st.set_page_config(layout="wide", page_title="Nyang Smart Retriever Debugger")

# --- Resource Loading ---
@st.cache_resource
def load_viz_data():
    if not os.path.exists(EMBEDDING_PKL_PATH):
        return None
    with open(EMBEDDING_PKL_PATH, 'rb') as f:
        return pickle.load(f)

@st.cache_resource
def load_models(embedding_model_path):
    # 1. Embedding Model
    embeddings = HuggingFaceEmbeddings(
        model_name=embedding_model_path,
        model_kwargs={'device': 'cuda'},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    # 2. LLM (Query Parser) - 4bit Quantization
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_LLM_LATEST)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_LLM_LATEST, quantization_config=bnb_config, device_map="auto"
    )
    llm_pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=128)
    
    return embeddings, llm_pipe

# --- Core Logic ---
def parse_query_with_llm(pipe, query):
    """LLM을 사용하여 자연어 질문을 구조화된 검색 조건으로 변환"""
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
너는 검색 쿼리 분석기다. 사용자 질문에서 브랜드, 카테고리, 가격 조건을 추출하여 JSON으로 출력하라.
가격은 숫자만, 없는 조건은 null로 표기해라.

예시: "3만원대 로얄캐닌 사료"
출력: {{"brand": "로얄캐닌", "category": "사료", "price_min": 30000, "price_max": 40000, "query": "사료 추천"}}
<|eot_id|><|start_header_id|>user<|end_header_id|>
"{query}"
<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""
    try:
        outputs = pipe(prompt, do_sample=False)
        generated = outputs[0]['generated_text'].split("assistant<|end_header_id|>")[-1].strip()
        # JSON 부분만 추출 시도
        start = generated.find('{')
        end = generated.rfind('}') + 1
        return json.loads(generated[start:end])
    except:
        return {"brand": None, "category": None, "price_min": None, "price_max": None, "query": query}

def main():
    st.title("🦁 Nyang Smart Retriever (Thinking Process)")
    
    # 데이터 로드
    viz_data = load_viz_data()
    if not viz_data:
        st.error("시각화 데이터가 없습니다.")
        return
        
    df = viz_data['dataframe']
    model_name = "V2" # 최신 모델 고정
    reducer = viz_data['reducers'][model_name]
    model_path = viz_data['models'][model_name]
    
    x_col, y_col, z_col = f'x_{model_name}', f'y_{model_name}', f'z_{model_name}'

    # 모델 로드 (최초 1회만 실행됨)
    with st.spinner("AI 모델 로딩 중... (VRAM 확보)"):
        embeddings, llm_pipe = load_models(model_path)

    # --- UI ---
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("1. 질문 입력")
        query = st.text_input("질문", "3만원대 로얄캐닌 고양이 사료 보여줘")
        
        if query:
            st.header("2. AI 분석 (Thinking)")
            # LLM 분석 수행
            search_filter = parse_query_with_llm(llm_pipe, query)
            st.json(search_filter)
            
            # 필터 조건 구성
            where_clause = {}
            if search_filter.get('brand'):
                # 부분 일치를 지원하지 않으므로, 데이터 정제가 중요함. 
                # 여기서는 데모를 위해 '$eq' 사용
                where_clause['brand'] = search_filter['brand']
            
            # ChromaDB 연결
            client = chromadb.PersistentClient(path=VECTOR_DB_DIR)
            collection = client.get_collection("product_search")
            
            # 임베딩
            q_vec = embeddings.embed_query(search_filter.get('query', query))
            
            # 검색 수행 (필터 적용)
            try:
                results = collection.query(
                    query_embeddings=[q_vec],
                    n_results=5,
                    where=where_clause if where_clause else None
                    # 가격 범위 필터는 ChromaDB의 복합 where 조건이 까다로워 후처리로 하는 게 나을 수 있음
                )
                
                st.header("3. 검색 결과 (Filtered)")
                if results['ids']:
                    res_df = pd.DataFrame({
                        '상품명': [m['product_name'] for m in results['metadatas'][0]],
                        '브랜드': [m['brand'] for m in results['metadatas'][0]],
                        '가격': [m['price'] for m in results['metadatas'][0]],
                        '거리': results['distances'][0]
                    })
                    st.table(res_df)
                else:
                    st.warning("조건에 맞는 상품이 없습니다.")
                    
            except Exception as e:
                st.error(f"검색 오류: {e}")

    with col2:
        st.header("4. 시각화 (Embedding Space)")
        
        fig = px.scatter_3d(
            df, x=x_col, y=y_col, z=z_col,
            color='category',
            hover_data=['product_name', 'price', 'brand'],
            opacity=0.3, height=800,
            title="Search Debugger View"
        )
        fig.update_traces(marker=dict(size=3))
        
        if query:
            # 질문 위치
            q_proj = reducer.transform(np.array(q_vec).reshape(1, -1))
            fig.add_trace(go.Scatter3d(
                x=[q_proj[0, 0]], y=[q_proj[0, 1]], z=[q_proj[0, 2]],
                mode='markers+text',
                marker=dict(size=15, color='red', symbol='diamond'),
                name='Query Intent'
            ))
            
            # 검색된 결과 강조
            if 'results' in locals() and results['ids']:
                found_ids = results['ids'][0] # ID 리스트
                # ID가 매핑되지 않아 시각화가 어려울 수 있음 (prepare_data에서 ID 저장 필요)
                # 여기서는 이름으로 매칭 시도 (불완전할 수 있음)
                found_names = [m['product_name'] for m in results['metadatas'][0]]
                found_df = df[df['product_name'].isin(found_names)]
                
                fig.add_trace(go.Scatter3d(
                    x=found_df[x_col], y=found_df[y_col], z=found_df[z_col],
                    mode='markers',
                    marker=dict(size=8, color='yellow', line=dict(width=2, color='black')),
                    name='Filtered Results'
                ))

        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()