release: python -c 'from app import db, app; app.app_context().push(); db.create_all()'
web: gunicorn app:app
