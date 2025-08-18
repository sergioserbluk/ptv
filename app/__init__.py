import os
from flask import Flask, render_template
from flask_socketio import SocketIO

try:
    import eventlet  # noqa: F401
    async_mode = "eventlet"
except Exception:  # pragma: no cover
    async_mode = "threading"

socketio = SocketIO(cors_allowed_origins="*", async_mode=async_mode)


def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["SECRET_KEY"] = "change-me"

    from .models import init_db
    from .services import set_socketio, state
    from .routes.torneos import torneos_bp
    from .routes.equipos import equipos_bp
    from .routes.partidos import partidos_bp
    from .routes.jugadores import jugadores_bp
    from .routes.streaming import streaming_bp
    from . import sockets
    from .errors import register_error_handlers

    init_db()
    set_socketio(socketio)

    app.register_blueprint(torneos_bp, url_prefix="/api/torneos")
    app.register_blueprint(equipos_bp, url_prefix="/api/equipos")
    app.register_blueprint(partidos_bp, url_prefix="/api/partidos")
    app.register_blueprint(jugadores_bp, url_prefix="/api/jugadores")
    app.register_blueprint(streaming_bp, url_prefix="/api/stream")

    sockets.register_socketio_events(socketio)
    register_error_handlers(app)

    @app.route("/")
    def index():
        return "OK · Control: /control · Display: /display · Admin: /admin"

    @app.route("/control")
    def control():
        return render_template("control.html")

    @app.route("/display")
    def display():
        return render_template("display.html", theme=state.get("theme", "dark"))

    @app.route("/admin")
    def admin():
        return render_template("admin.html")

    @app.route("/ads")
    def ads_list():
        files = []
        base = os.path.join(app.static_folder, "ads")
        if os.path.isdir(base):
            for f in sorted(os.listdir(base)):
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                    files.append(f"/static/ads/{f}")
        return {"images": files}

    return app
