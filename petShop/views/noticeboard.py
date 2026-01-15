import math
from datetime import datetime
from typing import Optional

from flask import Blueprint, jsonify, request
from flask_cors import cross_origin
from flask_jwt_extended import jwt_required, get_jwt_identity

from petShop.models import db, Question, Answer, User

board_bp = Blueprint("board", __name__, url_prefix="/api/board")

PER_PAGE_MAX = 50
PAGE_GROUP = 10

# ✅ 이 게시판(Noticeboard)에 "보이기만" 할 카테고리 3개
VISIBLE_CATS = ["문의사항", "건의사항", "기타"]

# ✅ 공지/이벤트는 여기 리스트에서 항상 제외(별도 페이지/별도 API로 사용)
HIDDEN_CATS = ["공지사항", "이벤트"]

PUBLIC_DETAIL_CATS = ["공지사항", "이벤트"]  # ✅ 상세는 누구나 열람



def _get_user_from_identity() -> Optional[User]:
    ident = get_jwt_identity()
    if not ident:
        return None
    return User.query.filter_by(user_id=str(ident)).first()


def _is_admin(user: Optional[User]) -> bool:
    return bool(user) and (user.role or "").upper() == "ADMIN"


def _is_owner(user: Optional[User], q: Question) -> bool:
    return bool(user) and (q.user_id == user.id)


