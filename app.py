# app.py
# ────────────────────────────────────────────────────────────
# Roblox helper micro-service
#   • /lookup?username=<name>
#       → {
#           username, user_id,
#           in_blooming, blooming_role,
#           in_merkaz,  merkaz_role
#         }
#   • /get_user_id?username=<name>   → { user_id: … }   (alias)
#   • /avatar/<user_id>              → 302 → head-shot PNG
# ────────────────────────────────────────────────────────────
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS, cross_origin
import requests

app = Flask(__name__)
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    allow_headers="*",
    expose_headers="*",
    methods=["GET", "POST", "OPTIONS"],
)

# ── Roblox API endpoints ────────────────────────────────────
USERNAME_API  = "https://users.roblox.com/v1/usernames/users"
GROUPS_API    = "https://groups.roblox.com/v2/users/{uid}/groups/roles"
THUMBNAIL_API = (
    "https://thumbnails.roblox.com/v1/users/avatar-headshot"
    "?userIds={uid}&size=150x150&format=Png&isCircular=false"
)
LEGACY_THUMB  = (
    "https://www.roblox.com/headshot-thumbnail/image"
    "?userId={uid}&width=150&height=150&format=png"
)

# שתי הקבוצות הרלוונטיות
BLOOMING_ID = 15843070
MERKAZ_ID   = 12470729

# ───────────────────────── helpers ──────────────────────────
def get_user_id(username: str) -> int:
    """Roblox username → userId"""
    payload = {"usernames": [username], "excludeBannedUsers": True}
    r = requests.post(USERNAME_API, json=payload, timeout=5)
    r.raise_for_status()
    data = r.json().get("data", [])
    if not data:
        raise ValueError("not-found")
    return data[0]["id"]


def get_groups(uid: int) -> list[dict]:
    """Return list of groups (and roles) the user belongs to."""
    url = GROUPS_API.format(uid=uid)
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    return r.json().get("data", [])


def resolve_headshot(uid: int) -> str:
    """Return a 150×150 PNG CDN URL for the user’s headshot."""
    try:
        meta = requests.get(THUMBNAIL_API.format(uid=uid), timeout=5).json()
        url = meta["data"][0]["imageUrl"]
        if url:
            return url
    except Exception:
        pass
    return LEGACY_THUMB.format(uid=uid)

# ───────────────────────── routes ───────────────────────────
@app.route("/lookup")
@cross_origin()
def route_lookup():
    """Username → userId + membership flags + roles"""
    username = request.args.get("username", "").strip()
    if not username:
        return jsonify(error="Username is required"), 400
    if username.startswith("@"):
        username = username[1:]

    try:
        uid = get_user_id(username)

        # דגלים ותפקידים
        in_blooming = in_merkaz = False
        blooming_role = merkaz_role = None

        for g in get_groups(uid):
            gid = g["group"]["id"]
            role = g["role"]["name"]
            if gid == BLOOMING_ID:
                in_blooming, blooming_role = True, role
            elif gid == MERKAZ_ID:
                in_merkaz, merkaz_role = True, role

        return jsonify(
            username=username,
            user_id=uid,
            in_blooming=in_blooming,
            blooming_role=blooming_role,
            in_merkaz=in_merkaz,
            merkaz_role=merkaz_role,
        )
    except ValueError:
        return jsonify(error="not-found"), 404
    except requests.RequestException:
        return jsonify(error="roblox-api"), 503
    except Exception as e:
        return jsonify(error=str(e)), 500


# alias ישן ל-backward-compat
@app.route("/get_user_id")
@cross_origin()
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
@cross_origin()
def route_avatar(uid: int):
    """Redirect (302) to the user’s head-shot image"""
    return redirect(resolve_headshot(uid), code=302)

# ───────────────────────── main ─────────────────────────────
if __name__ == "__main__":
    # http://localhost:10000
    app.run(host="0.0.0.0", port=10000)
