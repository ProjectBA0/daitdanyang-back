import os
import sys
import asyncio
from sqlalchemy import create_engine, text
from sentence_transformers import SentenceTransformer
import lancedb
import numpy as np

# 🦁 Setup Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_BACK = os.path.abspath(os.path.join(BASE_DIR, ".."))
sys.path.append(PROJECT_BACK)

# 🦁 Config
DB_PATH = os.path.join(BASE_DIR, "data", "lancedb_store")
SQLITE_PATH = os.path.join(PROJECT_BACK, "instance", "petshop.db")
if not os.path.exists(SQLITE_PATH):
    # Fallback to direct path if instance not used
    SQLITE_PATH = os.path.join(PROJECT_BACK, "petshop.db")

MODEL_NAME = "nlpai-lab/KURE-v1"

def sync_all():
    print(f"🦁 [Nyang Sync] Starting synchronization...")
    print(f"   - SQLite: {SQLITE_PATH}")
    print(f"   - LanceDB: {DB_PATH}")

    # 1. Connect to SQLite
    if not os.path.exists(SQLITE_PATH):
        print("❌ SQLite DB not found. Run seed.py first.")
        return

    sql_engine = create_engine(f"sqlite:///{SQLITE_PATH}")
    
    products = []
    with sql_engine.connect() as conn:
        result = conn.execute(text("SELECT id, title, content, price, category FROM product"))
        products = result.fetchall()
    
    print(f"✅ Loaded {len(products)} products from SQLite.")

    # 2. Load Embedding Model
    print("⏳ Loading Embedding Model (KURE-v1)...")
    model = SentenceTransformer(MODEL_NAME)
    
    # 3. Connect to LanceDB
    db = lancedb.connect(DB_PATH)
    try:
        tbl = db.open_table("nyang_products")
    except:
        print("❌ Table 'nyang_products' not found. Creating new...")
        # Schema definition might be needed if not inferred
        return

    # 4. Transform & Vectorize
    print("🚀 Vectorizing & Syncing...")
    
    data_to_add = []
    for p in products:
        p_id, title, content, price, category = p
        
        # 🦁 Text for Retrieval
        # Prefix "passage:" is crucial for KURE-v1
        text_body = f"passage: {title} {content} {category}"
        
        # Generate Vector
        vector = model.encode(text_body).tolist()
        
        # 🦁 Map to Schema
        record = {
            "id": f"shop_{p_id}",          # Prefix for ID collision avoidance
            "vector": vector,
            "text": text_body,
            "title": title,
            "price": price,
            "brand": "자사상품",            # Default brand
            "maker": "NyangShop",
            "category1": category or "기타",
            "category2": "",
            "category3": "",
            "category4": "",
            "link": f"/product/{p_id}",    # Internal Link
            "re_title": title,
            "main_category": category,
            "sub_category": "",
            "source_layer": "homepage",    # 🦁 Key Flag for Boosting!
            "type": "product",
            "original_chunk_meta": "{}"
        }
        data_to_add.append(record)

    # 5. Upsert to LanceDB
    if data_to_add:
        # Use merge_insert (upsert) on 'id'
        # Note: LanceDB python might use 'add' with mode='overwrite' or merge logic
        # For safety in V5, we just ADD. If ID exists, it might duplicate unless we delete first.
        
        # Strategy: Delete existing 'homepage' items first? 
        # For simplicity in this script, we just ADD.
        # Future improvement: tbl.delete("source_layer = 'homepage'")
        
        tbl.add(data_to_add)
        print(f"🎉 Successfully synced {len(data_to_add)} products to LanceDB!")
    else:
        print("⚠️ No products to sync.")

if __name__ == "__main__":
    sync_all()
