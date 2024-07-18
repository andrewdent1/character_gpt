from app2 import app, db

with app.app_context():
    db.create_all()
    print("Database and User table created successfully!")
