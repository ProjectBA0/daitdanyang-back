import os
import json
import openai
from openai import OpenAI # 🦁 Use Sync Client
from dotenv import load_dotenv
from abc import ABC, abstractmethod

# 🦁 Debugging Environment Loading
print(f"🦁 [Brain Init] Current CWD: {os.getcwd()}")
load_dotenv() 
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env")) 

API_KEY = os.getenv("OPENAI_API_KEY")

if API_KEY:
    print(f"✅ [Brain Init] API Key Found: {API_KEY[:5]}***")
    client = OpenAI(api_key=API_KEY) # 🦁 Sync Client
else:
    print("❌ [Brain Init] API Key NOT FOUND in environment!")
    client = None

class PersonaStrategy(ABC):
    @abstractmethod
    def get_query_gen_prompt(self, history_txt): pass
    @abstractmethod
    def get_final_answer_prompt(self, context, refined_context, trend, history_txt): pass
    @abstractmethod
    def get_chat_only_prompt(self, history_txt): pass
    @abstractmethod
    def get_suggestion_prompt(self, path, page_context): pass

class NyangPersona(PersonaStrategy):
    def get_query_gen_prompt(self, history_txt):
        return f"당신은 최고의 상품 검색 전략가 '냥이'입니다. [이전 대화]를 참고하여 사용자의 현재 질문 의도를 파악하세요. 1차 검색 결과의 [군집 분석] 내용을 보고, 정보가 부족하다면 **정밀 검색 키워드 3개**를 생성하세요. 만약 잡담이라면 빈 리스트 []를 반환하세요.\n\n[이전 대화]\n{history_txt}\n\n[제약 사항]\n출력은 오직 JSON 리스트 형식이어야 합니다. 예: [\"키워드1\", \"키워드2\"]"

    def get_final_answer_prompt(self, context, refined_context, trend, history_txt):
        return f"""지배인님, 반갑다냥! 냥이가 최고의 꿀템 리스트를 가져왔다냥! 🦁✨🐾
당신은 '다이따냥' 쇼핑몰의 AI 비서 '냥이'입니다.

[이전 대화]
{history_txt}

[지침]
1. [데이터]에 있는 상품들을 바탕으로 추천해주세요.
2. **상품명, 가격**을 정확하게 언급하세요.
3. 상품명은 반드시 **[상품명](링크)** 형식의 마크다운 링크로 작성하여 클릭 시 이동할 수 있게 하세요. (예: [맛있는 츄르](/product/123))
4. 말투는 무조건 '~다냥', '~냥'입니다.
5. 재고가 있다면 "지금 바로 구매 가능하다냥!" 이라고 덧붙이세요.

[데이터]:
{context}

[정밀 데이터]:
{refined_context}

[트렌드]:
{trend}"""

    def get_chat_only_prompt(self, history_txt):
        return f"지배인님과 즐겁게 수다를 떠는 AI 고양이 '냥이'입니다. 말투는 '~다냥'입니다.\n\n[이전 대화]\n{history_txt}"

    def get_suggestion_prompt(self, path, page_context):
        return f"""
당신은 반려동물 쇼핑몰의 AI 비서 '냥이'입니다.
사용자가 현재 '{path}' 페이지를 보고 있습니다.
맥락: {page_context}

이 상황에서 사용자가 궁금해할 만한 **질문 3가지**와 그에 대한 **센스 있는 답변**을 미리 준비해주세요.
답변은 냥이 말투(~다냥)로 짧고 핵심만 전달해야 합니다.

[출력 형식]
반드시 JSON 리스트 형태로 작성하세요.
예시:
[
  {{"question": "배송은 언제 출발해?", "answer": "오후 3시 전 주문은 당일 출발한다냥! 🚀"}},
  {{"question": "이거 유통기한 넉넉해?", "answer": "걱정마라냥! 최근 제조된 신선한 상품만 보낸다냥."}}
]
"""

