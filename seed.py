# back/seed.py
import os
import json
from datetime import datetime
import random
import sys


from app import create_app
from petShop.models import db, Product, Question, User, Review

# ✅ crawlers/data 경로
BASE_DATA_DIR = os.path.join(
    os.path.dirname(__file__),
    "data"
)

app = create_app()

with app.app_context():
    # =========================================================
    # 0️⃣ 기존 데이터 전체 삭제 (FK 고려 순서)
    # =========================================================
    db.session.query(Question).delete()
    db.session.query(Product).delete()
    db.session.query(User).delete()
    db.session.commit()
    print("🗑 기존 데이터 전체 삭제 완료")

    # =========================================================
    # 1️⃣ 관리자(admin) 유저 생성
    # =========================================================
    admin = User(
        user_id="admin",
        password="1234",
        nickname="관리자",
        email="admin@example.com",
        role="admin",
    )
    db.session.add(admin)
    db.session.flush()  # ✅ admin.id 확보 (commit 대신 flush)
    print("👤 관리자 계정 생성 완료")

    # =========================================================
    # 2️⃣ 공지사항(Question) 생성
    # =========================================================
    question1 = [
        Question(
            title="[배송공지] 설 연휴 배송 안내",
            category="공지사항",
            user_id=admin.id,  # ✅ 핵심: NOT NULL 해결
            content=(
                "안녕하세요, 다잇다냥입니다.\n"
                "설 연휴 기간 배송 및 고객센터 운영 일정에 대해 안내해 드립니다.\n\n"
                "1. 배송 안내\n"
                "  ▶ 2월 12일 (목) 17시 이전 결제 완료건 : 당일 출고 및 연휴 전 수령 가능\n"
                "    (일부 지역은 연휴 전 수령이 어려울 수 있습니다)\n"
                "  ▶ 2월 12일 (목) 17시 이후 결제 완료건 : 2월 19일 (목)부터 순차 출고,\n"
                "    2월 20일(금)부터 순차 수령 가능\n\n"
                "＊ 제주도, 도서산간 지역 및 업체배송은 1~3일 가량 일찍 마감됩니다.\n\n"
                "2. 고객센터 이용 안내\n"
                "  ▶ 휴무 기간 : 2월 13일(금) ~ 2월 19일(목)까지 휴무\n"
                "  ▶ 연휴 기간 내 궁금하신 사항은 내 정보 > 1:1 게시판을 이용해 주세요.\n\n"
                "설 연휴 전후 물량증가로 인해 배송지연이 예상되오니 너그러이 양해 부탁드립니다.\n"
                "가족과 함께 즐거운 설연휴 보내시기 바랍니다.\n"
                "감사합니다."
            ),
            created_date=datetime(2026, 1, 14),
        ),
        Question(
            title="[배송공지] 연말 연시 배송 안내",
            category="공지사항",
            user_id=admin.id,  # ✅ 핵심: NOT NULL 해결
            content=(
                "안녕하세요, 다잇다냥입니다.\n"
                "연말 및 새해 연휴 기간 배송 및 고객센터 운영 일정에 대해 안내해 드립니다.\n\n"
                "1. 배송 안내\n"
                "  ▶ 12월 30일 (화) 17시 이전 결제 완료건 : 당일 출고 및 31일 수령 가능\n"
                "    (일부 지역은 연휴 전 수령이 어려울 수 있습니다)\n"
                "  ▶ 12월 30일 (목) 17시 이후 결제 완료건 : 1월 2일 (금)부터 순차 출고,\n"
                "    1월 3일(토)부터 순차 수령 가능\n\n"
                "＊ 제주도, 도서산간 지역 및 업체배송은 1~3일 가량 일찍 마감됩니다.\n\n"
                "2. 고객센터 이용 안내\n"
                "  ▶ 휴무 기간 : 12월 31일(수) ~ 1월 1일(목)까지 휴무\n"
                "  ▶ 연휴 기간 내 궁금하신 사항은 내 정보 > 1:1 게시판을 이용해 주세요.\n\n"
                "즐거운 연말 보내시고 새해 복 많이 받으세요.\n"
                "감사합니다."
            ),
            created_date=datetime(2025, 12, 16),
        ),
        Question(
            title="[배송공지] 성탄절 배송공지",
            category="공지사항",
            user_id=admin.id,  # ✅ 핵심: NOT NULL 해결
            content=(
                "안녕하세요, 다잇다냥입니다.\n"
                "12월 25일은 성탄절로 인한 공휴일로 택배사에서 배송 업무를 하지 않습니다.\n"
                "따라서 12월 24일 출고된 상품은 12월 29일부터 순차 수령 가능하오니 주문 시 참고 부탁 드립니다.\n"
                "그럼 즐거운 성탄절 보내시기 바랍니다.\n"
                "감사합니다."
            ),
            created_date=datetime(2025, 12, 5),
        ),
        Question(
            title="택배 출고 마감시간 변경 안내",
            category="공지사항",
            user_id=admin.id,  # ✅ 핵심: NOT NULL 해결
            content=(
                "안녕하세요, 다잇다냥입니다.\n"
                "2025년 11월 10일(월) 부터 출고 마감 시간이 변경되어 안내드립니다.\n\n"
                "- 발송 마감\n"
                "평일 : 오후 5시 까지 결제 완료 시 당일 출고 (평일 5시 30분 => 평일 5시 변경)\n"
                "토요일 : 오후 12시 까지 결제 완료 시 당일 출고 (기존 동일)\n\n"
                "보다 안전하고 정호가한 배송을 위하여 마감 시간을 변경하게 되었사오니 참고 부탁 드립니다.\n"
                "앞으로도 보다 나은 서비스를 제공할 수 있도록 노력하겠습니다.\n"
                "감사합니다."
            ),
            created_date=datetime(2025, 11, 14),
        ),
        # --- 이벤트 ---
        Question(
            title="냥산타가 준비한 크리스마스 선물", category="이벤트", user_id=admin.id,
            start_date="2025.12.20", end_date="2025.12.31",
            img_url="/images/banner/event_banner1.png",
            content="""<h3>🎄 냥산타가 쏜다냥! 🎄</h3><p>우리 고양이 친구들을 위해 냥산타가 굴뚝 타고 선물을 가득 가져왔어냥!</p><br/><h4>🐟 인기 캔&간식 모음전</h4><p>우리 냥이가 환장하는 츄르, 참치캔, 동결건조 간식을 최대 50% 할인된 가격에 만나보라냥.</p><br/><h4>🏠 따뜻한 겨울 숨숨집</h4><p>추운 겨울에도 따끈하게 꿀잠 잘 수 있도록! 극세사 숨숨집과 온열 매트 특가 세일중이다냥!</p>"""
        ),
        Question(
            title="멍산타가 준비한 크리스마스 선물", category="이벤트", user_id=admin.id,
            start_date="2025.12.20", end_date="2025.12.31",
            img_url="/images/banner/event_banner2.png",
            content="""<h3>🎅 멍산타가 쏜다! 🎅</h3><p>댕댕이 친구들을 위해 멍산타가 양말 가득 선물을 담아왔어요!</p><br/><h4>🍖 인기 간식 모음전</h4><p>우리 강아지가 좋아하는 뼈다귀, 육포, 개껌을 최대 50% 할인된 가격에 만나보세요.</p><br/><h4>👕 따뜻한 겨울나기</h4><p>산책할 때 추위에 떨지 않도록! 기모 후드티와 패딩 조끼 특가 세일!</p>"""
        ),
        Question(
            title="신년맞이 전품목 세일", category="이벤트", user_id=admin.id,
            start_date="2025.12.20", end_date="2026.01.20",
            img_url="/images/banner/event_banner3.png",
            content="""<h3>🌅 2026년 새해 복 많이 받으세요!</h3><p>새해를 맞아 다잇다냥에서 전품목 감사 세일을 진행합니다.</p><br/><h4>🛍 세일 혜택</h4><ul><li>전품목 기본 <b>30% 파격 할인</b></li><li>5만원 이상 구매 시 무료배송</li><li>신년맞이 럭키박스 (선착순 100명)</li></ul><br/><p>새로운 시작, 다잇다냥과 함께 하세요!</p>"""
        ),
        Question(
            title="냥멍하라 1994", category="이벤트", user_id=admin.id,
            start_date="2025.12.20", end_date="2026.01.20",
            img_url="/images/banner/event_banner4.png",
            content="""<h3>📼 응답하라 냥멍이들! 1994 레트로 기획전</h3><p>그 시절 감성 그대로! 가격까지 <b>1994년 그때 그 가격</b>으로 되돌렸습니다!</p><br/><h4>💰 1994년 타임머신 가격</h4><ul><li>추억의 껌값으로 즐기는 '천원 삑삑이'</li><li>물가 상승 무시! 1994년 수준의 파격가 상품 대량 입고</li></ul><br/><h4>📺 90년대 감성 아이템</h4><ul><li>촌스러워서 더 귀여운 '할머니 조끼'</li><li>옛날 텔레비전 모양 스크래쳐</li></ul><br/><p>추억 여행과 함께 미친 가격을 경험해보세요!</p>"""
        ),
        # --- ID 조절용 더미 (6, 7, 8번) ---
        Question(title="[시스템] 서버 점검 안내", category="공지사항", user_id=admin.id, content="안정적인 서비스를 위해 서버 점검이 진행됩니다.", created_date=datetime(2026, 1, 1)),
        Question(title="[약관] 개인정보 처리방침 변경 안내", category="공지사항", user_id=admin.id, content="개인정보 처리방침이 일부 변경되었습니다.", created_date=datetime(2026, 1, 2)),
        Question(title="[안내] 고객센터 전화번호 변경", category="공지사항", user_id=admin.id, content="고객센터 번호가 1588-0000으로 변경되었습니다.", created_date=datetime(2026, 1, 3)),

        # --- 메인 이벤트 (Banner 4, 5, 6, 7 -> ID 9, 10, 11, 12) ---
        Question(
            title="[신규 입점] Lucy Pet Products 공식 런칭", category="이벤트", user_id=admin.id,
            start_date="2026.01.10", end_date="2026.03.31",
            img_url="/images/banner/banner4.jpg",
            content="""<h3>🥩 루시펫 신규 입점! 🥩</h3><p>장 건강 특화 프리미엄 사료, 루시펫이 다있다냥에 상륙했다냥!</p><br/><h4>✨ 브랜드 특징</h4><ul><li>장 건강 포뮬러</li><li>입점 기념 할인 이벤트</li><li>인기 상품 선착순 증정</li></ul><br/><p>반려동물의 건강을 생각한 프리미엄 사료 브랜드를 지금 만나보세요.</p>"""
        ),
        Question(
            title="[패드 기획전] 최대 34% 할인! 위생용품 모음전", category="이벤트", user_id=admin.id,
            start_date="2026.01.10", end_date="2026.02.28",
            img_url="/images/banner/banner5.jpg",
            content="""<h3>🧻 위생과 청결을 한 번에! 🧻</h3><p>매일 쓰는 필수 위생용품, 지금이 가장 저렴합니다.</p><br/><h4>💸 실속 혜택</h4><ul><li>최대 34% 할인</li><li>인기 패드 모음</li><li>재구매 고객 만족도 BEST</li></ul><br/><p>대용량부터 실속 구성까지 한 번에 준비하세요.</p>"""
        ),
        Question(
            title="[긴급특가] 유통기한 임박! 지금이 가장 싸다", category="이벤트", user_id=admin.id,
            start_date="2026.01.16", end_date="2026.01.31",
            img_url="/images/banner/banner6.jpg",
            content="""<h3>🚨 놓치면 끝! 긴급특가 🚨</h3><p>유통기한이 가까운 상품을 파격적인 가격으로 만나보세요.</p><br/><h4>💰 품질은 그대로, 가격만 착해졌습니다</h4><ul><li>한정 수량 / 조기 품절 주의</li><li>교환·환불 정책은 상품별 상이</li><li>기간 종료 시 자동 마감</li></ul><br/><p>정상 품질의 상품을 합리적인 가격으로 구매할 수 있는 절호의 기회입니다.</p>"""
        ),
        Question(
            title="[역대급 할인] 최대 75% OFF! 땡처리 특가전", category="이벤트", user_id=admin.id,
            start_date="2026.01.16", end_date="2026.01.25",
            img_url="/images/banner/banner7.jpg",
            content="""<h3>🔥 최대 75% OFF! 🔥</h3><p>황금연휴까지 단 한 번, 지금 아니면 만날 수 없는 가격!</p><br/><h4>🎉 땡처리 특가전 혜택</h4><ul><li>전 상품 대상 (일부 제외)</li><li>연휴 기간 한정 진행</li><li>재고 소진 시 조기 종료</li></ul><br/><p>세상 어디에도 없는 초특가 찬스로 부담 없이 쇼핑하세요.</p>"""
        ),

        # --- 메인 이벤트 (Banner 1, 2, 3 -> ID 13, 14, 15) ---
        Question(
            title="[신상품 출시] 아이들을 위한 종합 구강 건강 솔루션", category="이벤트", user_id=admin.id,
            start_date="2026.01.10", end_date="2026.03.31",
            img_url="/images/banner/banner1.jpg",
            content="""<h3>🦷 다이아몬드바 신제품 출시! 🦷</h3><p>양치가 어려운 아이들을 위한 신개념 구강 케어 제품이 나왔다냥!</p><br/><h4>✨ 구강 케어 솔루션</h4><ul><li>간편한 섭취</li><li>아이 맞춤 설계</li><li>출시 기념 특별 혜택 제공</li></ul><br/><p>간편하게 즐기면서 관리할 수 있는 구강 건강 솔루션을 만나보세요.</p>"""
        ),
        Question(
            title="[감사 이벤트] 구매 고객 대상 스페셜 증정", category="이벤트", user_id=admin.id,
            start_date="2026.01.01", end_date="2026.02.28",
            img_url="/images/banner/banner2.jpg",
            content="""<h3>🎁 Thank you! 사은품 증정 🎁</h3><p>항상 다있다냥과 함께해주셔서 감사합니다.</p><br/><h4>💝 특별한 선물</h4><ul><li>일정 금액 이상 구매 시 증정</li><li>사은품은 랜덤 발송</li><li>재고 소진 시 종료</li></ul><br/><p>소소하지만 특별한 선물을 준비했으니 꼭 받아가라냥!</p>"""
        ),
        Question(
            title="[단독 최저가] ONLY 다있다냥! 펫용품 대전", category="이벤트", user_id=admin.id,
            start_date="2026.01.15", end_date="2026.02.28",
            img_url="/images/banner/banner3.jpg",
            content="""<h3>🐶🐱 다있다냥 단독 펫용품 대전 🐱🐶</h3><p>다있다냥에서만 가능한 단독 최저가 세일!</p><br/><h4>🛍 쇼핑 리스트</h4><ul><li>전 카테고리 총집합 (장난감, 리빙, 의류 등)</li><li>단독 특가 상품 다수</li><li>신규 회원 추가 혜택</li></ul><br/><p>반려동물을 위한 모든 필수템을 한 자리에서 만나보세요.</p>"""
        ),
        # --- 고객문의 (배송) ---
        Question(title="배송 언제 오나요?", category="배송", user_id=admin.id, content="어제 주문했는데 언제 도착하는지 알고 싶어요. 빠른 배송 부탁드립니다!",
                 created_date=datetime(2025, 12, 20)),
        Question(title="배송지 변경 가능한가요?", category="배송", user_id=admin.id,
                 content="방금 주문을 했는데 이사 전 주소로 잘못 적었어요. 서울시 강남구... 로 변경 가능할까요?", created_date=datetime(2025, 12, 22)),
        Question(title="부분 배송 되나요?", category="배송", user_id=admin.id,
                 content="주문한 물건 중 하나가 입고 지연이라고 알림이 왔는데, 나머지는 먼저 받을 수 있을까요?", created_date=datetime(2025, 12, 23)),

        # --- 고객문의 (결제) ---
        Question(title="카드 결제 취소하고 싶어요", category="결제", user_id=admin.id, content="실수로 중복 주문을 했습니다. 하나는 취소 처리 부탁드립니다.",
                 created_date=datetime(2025, 12, 25)),
        Question(title="무통장 입금 확인 부탁드려요", category="결제", user_id=admin.id,
                 content="오늘 오전 10시에 입금자명 '고양이조아'로 입금했습니다. 확인 부탁드려요.", created_date=datetime(2025, 12, 26)),
        Question(title="현금영수증 발급되나요?", category="결제", user_id=admin.id,
                 content="무통장 입금으로 결제했는데 현금영수증 발급받고 싶습니다. 010-1234-5678로 신청합니다.", created_date=datetime(2025, 12, 27)),

        # --- 고객문의 (제품) ---
        Question(title="이 사료 유통기한이 어떻게 되나요?", category="제품", user_id=admin.id,
                 content="대량 구매하려고 하는데 유통기한이 언제까지인지 궁금합니다. 넉넉한가요?", created_date=datetime(2025, 12, 28)),
        Question(title="강아지도 먹어도 되나요?", category="제품", user_id=admin.id,
                 content="고양이 전용 츄르라고 되어있는데, 혹시 강아지에게 급여해도 문제 없는 성분인가요?", created_date=datetime(2025, 12, 29)),

        # --- 고객문의 (사이트이용) ---
        Question(title="회원 탈퇴는 어떻게 하나요?", category="사이트이용", user_id=admin.id,
                 content="사이트 이용을 중단하려고 하는데 탈퇴 메뉴를 못 찾겠습니다. 어디에 있나요?", created_date=datetime(2025, 12, 30)),
        Question(title="아이디 찾기 기능이 안 돼요", category="사이트이용", user_id=admin.id,
                 content="가입한 아이디를 잊어버려서 찾으려고 하는데, 핸드폰 인증 후에도 찾기가 안 됩니다.", created_date=datetime(2025, 12, 31)),
    ]






    review1 = [
        Review(
            user_id= admin.id,
            product_id = 580,
            content = "너무 좋아요",
            img_url = "https://shopping-phinf.pstatic.net/main_5281764/52817642964.20250213171143.jpg",
            rating = 5,
            create_date=datetime(2026,1,7)
        ),
        Review(
            user_id=admin.id,
            product_id=580,
            content="가격이 너무 비싸요",
            img_url="1.jpg",
            rating=3,
            create_date=datetime(2026, 1, 10)
        ),
        Review(
            user_id=admin.id,
            product_id=582,
            content="외관은 이쁜데 그냥저냥 그래요",
            img_url="5.jpg",
            rating=4,
            create_date=datetime(2026, 1, 7)
        )
    ]

    db.session.add_all(question1+review1)
    print("📢 공지사항 생성 완료")

    # =========================================================
    # 3️⃣ JSON 파일 순회 → Product 생성
    # =========================================================
    products_to_add = []
    count = 0

    if not os.path.exists(BASE_DATA_DIR):
        raise FileNotFoundError(f"❌ 데이터 폴더 없음: {BASE_DATA_DIR}")

    for root, dirs, files in os.walk(BASE_DATA_DIR):
        for filename in files:
            if not filename.endswith(".json"):
                continue

            file_path = os.path.join(root, filename)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # ✅ pet_type 추론 (data/dog | data/cat | data/other)
                rel_path = os.path.relpath(file_path, BASE_DATA_DIR)
                path_parts = rel_path.split(os.sep)

                pet_type = "dog"
                if path_parts[0] in ("dog", "cat", "other"):
                    pet_type = path_parts[0]

                # ✅ category 정리 ("강아지_사료" → "사료")
                raw_cat = data.get("main_category", "기타")
                category = raw_cat.split("_")[-1] if "_" in raw_cat else raw_cat
                sub_category = data.get("sub_category", "")
                title = data.get("re_title")
                product = Product(
                    title=title,
                    content=f"브랜드: {data.get('brand','')}\n제조사: {data.get('maker','')}",
                    price=int(data.get("lprice", 0) or 0),
                    img_url=data.get("image", ""),
                    category=category,
                    sub_category=sub_category,
                    pet_type=pet_type,
                    stock=100,
                    views=random.randint(100, 1000),
                    review_count=0,
                )


                products_to_add.append(product)
                count += 1

            except Exception as e:
                print(f"❌ JSON 처리 실패: {file_path} → {e}")

    if products_to_add:
        db.session.add_all(products_to_add)
        db.session.commit()
        print(f"✅ 총 {count}개 Product 시드 완료")
    else:
        db.session.commit()

    print("🎉 Product + Question + Admin 시드 완료!")
