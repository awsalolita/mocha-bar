import os

from flask import Flask, request, jsonify, Response
from werkzeug.utils import secure_filename

app = Flask(__name__)



# Require an x-api-key header on any route under /api.
@app.before_request
def require_api_key():
    if request.path.startswith("/api"):
        if request.headers.get("x-api-key") != "something":
            return jsonify({"error": "unauthorized"}), 401


# Read the request body, handling JSON, form and raw content types.
@app.route("/data", methods=["POST"])
def get_data():
    if request.is_json:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "invalid JSON body"}), 400
        return jsonify({"source": "json", "data": data}), 200

    if request.form:
        return jsonify({"source": "form", "data": request.form.to_dict()}), 200

    raw = request.get_data(as_text=True)
    if raw:
        return jsonify({"source": "raw", "data": raw}), 200

    return jsonify({"error": "empty body"}), 400


# Path parameter validated as an integer.
@app.route("/items/<int:id>", methods=["GET"])
def get_by_id(id):
    return jsonify({"id": id}), 200


# Query parameters: single, typed and repeated values.
@app.route("/search", methods=["GET"])
def get_query_param():
    name = request.args.get("name", default="")
    limit = request.args.get("limit", default=10, type=int)
    tags = request.args.getlist("tag")

    return jsonify({"name": name, "limit": limit, "tags": tags}), 200


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# File upload via multipart/form-data with a field named "file".
@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "no 'file' field in request"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "no file selected"}), 400

    if not _allowed_file(file.filename):
        return jsonify({"error": "file type not allowed"}), 415

    filename = secure_filename(file.filename)
    save_path = os.path.join(UPLOAD_DIR, filename)
    file.save(save_path)

    return jsonify(
        {
            "message": "file uploaded",
            "filename": filename,
            "size_bytes": os.path.getsize(save_path),
        }
    ), 201


USERS = [{"id": i, "name": f"user-{i}"} for i in range(1, 101)]


# Pagination: returns a page slice plus navigation metadata.
@app.route("/users", methods=["GET"])
def list_users():
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=10, type=int)

    page = max(page, 1)
    per_page = min(max(per_page, 1), 100)

    total = len(USERS)
    total_pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    items = USERS[start:end]

    return jsonify(
        {
            "items": items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }
    ), 200


# Health check.
@app.route("/health", methods=["GET"])
def health():
    return Response("OK", status=200)


@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "not found"}), 404


@app.errorhandler(413)
def too_large(_):
    return jsonify({"error": "payload too large"}), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
