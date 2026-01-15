import os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import umap.umap_ as umap

# ==========================================
# [스크립트 설명]
# 벡터 DB 고급 시각화 도구 (3D & Interactive)
# 1. ChromaDB에 저장된 모든 상품 벡터를 로드합니다.
# 2. UMAP 알고리즘으로 768차원 벡터를 3차원으로 축소합니다.
# 3. Plotly를 사용하여 회전/줌이 가능한 3D 산점도 HTML을 생성합니다.
# 4. (선택) 질문을 입력하면, 질문 벡터의 위치도 함께 표시합니다.
# ==========================================

# --- 설정 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DB_PATH = os.path.join(BASE_DIR, '..', '..', 'data', 'chroma_db')
EMBEDDING_MODEL_PATH = os.path.join(BASE_DIR, '..', '..', 'models', 'snowflake-finetuned-hard')
OUTPUT_HTML_PATH = os.path.join(BASE_DIR, '..', '..', 'embedding_visualization_3d.html')

def visualize_3d(query_text=None):
    print("--- 3D 임베딩 시각화 시작 ---")

    # 1. 모델 및 DB 로드
    print(f"모델 로드 중: {EMBEDDING_MODEL_PATH}")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_PATH,
        model_kwargs={'device': 'cuda'},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    vectorstore = Chroma(
        persist_directory=CHROMA_DB_PATH,
        embedding_function=embeddings
    )
    
    # 2. 데이터 추출
    print("DB에서 데이터 추출 중...")
    data = vectorstore.get(include=['embeddings', 'metadatas', 'documents'])
    
    if data['embeddings'] is None or len(data['embeddings']) == 0:
        print("데이터가 없습니다.")
        return

    vectors = np.array(data['embeddings'])
    metadatas = data['metadatas']
    documents = data['documents']
    
    # 메타데이터 정리 (DataFrame 생성용)
    df_data = []
    for i, meta in enumerate(metadatas):
        df_data.append({
            'product_name': meta.get('product_name', 'Unknown'),
            'category': meta.get('category', 'Etc'),
            'brand': meta.get('brand', ''),
            'price': meta.get('price', 0),
            'text_preview': documents[i][:100] + "..." # 툴팁용 미리보기
        })
    
    # 3. (옵션) 질문 벡터 추가
    if query_text:
        print(f"질문 벡터 생성 중: '{query_text}'")
        query_vector = embeddings.embed_query(query_text)
        vectors = np.vstack([vectors, np.array(query_vector)])
        df_data.append({
            'product_name': f"❓ 질문: {query_text}",
            'category': 'Query',
            'brand': '-',
            'price': 0,
            'text_preview': query_text
        })
        print("질문 벡터가 데이터에 추가되었습니다.")

    # 4. 차원 축소 (UMAP 3D)
    print(f"차원 축소 중 (768 -> 3D)... 데이터 개수: {len(vectors)}")
    reducer = umap.UMAP(n_components=3, n_neighbors=15, metric='cosine', random_state=42)
    projections = reducer.fit_transform(vectors)
    
    # DataFrame 생성
    df = pd.DataFrame(df_data)
    df['x'] = projections[:, 0]
    df['y'] = projections[:, 1]
    df['z'] = projections[:, 2]

    # 5. 시각화 (Plotly 3D)
    print("3D 그래프 생성 중...")
    
    # 기본 산점도 생성
    fig = px.scatter_3d(
        df, x='x', y='y', z='z',
        color='category',
        hover_data=['product_name', 'brand', 'price'],
        title='Nyang Chatbot Embedding Space (3D)',
        opacity=0.6
    )
    
    # 점 크기 조절 (전체적으로 작게)
    fig.update_traces(marker=dict(size=3))
    
    # 질문(Query) 점이 있다면 별도로 강조
    if query_text:
        query_idx = df[df['category'] == 'Query'].index
        if not query_idx.empty:
            fig.add_trace(go.Scatter3d(
                x=df.loc[query_idx, 'x'],
                y=df.loc[query_idx, 'y'],
                z=df.loc[query_idx, 'z'],
                mode='markers',
                marker=dict(
                    size=10, 
                    color='red', 
                    symbol='diamond',
                    line=dict(width=2, color='white')
                ),
                name='Current Query',
                hoverinfo='text',
                text=f"현재 질문: {query_text}"
            ))

    # 스타일 개선
    fig.update_layout(
        margin=dict(l=0, r=0, b=0, t=40),
        scene=dict(
            xaxis=dict(showgrid=True, zeroline=False),
            yaxis=dict(showgrid=True, zeroline=False),
            zaxis=dict(showgrid=True, zeroline=False)
        )
    )
    
    # 6. 저장
    fig.write_html(OUTPUT_HTML_PATH)
    print(f"시각화 파일 저장 완료: {OUTPUT_HTML_PATH}")
    print("웹 브라우저로 해당 파일을 열어보세요!")

if __name__ == "__main__":
    # 테스트 질문을 넣어 검색 위치를 확인해볼 수 있습니다.
    test_query = "고양이 털 관리하는 빗 추천해줘"
    visualize_3d(test_query)
