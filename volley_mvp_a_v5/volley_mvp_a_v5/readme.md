¡gracias por avisar! te lo vuelvo a preparar.

**Descarga (zip nuevo):**
[volley\_mvp\_a\_v5.zip](sandbox:/mnt/data/volley_mvp_a_v5.zip)

### Qué incluye (MVP-A)

* `app.py` (Flask + Socket.IO; si no tenés WebSocket, hace fallback a polling).
* **/display** único (fuente navegador en OBS).
* **/control** con iframe de preview, tanteador, sets, “Siguiente set”, timer, tema, modos (intro/partido/tiempo\_fuera/entre\_sets/publicidad), rotador de publicidad (carpeta `static/ads/`), y **export CSV** de eventos.
* DB SQLite se crea sola al iniciar con un torneo/reglas/partido de ejemplo.
* 2 imágenes de ejemplo en `static/ads/`.

### Cómo correr

```bash
pip install -U flask flask-socketio==5.3.6 python-socketio==5.11.3 python-engineio==4.8.1
# opcional (para WebSocket reales; si falla, podés omitirlo)
pip install -U eventlet==0.33.3

python app.py
```

* Abrí **http\://IP\_DE\_TU\_PC:5000/control** → elegí torneo y partido → **Aplicar**.
* En OBS añadí **una sola** Fuente de Navegador apuntando a **http\://IP\_DE\_TU\_PC:5000/display**.
* Desde el control manejás puntos/sets/modos/timer y se actualiza en vivo el display.

¿querés que le sume ahora un mini panel para crear partidos/equipos desde la web, o lo dejamos así y seguimos con el siguiente módulo?
