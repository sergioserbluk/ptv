import os, json
from flask import Flask, render_template, jsonify, send_from_directory
from flask_socketio import SocketIO
from .config import Config
from .db import init_db
from .services.state import set_socketio as _set_socketio

socketio = None  # se setea en create_app()

def create_app():
    global socketio
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)

    # DB
    init_db(app)

    # SocketIO (eventlet si está instalado; si no, threading/polling)
    try:
        import eventlet  # noqa: F401
        async_mode = "eventlet"
    except Exception:
        async_mode = "threading"

    sio = SocketIO(app, cors_allowed_origins="*", async_mode=async_mode)
    socketio = sio
    _set_socketio(sio)

    # Blueprints REST
    from .api import register_blueprints
    register_blueprints(app)

    # Páginas
    @app.route("/")
    def index():
        return "OK · Control: /control · Display: /display · Admin: /admin"

    @app.route("/control")
    def control_page():
        return render_template("control.html")

    @app.route("/display")
    def display_page():
        return render_template("display.html")

    @app.route("/admin")
    def admin_page():
        return render_template("admin.html")

    # Lista de imágenes de publicidad
    @app.route("/ads")
    def ads_list():
        files = []
        base = os.path.join(app.static_folder, "ads")
        if os.path.isdir(base):
            for f in sorted(os.listdir(base)):
                if f.lower().endswith((".png",".jpg",".jpeg",".gif",".webp")):
                    files.append(f"/static/ads/{f}")
        return {"images": files}

    # Presets de layout
    @app.route("/layouts/<path:filename>")
    def layouts_file(filename):
        return send_from_directory(os.path.join(app.static_folder, "layouts"), filename)

    # Socket handlers
    from .sockets.overlay import register_socketio
    register_socketio(sio)

    print(f" * SocketIO async_mode={async_mode}")
    return app, sio   # ← IMPORTANTE: devolvemos (app, socketio)
