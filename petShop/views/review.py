import os, uuid

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename

from petShop.models import Review, db, Product, User

review_bp = Blueprint('review', __name__, url_prefix='/api')

ALLOWED_EXT = {"png", "jpg", "jpeg", "webp"}

# 파일 이름에 .이 있고 확장자가 위 4개 중에 하나면 TRUE
# "." in filename = 파일명에 . 있는지 확인 / rsplit(".", 1) 오른쪽 기준으로 1번 자름
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

# 이미지 파일 삭제
def delete_image(img_url: str):
    if not img_url:
        return

    # 파일명 가져오기
    filename = os.path.basename(img_url)

    save_dir = current_app.config["UPLOAD_FOLDER_REVIEW"]
    file_path = os.path.join(save_dir, filename)

    if os.path.isfile(file_path):
        os.remove(file_path)

@review_bp.get('/product/<int:product_id>/reviews')
def list_reviews(product_id):
    page = request.args.get('page', default=1, type=int)
    limit = request.args.get('limit', default=8, type=int)
    sort = request.args.get('sort', default='id_desc',type=str)

    q = Review.query.filter(Review.product_id ==product_id)

    if sort == "rating_desc":
        q = q.order_by(Review.rating.desc())
    elif sort == "rating_asc":
        q = q.order_by(Review.rating.asc())
    elif sort == "id_desc":
        q = q.order_by(Review.create_date.desc())
    else:
        q = q.order_by(Review.create_date.desc())

    total = q.count()
    items = (q.offset((page - 1) * limit).limit(limit).all())

    return jsonify({
        "items": [r.to_dict() for r in items],
        "page": page,
        "limit": limit,
        "total": total,
        "totalPages": (total + limit - 1) // limit
    })

@review_bp.post('/product/<int:product_id>/reviews')
@jwt_required()
def create_review(product_id):
    identity = get_jwt_identity()  # 보통 로그인 아이디(user.user_id)가 들어옴

    # ✅ identity로 User 찾기
    u = User.query.filter_by(user_id=identity).first()
    if not u:
        return jsonify({"message": "유저를 찾을 수 없습니다."}), 401

    rating_raw = request.form.get("rating")
    try:
        rating = int(rating_raw)
    except (TypeError, ValueError):
        return jsonify({"message": "별점을 선택해 주세요."}), 400

    content = (request.form.get("content") or "").strip()

    if rating < 1 or rating > 5:
        return jsonify({"message": "별점은 1~5점만 가능합니다."}), 400
    if not content:
        return jsonify({"message": "내용을 입력해 주세요."}), 400

    img_url = None
    f = request.files.get("image")

    if f and f.filename:
        if not allowed_file(f.filename):
            return jsonify({"message": "이미지 확장자는 png/jpg/jpeg/webp만 가능합니다."}), 400

        safe = secure_filename(f.filename)
        ext = safe.rsplit(".", 1)[1].lower()
        new_name = f"{uuid.uuid4().hex}.{ext}"

        save_dir = current_app.config["UPLOAD_FOLDER_REVIEW"]
        os.makedirs(save_dir, exist_ok=True)  # ✅ 폴더 없으면 500 방지
        save_path = os.path.join(save_dir, new_name)
        f.save(save_path)

        img_url = f"/static/uploads/reviews/{new_name}"

    r = Review(
        user_id=u.id,          # ✅ 여기: 정수 PK로 저장 (정답)
        product_id=product_id,
        content=content,
        rating=rating,
        img_url=img_url
    )

    db.session.add(r)
    db.session.commit()
    return jsonify(r.to_dict()), 201


@review_bp.put('/reviews/<int:review_id>')
@jwt_required()
def update_review(review_id):
    identity = get_jwt_identity()
    r = Review.query.get_or_404(review_id)

    u = User.query.filter_by(user_id=identity).first()
    if not u:
        return jsonify({"message": "유저를 찾을 수 없습니다."}), 401

    # 3️⃣ 권한 체크
    if r.user_id != u.id:
        return jsonify({"message": "권한이 없습니다."}), 403

    rating = request.form.get("rating", type=int)
    content = (request.form.get("content") or "").strip()

    if rating is not None:
        if rating < 1 or rating > 5:
            return jsonify({"message": "별점은 1~5점만 가능합니다."}), 400
        r.rating = rating

    if content:
        r.content = content

    remove_image = request.form.get("removeImage") == "1"
    f = request.files.get("image")

    if remove_image:
        delete_image(r.img_url)
        r.img_url = None

    # 이미지 교체 (선택)

    if f and f.filename:
        if not allowed_file(f.filename):
            return jsonify({"message": "이미지 확장자는 png/jpg/jpeg/webp만 가능합니다."}), 400

        # 새 파일 저장
        safe = secure_filename(f.filename)
        ext = safe.rsplit(".", 1)[1].lower()
        new_name = f"{uuid.uuid4().hex}.{ext}"

        save_dir = current_app.config["UPLOAD_FOLDER_REVIEW"]
        os.makedirs(save_dir, exist_ok=True)
        f.save(os.path.join(save_dir, new_name))

        r.img_url = f"/static/uploads/reviews/{new_name}"

    db.session.commit()
    return jsonify(r.to_dict())

@review_bp.delete('/reviews/<int:review_id>')
@jwt_required()
def delete_review(review_id):
    identity = get_jwt_identity()

    r = Review.query.get_or_404(review_id)

    u = User.query.filter_by(user_id=identity).first()
    if not u:
        return jsonify({"message": "유저를 찾을 수 없습니다."}), 401

    if r.user_id != u.id:
        return jsonify({"message": "권한이 없습니다."}), 403

    # 파일 삭제
    delete_image(r.img_url)

    # DB row 삭제
    db.session.delete(r)
    db.session.commit()
    return jsonify({"message": "삭제 완료"})

@review_bp.get('/reviews/main')
def list_main_reviews():
    q = ((Review.query
          .filter(Review.img_url.isnot(None)))
          .order_by(Review.rating.desc(), Review.create_date.desc()))

    reviews = q.limit(3).all()

    return jsonify({
        "reviews": [{
            "id": r.id,
            "user_id": r.user_id,
            "content": r.content,
            "rating": r.rating,
            "img_url": r.img_url,
            "date": r.create_date.strftime("%Y-%m-%d")}
            for r in reviews]
    })

@review_bp.get('/me/reviews')
@jwt_required()
def list_my_reviews():
    i = get_jwt_identity()
    u = User.query.filter_by(user_id=i).first()
    if not u:
        return jsonify({"message": "유저를 찾을 수 없습니다."}), 401
    user_id = u.id

    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 8, type=int)
    rating = request.args.get('rating', type=int)

    q = (db.session.query(Review, Product)
         .join(Product, Product.id == Review.product_id)
         .filter(Review.user_id == user_id))

    if rating is not None:
        if rating < 1 or rating > 5:
            return jsonify({"message": "별점은 1~5점만 가능합니다."}),400
        q = q.filter(Review.rating == rating)

    q = q.order_by(Review.create_date.desc())

    total = q.count()
    item = q.offset((page - 1) * limit).limit(limit).all()

    items = []
    # join을 쓰면 list 안에 튜플로 들어감
    for r,p in item:
        items.append({
            "id": r.id,
            "product_id": r.product_id,
            "productName": p.title,
            "rating": r.rating,
            "content": r.content,
            "createdAt": r.create_date.strftime("%Y-%m-%d"),
            "images": [r.img_url] if r.img_url else []
        })

    return jsonify({
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "totalPages": (total + limit - 1)//limit,
    })