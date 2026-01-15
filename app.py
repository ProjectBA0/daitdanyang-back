# back/app.py
import os
from dotenv import load_dotenv

# 🦁 Load .env explicitly from the directory where app.py resides
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, '.env')
if os.path.exists(env_path):
    print(f"🦁 [App] Loading .env from: {env_path}")
    load_dotenv(env_path)
else:
    print(f"⚠️ [App] .env not found at: {env_path}")

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_migrate import Migrate

from petShop.models import db
from petShop.extensions import jwt

from petShop.views.cart import cart_bp
from petShop.views.order import order_bp
from petShop.views.product import product_bp
from petShop.views.recent import recent_bp
from petShop.views.review import review_bp
from petShop.views.wishlist import bp as wishlist_bp
from petShop.views.noticeboard import board_bp
from petShop.views.auth import bp as auth_bp
from petShop.views.newpost import post_bp
from petShop.views.event import event_bp
# from petShop.views.chat import chat_bp # 🦁 Deprecated: Simple Chatbot

# 🦁 Advanced VectorRagChatbot Imports
from VectorRagChatbot import chatbot_bp
from VectorRagChatbot.core.engine import NyangRagEngine
from VectorRagChatbot.core.brain import NyangPersona, BrainHub

migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    # 🦁 Initialize AI Engine & Brain (OpenAI-based)
    base_dir = os.path.abspath(os.path.dirname(__file__))
    engine = NyangRagEngine(base_dir)
    try:
        engine.load_resources() # Load LanceDB & Pickle
    except Exception as e:
        print(f"⚠️ [App] Engine Load Failed (Check DB path): {e}")
        
    brain = BrainHub(NyangPersona())
    
    # Register as Flask extensions
    app.extensions['nyang_engine'] = engine
    app.extensions['nyang_brain'] = brain

    # =========================
    # 1. 기본 시크릿 설정
    # =========================

    UPLOAD_ROOT = os.path.join(app.static_folder, "uploads")
    REVIEW_DIR = os.path.join(UPLOAD_ROOT, "reviews")
    os.makedirs(REVIEW_DIR, exist_ok=True)

    app.config["UPLOAD_ROOT"] =UPLOAD_ROOT
    app.config["UPLOAD_FOLDER_REVIEW"]=REVIEW_DIR
    app.config["MAX_CONTENT_LENGTH"] = 5*1024*1024

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev_secret_key")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev_jwt_secret_key")

    # JWT 헤더 설정
    app.config["JWT_TOKEN_LOCATION"] = ["headers"]
    app.config["JWT_HEADER_NAME"] = "Authorization"
    app.config["JWT_HEADER_TYPE"] = "Bearer"

    # =========================
    # 2. DB 설정 (⭐️ 제일 중요)
    # =========================
    # 🦁 Dynamic DB Path from Engine (HF Support)
    if engine.sql_path and os.path.exists(engine.sql_path):
        db_path = os.path.abspath(engine.sql_path)
        print(f"🦁 [App] Using DB found by Engine: {db_path}")
        default_db_uri = f"sqlite:///{db_path}"
    else:
        print("⚠️ [App] Engine did not find DB. Falling back to default.")
        default_db_uri = "sqlite:///petshop.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        default_db_uri
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # =========================
    # 3. CORS 설정
    # =========================
    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    )

    # =========================
    # 4. 확장 초기화
    # =========================
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # =========================
    # 5. 테스트 라우트
    # =========================
    @app.get("/")
    def index():
        return "Petshop API OK"

    # =========================
    # 6. 블루프린트 등록
    # =========================
    app.register_blueprint(product_bp)
    app.register_blueprint(wishlist_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(board_bp)
    app.register_blueprint(post_bp)
    app.register_blueprint(event_bp)
    app.register_blueprint(chatbot_bp) # 🦁 Advanced Chatbot (/api/chat)
    app.register_blueprint(order_bp)
    app.register_blueprint(recent_bp)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
