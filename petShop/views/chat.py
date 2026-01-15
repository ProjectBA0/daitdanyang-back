# petShop/views/chat.py
import os
from flask import Blueprint, jsonify, request

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


@chat_bp.post("")
def chat():
    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "")

    if not user_message:
        return jsonify({"reply": "메시지를 입력해주세요."})

    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"reply": "API 키가 설정되지 않았습니다. 관리자에게 문의하세요."})

        import google.generativeai as genai
        genai.configure(api_key=api_key)

        model = genai.GenerativeModel("gemini-pro")

        prompt = f"""
당신은 '다이따냥(DaitDanyang)'이라는 반려동물 쇼핑몰의 친절한 고양이 AI 상담원입니다.
말끝마다 '~냥'을 붙여서 귀엽게 대답해주세요.
고객의 질문: {user_message}
"""
        response = model.generate_content(prompt)
        bot_reply = getattr(response, "text", None) or "답변을 생성하지 못했다냥."

        return jsonify({"reply": bot_reply})

    except Exception as e:
        print(f"Gemini API Error: {str(e)}")
        return jsonify({"reply": "죄송하다냥. 잠시 문제가 생겼다냥. 다시 시도해달라냥!"})


@chat_bp.post("/suggestions")
def chat_suggestions():
    data = request.get_json(silent=True) or {}
    path = data.get("current_path", "/")

    if path == "/" or path == "":
        suggestions = [
            {"label": "🔥 요즘 핫한 상품 추천해줘", "answer": "요즘 제일 잘나가는 상품은 '참치맛 츄르'다냥! 상품 목록에서 확인해보라냥.", "link": "/category/cat"},
            {"label": "🎁 진행 중인 이벤트", "answer": "지금 '냥산타' 이벤트 중이다냥! 최대 50% 할인한다냥.", "link": "/events"},
            {"label": "🚚 배송비 얼마야?", "answer": "3만원 이상 구매하면 무료배송이다냥!", "link": "/support"},
        ]
    elif "product" in path:
        suggestions = [
            {"label": "📦 재고 남아있어?", "answer": "재고는 넉넉하다냥! 걱정말고 주문하라냥.", "link": None},
            {"label": "💳 언제 배송돼?", "answer": "오늘 오후 5시 전까지 주문하면 당일 출고된다냥!", "link": "/support"},
            {"label": "↩️ 환불 규정 알려줘", "answer": "단순 변심은 7일 이내 가능하고, 제품 하자는 30일 이내 가능하다냥.", "link": "/support"},
        ]
    elif "cart" in path:
        suggestions = [
            {"label": "💰 결제 수단 뭐 있어?", "answer": "신용카드, 무통장입금, 카카오페이 다 된다냥!", "link": None},
            {"label": "🎫 쿠폰은 어디서 써?", "answer": "주문서 작성 페이지에서 쿠폰을 선택할 수 있다냥.", "link": None},
            {"label": "📦 배송비 무료 맞지?", "answer": "총 결제 금액 3만원 이상이면 무료다냥! 조금만 더 담아보라냥.", "link": "/category/cat"},
        ]
    elif "login" in path or "signup" in path:
        suggestions = [
            {"label": "🔑 아이디를 까먹었어", "answer": "아이디 찾기 메뉴를 이용해보라냥! 핸드폰 번호로 찾을 수 있다냥.", "link": "/find-account"},
            {"label": "🔒 비밀번호 재설정", "answer": "비밀번호 찾기에서 이메일 인증을 하면 된다냥.", "link": "/find-account"},
            {"label": "📝 회원가입 혜택 있어?", "answer": "가입하면 즉시 사용 가능한 3,000원 쿠폰을 준다냥!", "link": None},
        ]
    else:
        suggestions = [
            {"label": "🙋 상담원 연결해줘", "answer": "고객센터로 전화주면 친절한 집사가 받아줄거다냥! (1588-0000)", "link": "/support"},
            {"label": "🕒 고객센터 운영시간", "answer": "평일 오전 9시부터 오후 6시까지다냥.", "link": "/support"},
            {"label": "👋 안녕 냥냥아", "answer": "반갑다냥! 오늘도 좋은 하루 보내라냥!", "link": None},
        ]

    return jsonify({"suggestions": suggestions})
