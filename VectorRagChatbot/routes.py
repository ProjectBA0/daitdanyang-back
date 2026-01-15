import asyncio
import json
import struct
import os
import numpy as np
from collections import Counter
from flask import request, jsonify, current_app, Response, stream_with_context, send_from_directory
from . import chatbot_bp

# from asgiref.sync import async_to_sync # 🦁 Removed: No longer needed

@chatbot_bp.route('/fast', methods=['POST'])
def chat_fast():
    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "")
    history = data.get("history", [])
    
    if not user_message:
        return jsonify({"reply": "메시지를 입력해주세요냥!"})
    
    brain = current_app.extensions.get('nyang_brain')
    
    try:
        formatted_history = []
        for h in history[-6:]: 
            role = 'user' if h['sender'] == 'user' else 'assistant'
            formatted_history.append({'user': h['text'] if role=='user' else '', 'assistant': h['text'] if role=='assistant' else ''})
        
        quick_reply = brain.generate_quick_chat(user_message, formatted_history)
        return jsonify({"reply": quick_reply})
        
    except Exception as e:
        print(f"❌ Fast Chat Error: {e}")
        return jsonify({"reply": "잠시만 기다려달라냥!"})

@chatbot_bp.route('/slow', methods=['POST'])
def chat_slow():
    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "")
    history = data.get("history", [])
    
    engine = current_app.extensions.get('nyang_engine')
    brain = current_app.extensions.get('nyang_brain')
    
    try:
        formatted_history = []
        for h in history[-6:]: 
            role = 'user' if h['sender'] == 'user' else 'assistant'
            formatted_history.append({'user': h['text'] if role=='user' else '', 'assistant': h['text'] if role=='assistant' else ''})

        # 2. Slow Talk (RAG Search & Synthesis) - Sync Call
        # ---------------------------------------------------------
        print(f"🦁 [RAG] Starting Hybrid Search for: '{user_message}'")
        tokens, s1_data, centroids, context_nodes = engine.search_hybrid(user_message, top_k=30)
        print(f"   - Vector Candidates: {len(s1_data)}")
        print(f"   - Reranked Context: {len(context_nodes)}")
        
        # Direct Sync Call
        sql_keywords = brain.extract_keywords(user_message)
        print(f"🦁 [RAG] SQL Keywords: {sql_keywords}")
        inventory_nodes = engine.search_sql(sql_keywords, limit=10)
        print(f"   - Inventory Matches: {len(inventory_nodes)}")
        
        tokens_rank = [("키워드", 1)]
        
        # Direct Sync Call
        print("🦁 [RAG] Generating Final Answer...")
        final_answer = brain.generate_final_answer(
            user_message, 
            context_nodes[:20], 
            inventory_nodes, 
            tokens_rank, 
            centroids, 
            formatted_history
        )
        
        if final_answer:
            final_answer = final_answer.replace("https://daitanyang.com", "")
            final_answer = final_answer.replace("http://daitanyang.com", "")
            final_answer = final_answer.replace("daitanyang.com", "")
            final_answer = final_answer.replace("www.daitanyang.com", "")
            final_answer = final_answer.replace("http://localhost:3000", "")
            final_answer = final_answer.replace("https://localhost:3000", "")

        sources = [{"title": n['title'], "score": n['score'], "link": n.get('link')} for n in inventory_nodes[:4]]
        
        # 🦁 Debug Info for Frontend
        debug_info = {
            "keywords": sql_keywords,
            "vector_candidates": len(s1_data),
            "reranked_candidates": len(context_nodes),
            "inventory_match": len(inventory_nodes),
            "centroids": [c['summary'] for c in centroids.values()]
        }

        return jsonify({
            "reply": final_answer,
            "sources": sources,
            "debug_info": debug_info
        })
        
    except Exception as e:
        print(f"❌ Slow Chat Error: {e}")
        return jsonify({"reply": f"오류가 났다냥: {str(e)}"})

@chatbot_bp.route('/suggestions', methods=['POST'])
def suggestions_endpoint():
    data = request.get_json(silent=True) or {}
    path = data.get("current_path", "/")
    brain = current_app.extensions.get('nyang_brain')
    
    if not brain: return jsonify({"suggestions": []})

    try:
        # Sync Call
        suggestions = brain.generate_suggestions(path)
        return jsonify({"suggestions": suggestions})
    except Exception as e:
        print(f"Suggestion Error: {e}")
        return jsonify({"suggestions": []})

# 🦁 3D Atlas Visualization Routes 🦁

