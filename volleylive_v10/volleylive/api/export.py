import io, csv
from flask import Blueprint, request, send_file
from ..services.util_db import get_db

bp = Blueprint("export", __name__)

@bp.get("/events/export.csv")
def export_events():
    match_id = request.args.get("match_id", type=int)
    if not match_id: return ("match_id requerido", 400)
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id,set_number,ts,type,payload_json FROM events WHERE match_id=? ORDER BY id", (match_id,))
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["id","set","timestamp","type","payload_json"])
    for r in c.fetchall():
        w.writerow([r[0], r[1], r[2], r[3], r[4]])
    data = out.getvalue().encode("utf-8")
    return send_file(io.BytesIO(data), mimetype="text/csv", as_attachment=True,
                     download_name=f"match_{match_id}_events.csv")
