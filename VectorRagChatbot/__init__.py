import os
import sys
from flask import Blueprint, current_app

# Add core directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.engine import NyangRagEngine
from core.brain import BrainHub, NyangPersona

chatbot_bp = Blueprint('vector_rag_chatbot', __name__, url_prefix='/api/chat')

def init_chatbot_engine(app):
    """
    Initializes the RAG Engine and Brain using localized data within the module.
    This makes the chatbot module fully independent.
    """
    with app.app_context():
        # 🦁 V5 Integration: Use localized data folder
        base_path = os.path.dirname(os.path.abspath(__file__))
        local_data = os.path.join(base_path, "data")
        
        print(f"🦁 [Nyang V5] Initializing Engine with Localized Data: {local_data}")
        
        try:
            # Initialize Engine with manual data path injection
            engine = NyangRagEngine(base_dir=None) 
            # Overwrite data paths to point to the local 'data' folder
            engine.data_dir = os.path.join(local_data, "lancedb_store")
            engine.cache_path = os.path.join(local_data, "v5_atlas_cache_FINAL.pkl")
            
            # 🦁 Force SQL Path Injection
            # PROJECT-main/back/VectorRagChatbot/__init__.py -> .. -> back -> instance/petshop.db
            sql_db_path = os.path.abspath(os.path.join(base_path, "..", "instance", "petshop.db"))
            engine.sql_path = sql_db_path
            print(f"🦁 [Init] Injected SQL Path: {engine.sql_path} (Exists: {os.path.exists(engine.sql_path)})")
            
            # Load Resources
            engine.load_resources()
            
            # Initialize Brain
            brain = BrainHub(NyangPersona())
            
            # Attach to App Extensions
            app.extensions['nyang_engine'] = engine
            app.extensions['nyang_brain'] = brain
            print("🦁 [Nyang V5] Localized Engine Ready!")
            
        except Exception as e:
            print(f"❌ [Nyang V5] Localized Engine Init Failed: {e}")

# Import routes to register endpoints
from . import routes