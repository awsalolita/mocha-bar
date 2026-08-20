from flask import Flask

import logging
import sys

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

## middleware
@app.before_request
def require_api_key():
    if request.path.startswith("/api"):
        if request.path.startswith("/api/client"):
            return None
        if not request.headers.get("X-API-Key"):
            return jsonify({"error": "unauthorized"}), 401

@app.route("/")
def hello():
  logger.info("hello endpoint hit")
  return "Hello, world!"

if __name__ == "__main__":
  app.run("0.0.0.0", 3000)
