from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # ← This enables CORS

API_ENDPOINT = "https://users.roblox.com/v1/usernames/users"


def get_user_id(username):
    request_payload = {"usernames": [username], "excludeBannedUsers": True}
    response_data = requests.post(API_ENDPOINT, json=request_payload)
    response_data.raise_for_status()
    data = response_data.json().get("data", [])
    if not data:
        raise ValueError(f"No user found for username '{username}'.")
    return data[0]["id"]


@app.route("/get_user_id", methods=["GET"])
def handle_get_user_id():
    username = request.args.get("username", "").strip()
    if not username:
        return jsonify({"error": "Username is required"}), 400

    if username.startswith("@"):
        username = username[1:]

    try:
        user_id = get_user_id(username)
        return jsonify({"username": username, "user_id": user_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