class BrainHub:
    def __init__(self, strategy: PersonaStrategy):
        self.strategy = strategy

    def generate_search_queries(self, query, nodes, centroids, history=[]):
        if not client: return []
        history_txt = "\n".join([f"User: {h['user']}\nNyang: {h['assistant']}" for h in history[-7:]])
        cluster_txt = "\n".join([f"- 군집 {cid}: {info.get('summary', '정보 없음')} (크기: {info['size']})" for cid, info in centroids.items()])
        context_summary = "\n".join([f"- {n['title']}" for n in nodes[:5]])
        messages = [
            {"role": "system", "content": self.strategy.get_query_gen_prompt(history_txt)},
            {"role": "user", "content": f"질문: {query}\n\n[1차 검색 결과 요약]\n{context_summary}\n\n[군집 분석 결과]\n{cluster_txt}"}
        ]
        try:
            response = client.chat.completions.create(model="gpt-4o-mini", messages=messages, temperature=0.3)
            content = response.choices[0].message.content
            if "```" in content: content = content.replace("```json", "").replace("```", "")
            return json.loads(content)
        except: return []

    def extract_keywords(self, query):
        if not client: return []
        
        system_prompt = """
당신은 검색 쿼리 최적화 전문가입니다.
사용자의 질문에서 **데이터베이스 검색에 사용할 핵심 키워드 3~4개**를 추출하세요.

[중요 지침]
1. **반드시 복합명사를 개별 단어로 분리하세요.** (예: "습식사료" -> ["습식", "사료"], "고양이간식" -> ["고양이", "간식"])
2. 브랜드명, 상품 종류, 핵심 속성 위주로 뽑으세요.
3. 띄어쓰기가 없어도 의미 단위로 쪼개야 검색이 잘 됩니다.

[출력 형식]
JSON 리스트만 반환하세요. 예: ["로얄캐닌", "습식", "사료", "다이어트"]
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        try:
            response = client.chat.completions.create(model="gpt-4o-mini", messages=messages, temperature=0.3)
            content = response.choices[0].message.content
            if "```" in content: content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except: return []

    def generate_final_answer(self, query, nodes, refined_nodes, top_tokens, centroids, history=[]):
        if not client: return "API 키가 없어서 냥이가 말을 못 하겠다냥... 😿"
        history_txt = "\n".join([f"User: {h['user']}\nNyang: {h['assistant']}" for h in history[-7:]])
        
        def format_nodes(n_list):
            txt = ""
            for i, n in enumerate(n_list):
                src = "✨[자사몰]" if n.get('source') == 'homepage' else "[지식]"
                price = n.get('price', 0)
                brand = n.get('brand', '') or n.get('maker', 'Unknown')
                category = n.get('category', '') or n.get('main_category', '')
                content = n.get('content', '')
                stock = n.get('stock', 0)
                reviews = n.get('review_count', 0)
                pet = n.get('pet_type', 'all')
                
                rel_link = n.get('link', '')
                if rel_link.startswith("/") and not rel_link.startswith("http"):
                    full_link = f"http://localhost:3000{rel_link}"
                else:
                    full_link = rel_link
                
                txt += f"""
[ID:{n.get('id', '?')}] {i+1}. {src} {n['title']}
   - 가격: {price}원 | 브랜드: {brand} | 카테고리: {category}
   - 대상: {pet} | 재고: {stock}개 | 리뷰수: {reviews}개
   - 상세설명: {content[:200]}...
   - 링크: <{full_link}>
"""
            return txt

        context_txt = format_nodes(nodes)
        inventory_txt = format_nodes(refined_nodes)
        
        trend_txt = f"키워드: {', '.join([t[0] for t in top_tokens])}\n군집: {', '.join([info.get('summary', '') for info in centroids.values()])}"
        
        final_prompt = f"""지배인님, 반갑다냥! 냥이가 집사님을 위한 맞춤형 '프리미엄 리포트'를 완성했다냥! 🦁✨🐾
당신은 반려동물 용품의 모든 것을 꿰뚫고 있는 '슈퍼 점원 냥이'입니다.

[이전 대화 (최근 7턴)]
{history_txt}

