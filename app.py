# app.py
# ────────────────────────────────────────────────────────────
# Roblox helper micro-service
#   • /get_user_id?username=<name>   → { user_id: … }
#   • /avatar/<user_id>              → 302 → head-shot PNG
#     (both endpoints send the CORS header so the browser is happy)
# ────────────────────────────────────────────────────────────
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS, cross_origin
import requests

app = Flask(__name__)

# 🔑  Enable wildcard CORS on every normal response
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    allow_headers="*",
    expose_headers="*",
    methods=["GET", "POST", "OPTIONS"],
)

USERNAME_API = "https://users.roblox.com/v1/usernames/users"
THUMBNAIL_API = (
    "https://thumbnails.roblox.com/v1/users/avatar-headshot"
    "?userIds={uid}&size=150x150&format=Png&isCircular=false"
)
LEGACY_THUMB = (
    "https://www.roblox.com/headshot-thumbnail/image"
    "?userId={uid}&width=150&height=150&format=png"
)

# ───────────────────────── helpers ──────────────────────────
def get_user_id(username: str) -> int:
    """Call Roblox username API → integer userId (raises for not-found)."""
    payload = {"usernames": [username], "excludeBannedUsers": True}
    r = requests.post(USERNAME_API, json=payload, timeout=5)
    r.raise_for_status()
    arr = r.json().get("data", [])
    if not arr:
        raise ValueError("not-found")
    return arr[0]["id"]


def resolve_headshot(uid: int) -> str:
    """Return a 150×150 PNG CDN URL for the user’s headshot."""
    try:
        meta = requests.get(THUMBNAIL_API.format(uid=uid), timeout=5).json()
        url = meta["data"][0]["imageUrl"]
        if url:
            return url
    except Exception:
        pass
    # fallback legacy thumbnail
    return LEGACY_THUMB.format(uid=uid)

# ───────────────────────── routes ───────────────────────────
@app.route("/get_user_id")
@cross_origin()  # belt-and-suspenders: add CORS even on error paths
def route_get_user_id():
    username = request.args.get("username", "").strip()
    if not username:
        return jsonify(error="Username is required"), 400
    if username.startswith("@"):
        username = username[1:]

    try:
        uid = get_user_id(username)
        return jsonify(username=username, user_id=uid)
    except ValueError:            # Roblox says “not found”
        return jsonify(error="not-found"), 404
    except Exception as e:        # network errors, etc.
        return jsonify(error=str(e)), 500


@app.route("/avatar/<int:uid>")
@cross_origin()  # CORS on the redirect response, just in case
def route_avatar(uid: int):
    """
    302-redirect to the PNG. Browsers follow redirects automatically,
    and because the final response is an image, CORS no longer matters.
    """
    return redirect(resolve_headshot(uid), code=302)

# ───────────────────────── main ─────────────────────────────
if __name__ == "__main__":
    # When run locally:  http://localhost:10000
    app.run(host="0.0.0.0", port=10000)
