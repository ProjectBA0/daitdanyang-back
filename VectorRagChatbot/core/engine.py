import os
import pickle
import numpy as np
import lancedb
import torch
from sentence_transformers import SentenceTransformer
from kiwipiepy import Kiwi
from sklearn.cluster import DBSCAN, KMeans
from collections import Counter
from loguru import logger # 🦁 Explicitly import loguru to avoid conflict with Flask logging 

from sqlalchemy import create_engine, text # 🦁 SQL Support

class NyangRagEngine:
    def __init__(self, base_dir=None):
        # 🦁 [Engine Init] Setting up paths
        curr_file = os.path.abspath(__file__)
        core_dir = os.path.dirname(curr_file) 
        chatbot_dir = os.path.dirname(core_dir) 
        back_dir = os.path.dirname(chatbot_dir) 
        
        from huggingface_hub import snapshot_download

        # 🦁 [Production] 1. Download Vector/Cache Data (Lineair/daitdanyang-db)
        hf_vec_repo = os.getenv("HF_VEC_REPO")
        if hf_vec_repo:
            try:
                print(f"🚀 [Engine Init] Downloading VECTOR Data from HF: {hf_vec_repo}")
                vec_download_path = os.path.join(chatbot_dir, "data")
                os.makedirs(vec_download_path, exist_ok=True)
                snapshot_download(
                    repo_id=hf_vec_repo,
                    repo_type="dataset",
                    local_dir=vec_download_path,
                    token=os.getenv("HF_TOKEN")
                )
                print("✅ Vector Data Download Complete!")
            except Exception as e:
                print(f"❌ Vector Data Download Failed: {e}")

        # 🦁 [Production] 2. Download SQL/General Data (Lineair/backDB)
        hf_db_repo = os.getenv("HF_DB_REPO")
        db_download_path = os.path.join(back_dir, "hf_db_storage")
        
        if hf_db_repo:
            try:
                print(f"🚀 [Engine Init] Downloading SQL Data from HF: {hf_db_repo}")
                os.makedirs(db_download_path, exist_ok=True)
                snapshot_download(
                    repo_id=hf_db_repo,
                    repo_type="dataset",
                    local_dir=db_download_path,
                    token=os.getenv("HF_TOKEN")
                )
                print("✅ SQL Data Download Complete!")
            except Exception as e:
                print(f"❌ SQL Data Download Failed: {e}")

        # 1. LanceDB & Cache Paths (Expects to be in chatbot_dir/data)
        self.data_dir = os.path.join(chatbot_dir, "data", "lancedb_store")
        self.cache_path = os.path.join(chatbot_dir, "data", "v5_atlas_cache_FINAL.pkl")
        
        # 2. SQL Database Path Strategy
        # Priority: 1. HF Downloaded -> 2. Instance Folder -> 3. Root
        potential_paths = [
            os.path.join(db_download_path, "petshop.db"),          # HF Download
            os.path.join(back_dir, "instance", "petshop.db"),      # Default Local
            os.path.join(back_dir, "petshop.db")                   # Root Local
        ]
        
        self.sql_path = None
        for p in potential_paths:
            if os.path.exists(p):
                self.sql_path = p
                print(f"🦁 [Engine Init] Selected SQL DB: {self.sql_path}")
                break
        
        if not self.sql_path:
             print(f"❌ Error: petshop.db NOT FOUND in any expected location!")
             print(f"   - Checked: {potential_paths}")

        self.db = None
        self.embed_model = None
        self.kiwi = None
        self.coords_cache = None
        self.colors_cache = None
        self.cat_id_cache = None
        self.meta_cache = []
        self.id_to_idx = {} # 🦁 Restored
        self.hierarchies = {}
        self.path_to_id = {}
        self.homepage_ids = []

    # ... (rest of the file)

    # ... (keep existing methods) ...

    # 🦁 New: SQL Keyword Search (Multi-Field Weighted Scoring)
    def search_sql(self, keywords, limit=15):
        if not keywords or not self.sql_path: 
            print(f"⚠️ SQL Search Skipped: path={self.sql_path}")
            return []
        
        try:
            sql_engine = create_engine(f"sqlite:///{self.sql_path}")
            results = []
            
            # 1. Fetch Candidates (Broad Multi-Field Search)
            conditions = []
            params = {}
            valid_kws = [k for k in keywords if len(k) > 1]
            if not valid_kws: return []

            # Fields to search
            fields = ["title", "content", "category", "sub_category"]

            for i, kw in enumerate(valid_kws):
                key = f"kw{i}"
                field_queries = [f"({f} LIKE :{key})" for f in fields]
                conditions.append(f"({' OR '.join(field_queries)})")
                params[key] = f"%{kw}%"
            
            # Combine all keyword conditions with OR to get broad candidates
            where_clause = " OR ".join(conditions)
            query = text(f"SELECT id, title, price, category, content, sub_category, pet_type, stock, review_count, img_url FROM product WHERE {where_clause} LIMIT 500")
            
            with sql_engine.connect() as conn:
                rows = conn.execute(query, params).fetchall()
                
            # 2. Advanced Weighting & Scoring
            scored_rows = []
            targets = ["고양이", "강아지", "cat", "dog", "관상어", "소동물", "조류"]
            
            for r in rows:
                score = 0
                title = (r[1] or "").lower()
                content = (r[4] or "").lower()
                category = (r[3] or "").lower()
                sub_cat = (r[5] or "").lower()
                
                for kw in valid_kws:
                    kw_lower = kw.lower()
                    
                    # 🎯 Title Match (Highest Weight)
                    if kw_lower in title:
                        score += 15.0 + (title.count(kw_lower) * 2.0)
                    
                    # 📂 Category Match (Medium Weight)
                    if kw_lower in category or kw_lower in sub_cat:
                        score += 8.0
                        
                    # 📝 Content Match (Lower Weight)
                    if kw_lower in content:
                        score += 3.0 + (content.count(kw_lower) * 0.5)
                        
                    # 🐕 Pet Type Match (Targeting Boost)
                    if kw_lower in targets:
                        score += 10.0
                
                # Bonus for Matching Multiple Different Keywords (Co-occurrence)
                matches = sum(1 for kw in valid_kws if kw.lower() in (title + content + category))
                if matches > 1:
                    score *= (1.2 ** (matches - 1)) # Multi-keyword bonus
                
                scored_rows.append((r, score))
            
            # Sort by refined score
            scored_rows.sort(key=lambda x: x[1], reverse=True)
            
            # 3. Format Top Results
            for r, score in scored_rows[:limit]:
                results.append({
                    "id": f"shop_{r[0]}",
                    "title": r[1],
                    "price": r[2],
                    "category": r[3],
                    "content": r[4],
                    "sub_category": r[5],
                    "pet_type": r[6],
                    "stock": r[7],
                    "review_count": r[8],
                    "img_url": r[9],
                    "link": f"/product/{r[0]}",
                    "score": score, # Use the weighted score
                    "source": "homepage",
                    "type": "product"
                })
            return results
        except Exception as e:
            print(f"❌ SQL Search Failed: {e}")
            return []
        self.embed_model = None
        self.kiwi = None
        self.coords_cache = None
        self.colors_cache = None
        self.cat_id_cache = None
        self.meta_cache = []
        self.id_to_idx = {}
        self.hierarchies = {}
        self.path_to_id = {}
        self.homepage_ids = []
        
    def load_resources(self):
        print("🚀 [V4 Engine] Loading Resources...")
        try:
            with open(self.cache_path, 'rb') as f:
                data = pickle.load(f)
            self.coords_cache = np.array(data['points'], dtype='<f4')
            self.colors_cache = np.array(data['colors'], dtype='u1')
            self.cat_id_cache = np.array(data['cat_indices'], dtype='<u4')
            self.meta_cache = data['metadata']
            self.hierarchies = data.get('hierarchies', {})
            self.path_to_id = data.get('path_to_id', {})
            self.homepage_ids = data.get('homepage_ids', [])
            for idx, doc_id in enumerate(data['ids']):
                self.id_to_idx[doc_id] = idx
            print(f"   - Atlas Data Loaded: {len(self.coords_cache)} points")
        except Exception as e:
            print(f"❌ Cache Load Failed: {e}")
            raise e
            
        try:
            self.db = lancedb.connect(self.data_dir)
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.embed_model = SentenceTransformer("nlpai-lab/KURE-v1", device=device)
            
            # 🦁 Kiwi Safe Loading
            try:
                self.kiwi = Kiwi()
            except Exception as e:
                print(f"⚠️ Kiwi Init Failed ({e}). Falling back to basic tokenizer.")
                self.kiwi = None
                
            print(f"   - AI Models & DB Connected on {device}")
        except Exception as e:
            print(f"❌ DB/Model Init Failed: {e}")
            raise e
        print("✅ [V4 Engine] Ready!")

    def extract_keywords(self, text):
        if not self.kiwi: return text.split()
        tokens = [t.form for t in self.kiwi.tokenize(text) if t.tag.startswith('N')]
        return tokens if tokens else text.split()

    def cluster_and_analyze(self, s1_data, request_id="unknown"):
        if not s1_data: return {}, {}
        coords = np.array([x['coord'] for x in s1_data])
        clustering = DBSCAN(eps=500, min_samples=3).fit(coords)
        labels = clustering.labels_
        unique = set(l for l in labels if l != -1)
        if len(unique) < 3:
            n_c = min(5, len(coords))
            labels = KMeans(n_clusters=n_c, n_init='auto').fit_predict(coords) if n_c > 0 else np.array([])
        
        counts = Counter(labels)
        top_clusters = [c[0] for c in counts.most_common(5) if c[0] != -1]
        centroids, doc_cluster_map = {}, {}
        cluster_docs = {cid: [] for cid in top_clusters}
        
        for i, item in enumerate(s1_data):
            lbl = labels[i]
            if lbl in top_clusters:
                doc_cluster_map[item['id']] = lbl
                if item['id'] in self.id_to_idx:
                    idx = self.id_to_idx[item['id']]
                    cluster_docs[lbl].append(self.meta_cache[idx]['title'])

        for cid in top_clusters:
            mask = (labels == cid)
            center = np.mean(coords[mask], axis=0).tolist()
            size = int(np.sum(mask))
            keywords = self.extract_keywords(" ".join(cluster_docs[cid]))
            summary = ", ".join([k[0] for k in Counter(keywords).most_common(3)])
            centroids[int(cid)] = {"center": center, "size": size, "summary": summary}
            
        logger.bind(request_id=request_id, payload={"step": "CLUSTERING", "s1_count": len(coords), "clusters": len(unique), "centroids": centroids}).info("Clustering Complete")
        return centroids, doc_cluster_map

    def search_hybrid(self, query, top_k=50, request_id="unknown"):
        try:
            tokens = self.extract_keywords(query)
            if not tokens: tokens = ["*"]
            logger.bind(request_id=request_id, payload={"step": "TOKENIZING", "details": {"tokens": tokens, "original_query": query}}).debug("Tokens extracted")
            
            tbl = self.db.open_table("nyang_products")
            s1_raw = tbl.search(" OR ".join(tokens), query_type="fts").limit(500).to_list()
            s1_data = []
            for r in s1_raw:
                idx = self.id_to_idx.get(r['id'])
                if idx is not None:
                    s1_data.append({"id": r['id'], "coord": self.coords_cache[idx].tolist()})
            
            query_center = np.mean(np.array([x['coord'] for x in s1_data]), axis=0).tolist() if s1_data else [0,0,0]
            logger.bind(request_id=request_id, payload={"step": "RETRIEVAL_PHASE_1", "query_center": query_center, "details": {"candidate_count": len(s1_data)}}).info("FTS Candidate Extraction")

            centroids, doc_cluster_map = self.cluster_and_analyze(s1_data, request_id)
            max_log_size = max([np.log1p(c['size']) for c in centroids.values()] + [1.0])
            
            emb = self.embed_model.encode([f"query: {query}"], normalize_embeddings=True).tolist()[0]
            vec_results = tbl.search(emb).limit(top_k).to_list()
            
            ranked_nodes = []
            for res in vec_results:
                idx = self.id_to_idx.get(res['id'])
                if idx is not None:
                    meta = self.meta_cache[idx]
                    node_coord = self.coords_cache[idx].tolist()
                    base_sim = max(0.0, 1.0 - res['_distance'] / 2.0)
                    boost, cluster_id = 1.0, -1
                    for cid, info in centroids.items():
                        if np.linalg.norm(np.array(node_coord) - np.array(info['center'])) < 600:
                            boost = 1.1 + 0.2 * (np.log1p(info['size']) / max_log_size)
                            cluster_id = cid
                            break
                    # 🦁 Fix: Check 'source_layer' (schema) and Boost 3.0
                    is_homepage = meta.get('source_layer') == 'homepage' or meta.get('source') == 'homepage'
                    src_boost = 3.0 if is_homepage else 1.0
                    
                    final_score = base_sim * boost * src_boost
                    ranked_nodes.append({
                        "idx": int(idx), "id": res['id'], "title": meta['title'], "price": meta.get('price', 0), "brand": meta.get('brand', ''),
                        "score": float(final_score), "type": meta.get('type','product'), "source": meta.get('source','crawled'), "coords": node_coord,
                        "cluster_id": cluster_id, "chain": [centroids[cluster_id]['center'], node_coord] if cluster_id != -1 else [node_coord, node_coord],
                        "history": {"s1": float(base_sim), "s2": float(boost), "s3": float(final_score), "src_boost": float(src_boost)},
                        "status": "PASS"
                    })
            
            ranked_nodes.sort(key=lambda x: x['score'], reverse=True)
            vec_log_data = [{"title": n['title'], "final": float(n['score']), "coords": n['coords'], "cluster_id": int(n['cluster_id']), "history": n['history']} for n in ranked_nodes]
            logger.bind(request_id=request_id, payload={"step": "VECTOR_RANKING", "count": len(vec_log_data), "details": vec_log_data}).debug("Ranking Complete")
            return tokens, s1_data, centroids, ranked_nodes
        except Exception as e:
            logger.error(f"❌ search_hybrid failed: {e}")
            return [], [], {}, []

    def search_refined(self, queries, request_id="unknown"):
        results = []
        try:
            tbl = self.db.open_table("nyang_products")
            for q in queries:
                emb = self.embed_model.encode([f"query: {q}"], normalize_embeddings=True).tolist()[0]
                try: results.append(tbl.search(emb).limit(5).to_list())
                except: pass
            logger.bind(request_id=request_id, payload={"step": "REFLECTION_SEARCH", "details": {"queries": queries, "results_count": len(results)}}).info("Refined Search Complete")
        except Exception as e: logger.error(f"Error in refined search: {e}")
        return results

    def rrf_merge(self, list1, list2_group, k=60):
        scores = Counter()
        for rank, item in enumerate(list1): scores[item['id']] += 1.0 / (k + rank + 1)
        for l in list2_group:
            for rank, item in enumerate(l): scores[item['id']] += 1.0 / (k + rank + 1)
        final_nodes, seen = [], set()
        for doc_id, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            if len(final_nodes) >= 5: break
            idx = self.id_to_idx.get(doc_id)
            if idx is not None and doc_id not in seen:
                meta = self.meta_cache[idx]
                final_nodes.append({"idx": int(idx), "title": meta['title'], "price": meta.get('price', 0), "brand": meta.get('brand', ''), "score": float(scores[doc_id]), "source": meta.get('source','crawled'), "type": meta.get('type','product'), "coords": self.coords_cache[idx].tolist()})
                seen.add(doc_id)
        return final_nodes