@chatbot_bp.route('/atlas')
def serve_atlas():
    # Serve the static HTML file
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), 'atlas.html')

@chatbot_bp.route('/atlas/config')
def get_atlas_config():
    engine = current_app.extensions.get('nyang_engine')
    if not engine: return jsonify({}), 503
    return jsonify({
        "trees": engine.hierarchies, 
        "path_map": engine.path_to_id, 
        "homepage_ids": engine.homepage_ids
    })

@chatbot_bp.route('/atlas/binary')
def get_atlas_binary():
    engine = current_app.extensions.get('nyang_engine')
    if not engine or engine.coords_cache is None: return Response(status_code=503)
    
    count = len(engine.coords_cache)
    header = struct.pack('<I', count)
    payload = header + engine.coords_cache.tobytes() + engine.colors_cache.tobytes() + engine.cat_id_cache.tobytes()
    
    return Response(payload, mimetype="application/octet-stream")

# 🦁 Streaming Reasoning for 3D Dashboard 🦁

def convert_numpy(obj):
    if isinstance(obj, np.integer): return int(obj)
    elif isinstance(obj, np.floating): return float(obj)
    elif isinstance(obj, np.ndarray): return obj.tolist()
    elif isinstance(obj, list): return [convert_numpy(i) for i in obj]
    elif isinstance(obj, dict): return {k: convert_numpy(v) for k, v in obj.items()}
    return obj

def sse_msg(event, data):
    safe_data = convert_numpy(data)
    return f"event: {event}\ndata: {json.dumps(safe_data, ensure_ascii=False)}\n\n"

@chatbot_bp.route('/stream_reasoning')
def stream_reasoning():
    q = request.args.get('q', '')
    h = request.args.get('h', '[]')
    
    if not q: return Response("event: done\ndata: {}\n\n", mimetype="text/event-stream")

    engine = current_app.extensions.get('nyang_engine')
    brain = current_app.extensions.get('nyang_brain')

    def generate():
        try:
            history = json.loads(h) if h else []
            req_id = "stream_" + os.urandom(4).hex()
            
            # 1. Perception
            yield sse_msg("log", {'step': 'PERCEPTION', 'msg': f'🧠 지배인님의 의도 파악 중: "{q}"'})
            
            # 2. Tokenizing & Retrieval
            yield sse_msg("log", {'step': 'RETRIEVAL', 'msg': '📡 [Phase 1] 34.6만 건의 벡터 공간 탐색...'})
            tokens, s1_data, centroids, context_nodes = engine.search_hybrid(q, top_k=50, request_id=req_id)
            
            yield sse_msg("log", {'step': 'TOKENIZING', 'msg': f'🔑 키워드: {tokens[:5]}'})
            yield sse_msg("log", {'step': 'RETRIEVAL', 'msg': '🌌 [Step 2] 의미론적 군집 분석 중...'})
            
            yield sse_msg("swarm_data", {"s1_nodes": s1_data, "centroids": centroids})
            
            # 3. Ranking
            yield sse_msg("log", {'step': 'RETRIEVAL', 'msg': '🎯 [Phase 2] 벡터 유사도 + 군집 밀도 가중치 적용...'})
            
            top_15 = context_nodes[:15]
            yield sse_msg("nodes", top_15)
            
            # 4. Reflection
            yield sse_msg("log", {'step': 'REFLECTION', 'msg': '🤔 [Brain] 의도 분석 및 정밀 검색...'})
            
            # Async call bridge for Brain methods
            new_queries = run_async(brain.generate_search_queries, q, top_15, centroids, history)
            
            if new_queries:
                yield sse_msg("log", {'step': 'REFLECTION', 'msg': f'💡 정밀 검색 쿼리: {new_queries}'})
            else:
                yield sse_msg("log", {'step': 'REFLECTION', 'msg': '😺 단순 대화 모드로 전환!'})

            # 5. Synthesis
            yield sse_msg("log", {'step': 'SYNTHESIS', 'msg': '✨ 최종 답변 작성 중...'})
            
            # We don't generate the full text here to save time for visualization, 
            # or we could call generate_final_answer if needed.
            # For visualization purpose, we finish here.
            
            yield sse_msg("log", {'step': 'done', 'msg': '🦁 냥이 임무 완료!'})
            yield sse_msg("done", {})
            
        except Exception as e:
            print(f"Stream Error: {e}")
            yield sse_msg("error", {"msg": str(e)})
            yield sse_msg("done", {})

    return Response(stream_with_context(generate()), mimetype="text/event-stream")