@board_bp.route("", methods=["GET", "OPTIONS"])
@board_bp.route("/", methods=["GET", "OPTIONS"])
@cross_origin()
@jwt_required(optional=True)
def board_list():
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200

    user = _get_user_from_identity()
    is_admin = _is_admin(user)

    page = request.args.get("page", default=1, type=int)
    limit = request.args.get("per_page", default=10, type=int)
    category = request.args.get("category")  # "전체" or 특정 카테고리

    page = max(page, 1)
    limit = max(1, min(limit, PER_PAGE_MAX))

    q = Question.query

    # ✅ 공지/이벤트는 항상 제외
    q = q.filter(~Question.category.in_(HIDDEN_CATS))

    # ✅ 보이는 카테고리는 3개로 고정
    q = q.filter(Question.category.in_(VISIBLE_CATS))

    # ✅ 카테고리 필터 (전체면 미적용)
    if category and category != "전체":
        # 혹시 프론트에서 잘못된 category가 넘어오면 결과 0개가 되는 게 정상
        q = q.filter(Question.category == category)

    q = q.order_by(Question.created_date.desc())

    total = q.order_by(None).count()
    total_pages = max(1, math.ceil(total / limit))
    if page > total_pages:
        page = total_pages

    items = q.offset((page - 1) * limit).limit(limit).all()

    result = []
    for row in items:
        title = getattr(row, "title", None) or getattr(row, "subject", "")
        view = getattr(row, "view_count", 0)
        date_str = row.created_date.strftime("%Y-%m-%d") if row.created_date else ""
        writer = row.user.nickname if getattr(row, "user", None) else "알수없음"

        result.append({
            "id": row.id,
            "title": title,
            "writer": writer,
            "date": date_str,
            "view": view,
            "category": row.category,
            "is_owner": _is_owner(user, row),
            "can_open_detail": True,  # ✅ 이제 제한 없음
        })

    start_page = ((page - 1) // PAGE_GROUP) * PAGE_GROUP + 1
    end_page = min(start_page + PAGE_GROUP - 1, total_pages)

    return jsonify({
        "items": result,
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "start_page": start_page,
        "end_page": end_page,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "is_logged_in": bool(user),
        "is_admin": is_admin,
    }), 200


@board_bp.get("/notices")
def list_notices():
    """
    ✅ 공지사항을 별도 위치에서 쓴다면 유지.
    안 쓰면 지워도 됨.
    """
    q = (Question.query
         .filter(Question.category == "공지사항")
         .order_by(Question.created_date.desc()))
    items = q.limit(3).all()

    return jsonify({
        "items": [
            {
                "id": n.id,
                "title": getattr(n, "title", "") or getattr(n, "subject", ""),
                "date": n.created_date.strftime("%Y-%m-%d") if n.created_date else ""
            }
            for n in items
        ]
    }), 200


@board_bp.route("/<int:question_id>", methods=["GET", "OPTIONS"])
@jwt_required(optional=True)
def read_post(question_id):
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200

    user = _get_user_from_identity()
    is_admin = _is_admin(user)

    post = Question.query.get_or_404(question_id)

    # ✅ 공지/이벤트는 누구나 상세 열람 가능
    if post.category in PUBLIC_DETAIL_CATS:
        return jsonify({"item": to_dict_full(post, user=user)}), 200

    # ✅ 비회원은 상세 불가
    if not user:
        return jsonify({"msg": "로그인이 필요합니다."}), 401

    # ✅ 관리자면 허용
    if is_admin:
        return jsonify({"item": to_dict_full(post, user=user)}), 200

    # ✅ 작성자 본인만 허용
    if post.user_id != user.id:
        return jsonify({"msg": "권한이 없습니다."}), 403

    return jsonify({"item": to_dict_full(post, user=user)}), 200

@board_bp.post("")
@jwt_required()
def board_create():
    user = _get_user_from_identity()
    if not user:
        return jsonify({"msg": "유저 정보를 찾을 수 없습니다. 다시 로그인 해주세요."}), 401

    data = request.get_json() or {}

    # ✅ 공지/이벤트로 작성하려는 시도는 막아두는 게 안전 (관리자 페이지가 따로 있다면 거기서만)
    board_type = data.get("boardType", "문의사항")
    if board_type not in VISIBLE_CATS:
        return jsonify({"msg": "허용되지 않은 카테고리입니다."}), 400

    new_q = Question(
        title=data.get("title"),
        content=data.get("content"),
        category=board_type,
        user_id=user.id,
    )

    db.session.add(new_q)
    db.session.commit()
    return jsonify({"msg": "게시글이 등록되었습니다.", "id": new_q.id}), 201


@board_bp.put("/<int:question_id>")
@jwt_required()
def board_update(question_id):
    user = _get_user_from_identity()
    if not user:
        return jsonify({"msg": "로그인이 필요합니다."}), 401

    q = Question.query.get_or_404(question_id)
    is_admin = _is_admin(user)

    if (not is_admin) and (q.user_id != user.id):
        return jsonify({"msg": "수정 권한이 없습니다."}), 403

    data = request.form if request.form else (request.get_json() or {}) # 🦁 Handle both Form and JSON

    q.title = data.get("title", q.title)
    q.content = data.get("content", q.content)
    
    # 🦁 Allow Category & Event Fields Update
    if is_admin:
        q.category = data.get("boardType", q.category)
        q.start_date = data.get("start_date", q.start_date)
        q.end_date = data.get("end_date", q.end_date)
        
        # Simple Image Handling (if provided via form-data as string path or logic needed)
        # For now, assuming img_url string update or keep existing
        # Actual file upload logic usually handled separately or via attachment
    
    q.modified_date = datetime.utcnow()

    db.session.commit()
    return jsonify({"msg": "게시글이 수정되었습니다."}), 200


@board_bp.delete("/<int:question_id>")
@jwt_required()
def board_delete(question_id):
    user = _get_user_from_identity()
    if not user:
        return jsonify({"msg": "로그인이 필요합니다."}), 401

    q = Question.query.get_or_404(question_id)
    is_admin = _is_admin(user)

    if (not is_admin) and (q.user_id != user.id):
        return jsonify({"msg": "삭제 권한이 없습니다."}), 403

    db.session.delete(q)
    db.session.commit()
    return jsonify({"msg": "게시글이 삭제되었습니다.", "ok": True}), 200


@board_bp.post("/<int:question_id>/answer")
@jwt_required()
def create_answer(question_id):
    """
    ✅ 답변은 관리자만
    (일반 문의/건의/기타 글에 관리자 답변 달아주는 용도)
    """
    user = _get_user_from_identity()
    if not _is_admin(user):
        return jsonify({"msg": "관리자만 답변이 가능합니다."}), 403

    data = request.get_json() or {}

    new_a = Answer(
        question_id=question_id,
        user_id=user.id,
        content=data.get("content"),
        created_date=datetime.utcnow(),
    )

    db.session.add(new_a)
    db.session.commit()
    return jsonify({"msg": "답변이 등록되었습니다."}), 201


def to_dict_full(q: Question, user: Optional[User] = None):
    is_admin = _is_admin(user)
    is_owner = _is_owner(user, q)

    date_display = q.created_date.strftime("%Y-%m-%d") if q.created_date else ""

    answers = []
    if hasattr(q, "answers") and q.answers:
        answers = [{
            "id": a.id,
            "content": a.content,
            "writer": "관리자",
            "date": a.created_date.strftime("%Y-%m-%d") if a.created_date else "",
        } for a in q.answers]

    return {
        "id": q.id,
        "title": getattr(q, "title", None) or getattr(q, "subject", ""),
        "content": getattr(q, "content", ""),
        "category": q.category,
        "writer": q.user.nickname if getattr(q, "user", None) else "알수없음",
        "date": date_display,
        "view": getattr(q, "view_count", 0),
        "img_url": getattr(q, "img_url", None),
        "start_date": getattr(q, "start_date", ""), # 🦁 Added
        "end_date": getattr(q, "end_date", ""),     # 🦁 Added
        "is_owner": is_owner,
        "is_admin": is_admin,
        "answers": answers,
    }
