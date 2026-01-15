from datetime import datetime
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, request, jsonify, abort, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename

from petShop.models import db, User, Question

post_bp = Blueprint("post", __name__, url_prefix="/api/post")

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def _get_current_user() -> User:
    """
    ✅ auth.py는 JWT identity에 user_id(문자열)를 넣고 있음.
    예: identity="admin"
    그래서 User.user_id로 조회한다.
    """
    ident = get_jwt_identity()
    if not ident:
        abort(401)

    user = User.query.filter_by(user_id=str(ident)).first()
    if not user:
        abort(401)

    return user


def _is_admin(user: User) -> bool:
    return (user.role or "").upper() == "ADMIN"


def _save_image(file_storage):
    if not file_storage or not file_storage.filename:
        return None

    filename = secure_filename(file_storage.filename)
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_IMAGE_EXTS:
        abort(400, description="이미지 파일만 업로드할 수 있습니다.")

    unique_name = f"{uuid4().hex}{ext}"

    upload_dir = Path(current_app.root_path) / "static" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    save_path = upload_dir / unique_name
    file_storage.save(save_path)

    return f"/static/uploads/{unique_name}"


@post_bp.route("", methods=["POST"])
@jwt_required()
def create_post():
    user = _get_current_user()

    data = request.get_json(silent=True) or {}

    title = (request.form.get("title") or data.get("title") or "").strip()
    content = (request.form.get("content") or data.get("content") or "").strip()

    category = (
        request.form.get("category")
        or data.get("category")
        or request.form.get("boardType")
        or data.get("boardType")
        or "문의사항"
    ).strip()

    if not title or not content:
        return jsonify({"message": "title/content는 필수입니다."}), 400

    if category == "공지사항" and not _is_admin(user):
        return jsonify({"message": "공지 작성 권한이 없습니다."}), 403

    img_url = _save_image(request.files.get("attachment"))

    post = Question(
        title=title,
        content=content,
        category=category,
        user_id=user.id,
        created_date=datetime.utcnow(),
        img_url=img_url,
    )

    db.session.add(post)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify({"id": post.id, "message": "created", "item": post.to_dict()}), 201


@post_bp.route("/<int:post_id>", methods=["GET"])
@jwt_required(optional=True)
def read_post(post_id):
    ident = get_jwt_identity()
    user = User.query.filter_by(user_id=str(ident)).first() if ident else None

    post = Question.query.get_or_404(post_id)

    if post.category == "공지사항":
        return jsonify({"item": post.to_dict()}), 200

    if not user:
        return jsonify({"message": "로그인이 필요합니다."}), 401

    if _is_admin(user) or post.user_id == user.id:
        return jsonify({"item": post.to_dict()}), 200

    return jsonify({"message": "권한이 없습니다."}), 403


@post_bp.route("/<int:post_id>", methods=["PATCH"])
@jwt_required()
def update_post(post_id):
    user = _get_current_user()
    post = Question.query.get_or_404(post_id)

    if not (_is_admin(user) or post.user_id == user.id):
        return jsonify({"message": "수정 권한이 없습니다."}), 403

    data = request.get_json(silent=True) or {}

    title = request.form.get("title") or data.get("title")
    content = request.form.get("content") or data.get("content")
    category = request.form.get("category") or data.get("category") or request.form.get("boardType") or data.get("boardType")

    if title is not None:
        post.title = title.strip()

    if content is not None:
        post.content = content.strip()

    if category is not None:
        new_category = category.strip()
        if new_category == "공지사항" and not _is_admin(user):
            return jsonify({"message": "공지로 변경할 권한이 없습니다."}), 403
        post.category = new_category

    if request.files.get("attachment") and request.files["attachment"].filename:
        post.img_url = _save_image(request.files.get("attachment"))

    post.modified_date = datetime.utcnow()

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify({"message": "updated", "item": post.to_dict()}), 200


@post_bp.route("/<int:post_id>", methods=["DELETE"])
@jwt_required()
def delete_post(post_id):
    user = _get_current_user()
    post = Question.query.get_or_404(post_id)

    if not (_is_admin(user) or post.user_id == user.id):
        return jsonify({"message": "삭제 권한이 없습니다."}), 403

    db.session.delete(post)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify({"message": "deleted"}), 200
