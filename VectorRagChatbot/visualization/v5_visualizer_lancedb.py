import os
import lancedb
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sklearn.decomposition import PCA
from sentence_transformers import SentenceTransformer
import torch
import uvicorn
import pyarrow as pa

# [Nyang V5 3D Visualizer Server - LanceDB Edition] 🦁🌌
# LanceDB 기반의 지식 공간을 3D로 실시간 투영합니다.

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 설정
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "lancedb_store")
TABLE_NAME = "nyang_products"
MODEL_NAME = "nlpai-lab/KURE-v1"
SAMPLE_SIZE = 10000  # 성능을 위해 조정 가능

class NyangVisualizer:
    def __init__(self):
        print("⚙️  Loading Model and DB for Visualization (LanceDB)...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(MODEL_NAME, device=self.device)
        if self.device == "cuda": self.model.half()
        
        # LanceDB 연결
        self.db = lancedb.connect(DB_PATH)
        try:
            self.table = self.db.open_table(TABLE_NAME)
        except Exception as e:
            print(f"❌ Failed to open table '{TABLE_NAME}': {e}")
            print(f"Available tables: {self.db.list_tables()}")
            raise e
        
        # 1. 고정된 배경 데이터(Starfield) 준비
        print(f"🌌 Fetching {SAMPLE_SIZE} samples from LanceDB...")
        # LanceDB는 샘플링을 위해 limit 사용
        df = self.table.search().limit(SAMPLE_SIZE).to_pandas()
        
        # 데이터 추출 (LanceDB 스키마에 맞춤)
        # vector 컬럼은 보통 'vector'임
        self.base_embeddings = np.stack(df['vector'].values) 
        self.base_docs = df['text'].tolist()
        # 메타데이터는 나머지 컬럼들
        self.base_metas = df.drop(columns=['vector', 'text']).to_dict(orient='records')
        
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

# 전역 인스턴스 생성
try:
    viz = NyangVisualizer()
except Exception as e:
    print(f"🚨 Visualizer Init Failed: {e}")
    viz = None

@app.get("/data")
def get_data(query: str = ""):
    if not viz:
        return {"error": "Visualizer not initialized"}

    # 배경 포인트 데이터
    points = []
    for i in range(len(viz.base_3d)):
        meta = viz.base_metas[i]
        
        # [Nyang V5] 메타데이터 추출 로직 (LanceDB 스키마 대응)
        category = meta.get("category", "기타")
        title = meta.get("title", "Info")

        points.append({
            "x": float(viz.base_3d[i][0]),
            "y": float(viz.base_3d[i][1]),
            "z": float(viz.base_3d[i][2]),
            "text": viz.base_docs[i][:50] + "...", 
            "title": title,
            "category": category, 
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
    print(f"🚀 Starting Visualizer on port 8002...")
    uvicorn.run(app, host="0.0.0.0", port=8002)
