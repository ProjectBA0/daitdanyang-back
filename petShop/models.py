from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.types import JSON
from datetime import datetime

db = SQLAlchemy()


# ============================================
# 1. User & Address (회원 + 여러 배송지)
# ============================================
class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)

    # 로그인 아이디
    user_id = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)

    nickname = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    # 기본 배송지 (선택 사항)
    default_address = db.Column(db.String(255), nullable=True)

    phone = db.Column(db.String(20), unique=True, nullable=True)

    role = db.Column(db.String(20), nullable=False, default="USER" )

    # ✅ 선호 반려동물 (다중 선택 가능) ex) ["dog", "cat"]
    pet_list = db.Column(JSON, nullable=True )




class Address(db.Model):
    """
    유저가 저장해 두는 여러 배송지 (집, 회사, 부모님댁 등)
    주문할 때 여기서 하나 선택하거나, 새 주소 입력해서 추가 저장
    """
    __tablename__ = 'address'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False
    )
    user = db.relationship(
        'User',
        backref=db.backref('addresses', lazy=True)
    )

    # 주소 이름 (집, 회사 같은 라벨)
    label = db.Column(db.String(50), nullable=True)

    full_address = db.Column(db.String(255), nullable=False)

    # 기본 배송지 여부
    is_default = db.Column(db.Boolean, nullable=False, default=False)


# ============================================
# 2. Product (펫 상품)
# ============================================
class Product(db.Model):
    __tablename__ = 'product'

    id = db.Column(db.Integer, primary_key=True)

    # 상품명
    title = db.Column(db.String(200), nullable=False)

    # 상품 설명
    content = db.Column(db.Text, nullable=True)

    # 가격 (원 단위 정수)
    price = db.Column(db.Integer, nullable=False)

    # 대표 이미지 경로 또는 URL
    img_url = db.Column(db.String(255), nullable=True)

    # 상품 카테고리 (사료, 간식, 장난감, 용품 등)
    category = db.Column(db.String(50), nullable=True)

    # 상품 카테고리 (사료, 간식, 장난감, 용품 등)
    sub_category = db.Column(db.String(50), nullable=True)

    # 대상 동물 (cat, dog, etc)
    pet_type = db.Column(db.String(10), nullable=True)

    # 조회수
    views = db.Column(db.Integer, nullable=False, default=0)

    # 재고 수량
    stock = db.Column(db.Integer, nullable=False, default=0)

    # 리뷰 개수 (리뷰 작성 시 증가)
    review_count = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "price": self.price,

            # 프론트가 item.imgUrl을 쓰고 있으니 imgUrl 키로 내려줌
            "imgUrl": self.img_url,

            "category": self.category,
            "sub_category": self.sub_category,
            "pet_type": self.pet_type,

            "views": self.views,
            "stock": self.stock,
            "review_count": self.review_count,
        }

# ============================================
# 3. QnA (문의 게시판)
# ============================================
class Question(db.Model):
    """
    상품 문의, 이벤트 문의, 일반 문의 등
    """
    __tablename__ = 'question'

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)

    # 예: "상품문의", "이벤트", "건의사항" 등
    category = db.Column(db.String(50), nullable=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False
    )
    user = db.relationship(
        'User',
        backref=db.backref('questions', lazy=True)
    )

    content = db.Column(db.Text, nullable=False)

    created_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    modified_date = db.Column(db.DateTime, nullable=True)

    img_url = db.Column(db.String(255), nullable=True)

    # ✅ 이벤트용 기간 필드 (통합)
    start_date = db.Column(db.String(50), nullable=True)
    end_date = db.Column(db.String(50), nullable=True)

    def to_dict(self):
        # ✅ 이벤트인 경우 기간을, 일반 게시글인 경우 생성일을 'date' 키로 반환
        display_date = f"{self.start_date} ~ {self.end_date}" if self.start_date else self.created_date.strftime(
            "%Y-%m-%d")

        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "writer": self.user.nickname if self.user else "알수없음",
            "date": display_date,  # ✅ 프론트엔드 호환성 유지
            "img_url": self.img_url,
            "start_date": self.start_date,
            "end_date": self.end_date
        }

