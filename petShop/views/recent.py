from flask import Blueprint, request, jsonify, make_response

recent_bp = Blueprint("recent", __name__, url_prefix="/api/recent")

@recent_bp.post("/view")
def recent_view():
    data = request.get_json(silent=True) or {}
    product_id = str(data.get("productId", ""))

    recent = request.cookies.get("recent", "")
    recent_list = recent.split(",") if recent else []

    recent_list = [x for x in recent_list if x != product_id]
    recent_list.insert(0, product_id)
    recent_list = recent_list[:20]

    resp = make_response(jsonify({"ok": True}))
    resp.set_cookie("recent", ",".join(recent_list), max_age=60*60*24*30)
    return resp


@recent_bp.get("")
def recent_list():
    recent = request.cookies.get("recent", "")
    ids = recent.split(",") if recent else []
    return jsonify({"items": ids})