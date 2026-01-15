from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity


from petShop.models import Cart, Product,db
from flask import request

cart_bp = Blueprint("cart", __name__, url_prefix="/api/cart")

# 장바구니 목록 조회 / 현재 유저의 cart를 가져와 carts를 돌면서(for문 축약형인 리스트 컴프리헨션) json으로 바꿔줌
@cart_bp.route("", methods=["GET"])
@jwt_required()
def get_cart():
    print("AUTH HEADER IN CART:", request.headers.get("Authorization"))
    current_user_id = get_jwt_identity()

    carts = Cart.query.filter_by(user_id=current_user_id).all()
    return jsonify([{
        ""
        "id": c.id,
        "product_id": c.product_id,
        "count": c.count,
        "product": c.product.to_dict() if c.product else None
    } for c in carts]), 200

# 장바구니 추가
@cart_bp.route("", methods=["POST"])
@jwt_required()
def add_cart():
    current_user_id = get_jwt_identity()
    data = request.get_json() or {}
    product_id = data.get("product_id")
    count = int(data.get("count", 1))

# 유효성 검사 product_id가 없거나 db에 없으면 404
    if not product_id:
        return jsonify({"message": "product_id is required"}), 400
    if not Product.query.get(product_id):
        return jsonify({"message": "Product not found"}), 404

# 이미 담긴 상품인지 확인 / 수정이니까 200
    exist = Cart.query.filter_by(user_id=current_user_id, product_id=product_id).first()
    if exist:
        exist.count += count
        db.session.commit()
        return jsonify({"id": exist.id, "product_id": exist.product_id, "count": exist.count}), 200

# 없으면 카트에 담기 / 새로 만드니까 201
    item = Cart(user_id=current_user_id, product_id=product_id, count=count)
    db.session.add(item)
    db.session.commit()
    return jsonify({"id": item.id, "product_id": item.product_id, "count": item.count}), 201


# 수량 변경
@cart_bp.route("/<int:cart_id>", methods=["PATCH"])
@jwt_required()
def patch_cart(cart_id):
    current_user_id = get_jwt_identity()
    data = request.get_json() or {}
    count = data.get("count")
    if count is None:
        return jsonify({"message": "count is required"}), 400
# 내 cart가 아니라면 cart_id가 존재해도 못찾게 막음 (보안)
# A 유저의 cart_id = 5, B 유저가 URL을 바꿔서 요청 → B가 A의 장바구니 수정 / 삭제 가능
    item = Cart.query.filter_by(id=cart_id, user_id=current_user_id).first()
    if not item:
        return jsonify({"message": "Cart item not found"}), 404

# 수량 최소 1
    item.count = max(1, int(count))
    db.session.commit()
    return jsonify({"id": item.id, "product_id": item.product_id, "count": item.count}), 200

# 장바구니 상품 삭제
@cart_bp.route("/<int:cart_id>", methods=["DELETE"])
@jwt_required()
def delete_cart(cart_id):
    current_user_id = get_jwt_identity()

    item = Cart.query.filter_by(id=cart_id, user_id=current_user_id).first()
    if not item:
        return jsonify({"message": "Cart item not found"}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200