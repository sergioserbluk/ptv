# Requisitos de hardware y configuración básica

## Requisitos mínimos de hardware

- **CPU:** procesador moderno de cuatro núcleos (Intel i5/AMD Ryzen 5 o superior).
- **Memoria:** al menos 8 GB de RAM.
- **GPU:** recomendada para codificación por hardware (NVIDIA NVENC, AMD VCE o Intel QuickSync).
- **Red:** conexión estable de al menos 10 Mbps de subida para transmitir en 1080p a 30 fps.

## Configuración rápida en OBS

1. **Fuente de video:** agregar "Captura de ventana" o "Captura de juego" según corresponda.
2. **Ajustes de salida:**
   - Modo de salida: Avanzado.
   - Codificador: usar codificación por hardware si está disponible (NVENC, VCE, QuickSync).
   - Bitrate de video: 4500‑6000 kbit/s para 1080p, 2500‑4000 kbit/s para 720p.
3. **Ajustes de video:**
   - Resolución base y de salida según la fuente (1920x1080 recomendado).
   - FPS: 30 o 60 según la potencia disponible.
4. **Servidor de transmisión:**
   - Para RTMP: ingresar `rtmp://<servidor>/live` como URL y una clave de transmisión.
   - Para WebRTC: utilizar un complemento o script que exponga la conexión WebRTC y pegar la URL que devuelve el backend (`/api/stream/url`).
5. **Iniciar transmisión:** una vez configurado, presionar "Iniciar transmisión" en OBS.

Estos parámetros proporcionan una base funcional; pueden ajustarse según el ancho de banda y la potencia del hardware disponible.
