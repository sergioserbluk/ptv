from ..db import get_db
def get_db():
    return get_db.__wrapped__() if hasattr(get_db, "__wrapped__") else get_db()
