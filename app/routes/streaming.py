"""HTTP endpoints for controlling the video stream."""
from flask import Blueprint, jsonify

from ..streaming import stream_manager

streaming_bp = Blueprint("streaming", __name__)


@streaming_bp.post("/start")
def start_stream():
    url = stream_manager.start()
    return jsonify({"url": url})


@streaming_bp.post("/stop")
def stop_stream():
    stream_manager.stop()
    return jsonify({"stopped": True})


@streaming_bp.get("/url")
def stream_url():
    return jsonify({"url": stream_manager.get_url()})
