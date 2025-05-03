import sqlite3
import os
from flask import Flask

app = Flask(__name__)
app.config['DATABASE'] = os.path.join(app.root_path, 'running_event.db')

def get_db_connection():
    """Create a database connection"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def reset_donations():
    """Delete all donations from the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete all donations
        cursor.execute('DELETE FROM donations')
        
        conn.commit()
        conn.close()
        
        print("✅ All donations have been deleted successfully!")
        return True
    except Exception as e:
        print(f"❌ Error deleting donations: {str(e)}")
        return False

def reset_laps():
    """Delete all laps from the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete all laps
        cursor.execute('DELETE FROM laps')
        
        conn.commit()
        conn.close()
        
        print("✅ All laps have been deleted successfully!")
        return True
    except Exception as e:
        print(f"❌ Error deleting laps: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting emergency database reset...")
    print("1. Resetting donations...")
    reset_donations()
    
    print("\nDo you want to also delete all laps? (y/n)")
    choice = input().lower()
    if choice == 'y':
        print("2. Resetting laps...")
        reset_laps()
    
    print("\n✅ Reset completed!")
    print("You can now restart your application.")