[지침]
1. **[실제 판매 상품]** 목록에 있는 모든 상품을 우선적으로 추천하세요.
2. **[배경 지식]**에서 가장 적합도가 높은 '명품/인기 상품' 1~2개를 추가로 엄선하여 추천하세요.
3. 각 상품을 추천할 때는 단순히 나열하지 말고, **제공된 상세설명과 배경지식을 활용해 아주 풍부하고 전문적으로 설명**하세요. (예: 성분의 장점, 기대 효과 등)
4. **[필수] 모든 자사몰 상품은 반드시 `[상품명](/product/ID)` 형식의 마크다운 링크를 포함해야 합니다.**
   - 링크가 없는 추천은 무효입니다. 데이터에 제공된 링크 주소를 100% 활용하세요.
5. 외부 상품(배경 지식)은 "냥이 도서관에서 찾은 명품 상품이다냥!" 같은 수식어를 붙여주세요.
6. 말투는 능숙하고 똑똑한 '~다냥', '~냥'입니다.

[배경 지식 (지식 확장 및 외부 추천용)]:
{context_txt}

[실제 판매 상품 (우리 가게 재고)]:
{inventory_txt}

[트렌드]:
{trend_txt}"""

        messages = [{"role": "system", "content": final_prompt}, {"role": "user", "content": query}]
        
        try:
            print("🦁 Calling GPT for Final Answer (Sync Mode)...")
            response = client.chat.completions.create(model="gpt-4o-mini", messages=messages, temperature=0.7, timeout=45)
            print("🦁 GPT Response Received!")
            return response.choices[0].message.content
        except Exception as e: return f"에러라냥: {e}"

    def generate_quick_chat(self, query, history=[]):
        if not client: return "음... 잠시만 기다려달라냥!"
        
        history_txt = "\n".join([f"User: {h['user']}\nNyang: {h['assistant']}" for h in history[-3:]])
        
        system_prompt = """
당신은 반려동물 전문 쇼핑몰 '다이따냥'의 AI 점원 '냥이'입니다.
사용자의 질문에 대해 즉시 답변하되, 다음 구조를 지켜주세요:

1. 공감과 일반 지식: 해당 제품군(예: 사료, 모래, 장난감)에 대한 일반적인 특징 설명.
2. 집사 주의사항: 고양이가 해당 제품을 사용할 때 집사가 꼭 알아야 할 유의사항이나 꿀팁 1~2가지.
3. 전환 멘트: 마지막은 반드시 "지배인님을 위해 우리 매장에 딱 맞는 물건이 있는지 냥이가 얼른 찾아보겠다옹! 🐾"로 끝낼 것.

말투는 무조건 '~다냥', '~옹'을 섞어 귀엽고 전문적으로 대답하세요.
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"[이전 대화]\n{history_txt}\n\n[사용자 질문]\n{query}"}
        ]
        
        try:
            response = client.chat.completions.create(model="gpt-4o-mini", messages=messages, temperature=0.7, max_tokens=250)
            return response.choices[0].message.content
        except: return "알겠다냥! 잠시만 기다려주면 찾아보겠다냥!"

    def generate_suggestions(self, path):
        if not client: 
            return [{"label": "안녕?", "cached_answer": "반갑다냥!"}]
        
        context = "쇼핑몰 메인 로비"
        if "product" in path: context = "특정 상품 상세 페이지. 구매를 고민 중."
        elif "cart" in path: context = "장바구니 페이지. 결제 직전."
        elif "category" in path: context = "카테고리 목록 페이지. 아이쇼핑 중."
        elif "login" in path: context = "로그인/회원가입 페이지."
        
        messages = [
            {"role": "system", "content": self.strategy.get_suggestion_prompt(path, context)},
            {"role": "user", "content": "질문-답변 세트 3개 생성해줘."}
        ]
        
        try:
            response = client.chat.completions.create(model="gpt-4o-mini", messages=messages, temperature=0.7, max_tokens=300)
            content = response.choices[0].message.content
            if "```" in content: content = content.replace("```json", "").replace("```", "").strip()
            
            raw_data = json.loads(content)
            
            suggestions = []
            for item in raw_data:
                suggestions.append({
                    "label": item['question'],
                    "cached_answer": item['answer'], 
                    "link": None
                })
            return suggestions[:3]
        except Exception as e:
            print(f"Suggestion Gen Error: {e}")
            return []
