# app.py
# ────────────────────────────────────────────────────────────
# Roblox helper micro-service
#   • /get_user_id?username=<name>   → { user_id: … }
#   • /avatar/<user_id>              → 302 → head-shot PNG
# ────────────────────────────────────────────────────────────
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)                         # allow all origins

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
    payload = {"usernames": [username], "excludeBannedUsers": True}
    r = requests.post(USERNAME_API, json=payload, timeout=5)
    r.raise_for_status()
    arr = r.json().get("data", [])
    if not arr:
        raise ValueError("not-found")
    return arr[0]["id"]


def resolve_headshot(uid: int) -> str:
    """
    Ask Roblox Thumbnails API for the CDN image.
    Fall back to the legacy thumbnail endpoint if needed.
    """
    try:
        meta = requests.get(THUMBNAIL_API.format(uid=uid), timeout=5).json()
        url = meta["data"][0]["imageUrl"]
        if url:
            return url
    except Exception:
        pass
    return LEGACY_THUMB.format(uid=uid)


# ───────────────────────── routes ───────────────────────────
@app.route("/get_user_id")
def route_get_user_id():
    username = request.args.get("username", "").strip()
    if not username:
        return jsonify(error="Username is required"), 400
    if username.startswith("@"):
        username = username[1:]

    try:
        uid = get_user_id(username)
        return jsonify(username=username, user_id=uid)
    except ValueError:
        return jsonify(error="not-found"), 404
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/avatar/<int:uid>")
def route_avatar(uid: int):
    """
    Redirect (302) to the actual PNG.  Browsers follow the redirect,
    and because the response is an image, there are no CORS worries.
    """
    return redirect(resolve_headshot(uid), code=302)


# ───────────────────────── main ─────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
