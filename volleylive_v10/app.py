from volleylive import create_app, socketio as _sio

if __name__ == "__main__":
    res = create_app()
    # Soporta tanto (app, socketio) como sólo app (por si alguna vez cambia)
    if isinstance(res, tuple):
        app, socketio = res
    else:
        app = res
        socketio = _sio

    port = 5000
    print(f" * Running http://0.0.0.0:{port}")
    socketio.run(app, host="0.0.0.0", port=port)
