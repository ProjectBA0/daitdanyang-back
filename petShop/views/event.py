from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from petShop.models import db, Question  # ✅ Question으로 변경

event_bp = Blueprint('event', __name__, url_prefix='/api/event')


@event_bp.get("")
@jwt_required(optional=True)
def get_events():
    # ✅ category='이벤트'인 게시글만 조회
    events = Question.query.filter_by(category='이벤트').order_by(Question.id.asc()).all()

    current_user = get_jwt_identity()
    is_admin = (current_user == 'admin')

    return jsonify({
        "items": [e.to_dict() for e in events],
        "is_admin": is_admin
    })


@event_bp.get("/<int:event_id>")
@jwt_required(optional=True)
def get_event_detail(event_id):
    # ✅ Question 테이블에서 조회
    event = Question.query.get_or_404(event_id)

    # 관리자 여부 확인
    current_user = get_jwt_identity()
    is_admin = (current_user == 'admin')

    result = event.to_dict()
    result['is_admin'] = is_admin

    return jsonify(result)


# ✅ 이벤트 등록 (Admin 전용)
@event_bp.post("")
@jwt_required()
def create_event():
    current_user = get_jwt_identity()
    if current_user != 'admin':
        return jsonify({"msg": "관리자만 접근 가능합니다."}), 403

    data = request.get_json()

    # ✅ 관리자 유저 객체 찾기
    from petShop.models import User
    admin_user = User.query.filter_by(user_id='admin').first()

    new_event = Question(
        title=data.get('title'),
        content=data.get('content'),
        img_url=data.get('img_url'),
        start_date=data.get('start_date'),
        end_date=data.get('end_date'),
        category='이벤트',  # ✅ 카테고리 고정
        user_id=admin_user.id
    )
    db.session.add(new_event)
    db.session.commit()
    return jsonify({"msg": "이벤트가 등록되었습니다.", "id": new_event.id}), 201


# ✅ 이벤트 수정 (Admin 전용)
@event_bp.put("/<int:event_id>")
@jwt_required()
def update_event(event_id):
    current_user = get_jwt_identity()
    if current_user != 'admin':
        return jsonify({"msg": "관리자만 접근 가능합니다."}), 403

    event = Question.query.get_or_404(event_id)
    data = request.get_json()

    event.title = data.get('title', event.title)
    event.content = data.get('content', event.content)
    event.img_url = data.get('img_url', event.img_url)
    event.start_date = data.get('start_date', event.start_date)
    event.end_date = data.get('end_date', event.end_date)

    db.session.commit()
    return jsonify({"msg": "이벤트가 수정되었습니다."}), 200


# ✅ 이벤트 삭제 (Admin 전용)
@event_bp.delete("/<int:event_id>")
@jwt_required()
def delete_event(event_id):
    current_user = get_jwt_identity()
    if current_user != 'admin':
        return jsonify({"msg": "관리자만 접근 가능합니다."}), 403

    event = Question.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    return jsonify({"msg": "이벤트가 삭제되었습니다."}), 200