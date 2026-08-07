from flask import Flask

import logging
import sys
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/")
def hello():
  logger.info("hello endpoint hit")
  return "Hello, world!"

if __name__ == "__main__":
  app.run("0.0.0.0", 3000)
