import os
import json
import chromadb
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sklearn.decomposition import PCA
from sentence_transformers import SentenceTransformer
import torch
import uvicorn

# [Nyang V4 3D Visualizer Server] 🦁🌌
# 34.6만 개의 지식 공간을 3D로 실시간 투영합니다.

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 설정
DB_PATH = r"v4_advanced_rag/data/vector_db_v4"
MODEL_NAME = "nlpai-lab/KURE-v1"
COLLECTION_NAME = "nyang_ultimate_knowledge"
SAMPLE_SIZE = 50000 # 지배인님의 요청대로 대폭 확대 (브라우저 한계 고려)

class NyangVisualizer:
    def __init__(self):
        print("⚙️  Loading Model and DB for Visualization...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(MODEL_NAME, device=self.device)
        if self.device == "cuda": self.model.half()
        
        self.client = chromadb.PersistentClient(path=DB_PATH)
        self.collection = self.client.get_collection(name=COLLECTION_NAME)
        
        # 1. 고정된 배경 데이터(Starfield) 준비
        print(f"🌌 Fetching {SAMPLE_SIZE} samples from DB...")
        results = self.collection.get(include=['embeddings', 'metadatas', 'documents'], limit=SAMPLE_SIZE)
        
        self.base_embeddings = np.array(results['embeddings'])
        self.base_metas = results['metadatas']
        self.base_docs = results['documents']
        
        # 2. PCA 모델 학습 (1024D -> 3D)
        print("🧠 Fitting PCA Model...")
        self.pca = PCA(n_components=3)
        self.base_3d = self.pca.fit_transform(self.base_embeddings)
        print("✅ Visualization Engine Ready!")

    def get_query_3d(self, query_text):
        # 쿼리를 같은 3D 공간으로 투영
        prefixed_query = f"query: {query_text}"
        query_vec = self.model.encode([prefixed_query], normalize_embeddings=True)
        query_3d = self.pca.transform(query_vec)
        return query_3d[0].tolist()

viz = NyangVisualizer()

@app.get("/data")
def get_data(query: str = ""):
    # 배경 포인트 데이터
    points = []
    for i in range(len(viz.base_3d)):
        meta = viz.base_metas[i]
        
        # [Nyang V4] 다형성 메타데이터 추출 로직 🦁
        # 1순위: 상품 대분류 (가장 중요)
        category = meta.get("category_depth1") or meta.get("main_category")
        
        # 2순위: 지식 출처 (QA 데이터 등)
        if not category:
            source = meta.get("source")
            if source:
                category = f"지식_{source}" # 예: 지식_QA
        
        # 3순위: 데이터 타입
        if not category:
            dtype = meta.get("type")
            if dtype:
                category = f"타입_{dtype}"

        # 4순위: 최후의 수단
        if not category:
            category = "기타"

        points.append({
            "x": float(viz.base_3d[i][0]),
            "y": float(viz.base_3d[i][1]),
            "z": float(viz.base_3d[i][2]),
            "text": viz.base_docs[i][:50] + "...", # 텍스트 미리보기
            "title": meta.get("title", "Info"),
            "category": category, # 색상 및 필터링 핵심 키
            "type": "database"
        })
    
    # 쿼리 포인트 데이터 (있는 경우)
    query_point = None
    if query:
        q_3d = viz.get_query_3d(query)
        query_point = {
            "x": q_3d[0], "y": q_3d[1], "z": q_3d[2],
            "text": query, "title": "Current Query", "category": "Query", "type": "query"
        }
        
    return {"points": points, "query_point": query_point}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
