"""
Database Reset Script
Deletes and recreates the database with correct schema
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.database.models import Base
from backend.database.session import engine

def reset_database():
    """Drop all tables and recreate them"""
    db_path = "psur_system.db"
    
    # Close any existing connections
    engine.dispose()
    
    # Delete the database file if it exists
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f"Deleted old database: {db_path}")
        except Exception as e:
            print(f"Error deleting database: {e}")
            print("Please close the backend server and try again")
            return False
    
    # Create all tables
    print("Creating fresh database with new schema...")
    Base.metadata.create_all(bind=engine)
    print("Database recreated successfully!")
    print("\nYou can now restart the backend server.")
    return True

if __name__ == "__main__":
    reset_database()
