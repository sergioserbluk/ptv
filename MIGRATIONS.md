# Database migrations

1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Ejecutar migraciones pendientes:
   ```bash
   alembic upgrade head
   ```
3. Crear una nueva migración automática:
   ```bash
   alembic revision --autogenerate -m "mensaje"
   alembic upgrade head
   ```
