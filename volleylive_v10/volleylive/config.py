import os
class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY","dev_key")
    DB_PATH = os.path.join(os.path.dirname(__file__), "matches.db")