class Answer(db.Model):
    """
    관리자 또는 스태프가 남기는 답변
    """
    __tablename__ = 'answer'

    id = db.Column(db.Integer, primary_key=True)

    question_id = db.Column(
        db.Integer,
        db.ForeignKey('question.id', ondelete='CASCADE'),
        nullable=False
    )
    question = db.relationship(
        'Question',
        backref=db.backref('answers', lazy=True)
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False
    )
    user = db.relationship(
        'User',
        backref=db.backref('answers', lazy=True)
    )

    title = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=False)

    created_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    modified_date = db.Column(db.DateTime, nullable=True)

    img_url = db.Column(db.String(255), nullable=True)


# ============================================
# 4. Cart (장바구니)
# ============================================
class Cart(db.Model):
    __tablename__ = 'cart'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False
    )
    user = db.relationship(
        'User',
        backref=db.backref('carts', lazy=True)
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey('product.id', ondelete='CASCADE'),
        nullable=False
    )
    product = db.relationship(
        'Product',
        backref=db.backref('carts', lazy=True)
    )

    # 장바구니에 담긴 수량
    count = db.Column(db.Integer, nullable=False, default=1)


# ============================================
# 5. Order (주문)
# ============================================
class Order(db.Model):
    __tablename__ = "orders"  # ✅ 'order' 대신 'orders' 추천

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True
    )
    user = db.relationship("User", backref=db.backref("orders", lazy=True))

    order_address = db.Column(db.String(255), nullable=False)
    order_phone = db.Column(db.String(20), nullable=True)
    ordered_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # ✅ Order → OrderItem (한 주문에 여러 상품)
    items = db.relationship(
        "OrderItem",
        backref="order",
        cascade="all, delete-orphan",
        lazy=True
    )

# ============================================
# 5. OrderItem (주문상세)
# ============================================
class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)

    # ✅ FK는 orders.id 로
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)

    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="DELIVERED")

    # snapshot
    unit_price = db.Column(db.Integer, nullable=False, default=0)
    product_name = db.Column(db.String(255))
    product_image = db.Column(db.String(255))

    # ✅ OrderItem → Product 관계 (상품 정보 접근 편하게)
    product = db.relationship("Product", lazy=True)

# ============================================
# 6. Reviews (상품 리뷰)
# ============================================
class Review(db.Model):
    __tablename__ = 'review'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False
    )
    user = db.relationship(
        'User',
        backref=db.backref('reviews', lazy=True)
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey('product.id', ondelete='CASCADE'),
        nullable=False
    )
    product = db.relationship(
        'Product',
        backref=db.backref('reviews', lazy=True)
    )

    # 리뷰 내용
    content = db.Column(db.Text, nullable=False)

    img_url = db.Column(db.String(255), nullable=True)

    # 평점 (1~5점 등)
    rating = db.Column(db.Integer, nullable=False)

    create_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "img_url": self.img_url,
            "rating": self.rating,
            "create_date": self.create_date.isoformat(),
            "writer": f"구매자{self.id}"
        }
# ============================================
# 7. pet (내가 키우는 동물에 대한 정보)
# ============================================

class Pet(db.Model):
    __tablename__ = 'pet'

    id = db.Column(db.Integer, primary_key=True)

    # 어떤 유저의 펫인지
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False
    )
    user = db.relationship(
        'User',
        backref=db.backref('pets', lazy=True)
    )

    # 펫 이름
    name = db.Column(db.String(50), nullable=False)

    # 동물 종류 (dog, cat, etc)
    pet_type = db.Column(db.String(20), nullable=False)

    # 이 펫의 성별 / 생일
    gender = db.Column(db.String(10), nullable=True)
    birthday = db.Column(db.Date, nullable=True)

    # 선택: 품종, 몸무게 등 추가 가능
    breed = db.Column(db.String(50), nullable=True)
    weight = db.Column(db.Float, nullable=True)


# ============================================
# 8. Wishlist (찜 목록)
# ============================================
class Wishlist(db.Model):
    __tablename__ = 'wishlist'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False
    )
    user = db.relationship(
        'User',
        backref=db.backref('wishlists', lazy=True)
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey('product.id', ondelete='CASCADE'),
        nullable=False
    )
    product = db.relationship(
        'Product',
        backref=db.backref('wishlists', lazy=True)
    )

    created_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

# ==============================================================================
# [Gemini 작업 로그] - 2025.12.26
# 1. Wishlist 모델 추가
#    - User와 Product를 N:M 관계처럼 연결 (중간 테이블 역할)
#    - user_id, product_id, created_date 필드 포함
# ==============================================================================

