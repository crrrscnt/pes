#!/usr/bin/env python3
"""
Seed script to create test users and initial data
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models import User, UserRole, Base
from app.security import hash_password


def create_test_users():
    """Create test users"""
    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)

        users = [
            {
                "email": "user@test.com",
                "password": "password123",
                "role": UserRole.USER,   # ← enum, не строка
            },
            {
                "email": "admin@test.com",
                "password": "admin123",
                "role": UserRole.ADMIN,  # ← enum, не строка
            },
        ]

        for user_data in users:
            existing = db.query(User).filter(User.email == user_data["email"]).first()
            if existing:
                print(f"Already exists: {user_data['email']}")
                continue

            user = User(
                email=user_data["email"],
                hashed_password=hash_password(user_data["password"]),
                role=user_data["role"],
            )
            db.add(user)
            print(f"Created: {user_data['email']} ({user_data['role'].value})")

        db.commit()
        print("Seed data created successfully!")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_test_users()
