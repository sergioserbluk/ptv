from flask import Blueprint
from . import admin, lineup, export, catalog  # asegúrate de que estos archivos existen

def register_blueprints(app):
    app.register_blueprint(admin.bp,   url_prefix="/api/admin")
    app.register_blueprint(lineup.bp,  url_prefix="/api")
    app.register_blueprint(export.bp,  url_prefix="/api")
    app.register_blueprint(catalog.bp, url_prefix="/api")
