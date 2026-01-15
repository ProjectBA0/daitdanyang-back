# ✅ back/petShop/views/order.py  (예: Blueprint 파일)
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from petShop.models import db, User, Order, OrderItem, Product

order_bp = Blueprint("orders", __name__, url_prefix="/api/orders")


# =========================
# 0) 유틸: 현재 로그인 유저(User) 얻기
# - JWT identity에 user.user_id(문자열) 넣는 방식이라면 filter_by(user_id=ident)
# - JWT identity에 user.id(정수) 넣는 방식이라면 query.get(ident)
# =========================
def get_current_user():
    ident = get_jwt_identity()

    # ✅ 지금 너 프로젝트는 "문자열 로그인아이디(user.user_id)"를 identity로 쓰는 흐름이었음
    # access_token = create_access_token(identity=user.user_id)
    user = User.query.filter_by(user_id=ident).first()
    return user


# =========================
# 1) 주문 목록 조회 (OrderList.jsx가 원하는 스키마로 반환)
# GET /api/orders
# =========================
@order_bp.route("", methods=["GET"])
@order_bp.route("/", methods=["GET"])
@jwt_required()
def list_orders():
    user = get_current_user()
    if not user:
        return jsonify({"error": "유저를 찾을 수 없습니다."}), 401

    orders = (
        Order.query
        .filter(Order.user_id == user.id)   # ✅ Order.user_id는 User.id(FK int)
        .order_by(Order.ordered_date.desc())
        .all()
    )

    payload = []
    for o in orders:
        items_payload = []

        for it in o.items:  # Order.items relationship
            p = getattr(it, "product", None)

            # snapshot 우선, 없으면 product에서 보강
            name = it.product_name or (getattr(p, "title", None) if p else None) or ""
            image_url = it.product_image or (getattr(p, "img_url", None) if p else None) or ""
            unit_price = int(it.unit_price or (getattr(p, "price", 0) if p else 0) or 0)
            qty = int(it.qty or 0)
            line_total = unit_price * qty

            # ✅ OrderList.jsx가 기대하는 키로 맞춤
            items_payload.append({
                "id": it.id,
                "productId": it.product_id,
                "name": name,                 # it.name
                "imageUrl": image_url,        # it.imageUrl
                "qty": qty,                   # it.qty
                "price": line_total,          # it.price  (총액)
                "optionText": "",             # 아직 옵션 없으면 빈 문자열
                "status": "PAID",             # 상태 컬럼 없으면 일단 기본값
                "courier": None,              # 운송장 기능 나중에
                "trackingNo": None,
                "reviewWritten": False,
                "deliveredAt": None,
            })

        payload.append({
            "orderId": o.id,                                  # order.orderId
            "orderedAt": o.ordered_date.strftime("%Y-%m-%d"), # order.orderedAt
            "items": items_payload,
        })

    return jsonify(payload), 200


# =========================
# 2) 주문 생성
# POST /api/orders
# body: { items: [{ product_id, qty }] }
# return: { order_id }
# =========================
@order_bp.route("", methods=["POST"])
@order_bp.route("/", methods=["POST"])
@jwt_required()
def create_order():
    user = get_current_user()
    if not user:
        return jsonify({"error": "유저를 찾을 수 없습니다."}), 401

    data = request.get_json(silent=True)

    # ✅ {items:[...]} 도 받고, [...] (배열만)도 받기
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("items") or []
    else:
        items = []

    print("DEBUG order payload =", data)
    print("DEBUG items =", items)

    if not isinstance(items, list) or len(items) == 0:
        return jsonify({"error": "items가 비어있습니다.", "data": data}), 400

    # ✅ 주문 기본정보
    if not user.default_address:
        return jsonify({"error": "기본 주소가 없습니다."}), 400

    try:
        order = Order(
            user_id=user.id,  # FK int
            order_address=user.default_address,
            order_phone=user.phone,
        )
        db.session.add(order)
        db.session.flush()  # order.id 확보

        # ✅ OrderItem 생성 + snapshot 저장
        for row in items:
            # row가 dict가 아니면 방어
            if not isinstance(row, dict):
                raise ValueError("items 요소 형식이 올바르지 않습니다.")

            product_id = row.get("product_id")
            qty = int(row.get("qty") or 0)

            if not product_id or qty <= 0:
                return jsonify({"error": "product_id/qty가 올바르지 않습니다.", "row": row}), 400

            p = Product.query.get(product_id)
            if not p:
                return jsonify({"error": f"상품이 없습니다. product_id={product_id}"}), 404

            unit_price = int(getattr(p, "price", 0) or 0)
            product_name = getattr(p, "title", "") or ""
            product_image = getattr(p, "img_url", "") or ""

            it = OrderItem(
                order_id=order.id,
                product_id=p.id,
                qty=qty,
                unit_price=unit_price,
                product_name=product_name,
                product_image=product_image,
                status = "DELIVERED"
            )
            db.session.add(it)

        db.session.commit()
        return jsonify({"order_id": order.id}), 201

    except Exception as e:
        db.session.rollback()
        print("ERROR create_order:", repr(e))
        return jsonify({"error": "주문 생성 실패", "detail": str(e)}), 500


# =========================
# 3) 주문 1건 상세 조회 (Order.jsx 용)
# GET /api/orders/<int:order_id>
# =========================
@order_bp.route("/<int:order_id>", methods=["GET"])
@jwt_required()
def get_order(order_id):
    user = get_current_user()
    if not user:
        return jsonify({"error": "유저를 찾을 수 없습니다."}), 401

    o = Order.query.get_or_404(order_id)
    if o.user_id != user.id:
        return jsonify({"error": "권한이 없습니다."}), 403

    items_payload = []
    for it in o.items:
        p = getattr(it, "product", None)

        name = it.product_name or (getattr(p, "title", None) if p else None) or ""
        image_url = it.product_image or (getattr(p, "img_url", None) if p else None) or ""
        unit_price = int(it.unit_price or (getattr(p, "price", 0) if p else 0) or 0)
        qty = int(it.qty or 0)
        line_total = unit_price * qty

        items_payload.append({
            "id": it.id,
            "product_id": it.product_id,
            "title": name,
            "img_url": image_url,
            "qty": qty,
            "line_price": line_total,
            "unit_price": unit_price,
        })

    return jsonify({
        "order": {
            "order_id": o.id,
            "ordered_date": o.ordered_date.strftime("%Y-%m-%d"),
            "order_address": o.order_address,
            "order_phone": o.order_phone,
        },
        "items": items_payload
    }), 200


@order_bp.route("/<int:order_id>", methods=["DELETE"])
@jwt_required()
def cancel_order(order_id):
    user = get_current_user()
    if not user:
        return jsonify({"error": "유저를 찾을 수 없습니다."}), 401

    o = Order.query.get_or_404(order_id)
    if o.user_id != user.id:
        return jsonify({"error": "권한이 없습니다."}), 403

    db.session.delete(o)  # cascade로 OrderItem도 같이 삭제됨 (설정되어 있어야 함)
    db.session.commit()
    return jsonify({"ok": True, "orderId": order_id}), 200

