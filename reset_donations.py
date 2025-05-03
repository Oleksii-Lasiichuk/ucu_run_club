import sqlite3
import os
import sys

# Path to the database
DB_PATH = os.path.join(os.path.dirname(__file__), 'running_event.db')

def get_db_connection():
    """Create a database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def reset_donations():
    """Delete all donations from the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get count of records that will be deleted
        count_result = conn.execute('SELECT COUNT(*) as count FROM donations').fetchone()
        deleted_count = count_result['count'] if count_result else 0
        
        # Delete all donation records
        cursor.execute('DELETE FROM donations')
        
        conn.commit()
        conn.close()
        
        print(f"✅ Всі {deleted_count} донатів було успішно видалено!")
        return True
    except Exception as e:
        print(f"❌ Помилка при видаленні донатів: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚨 УВАГА! Ця програма видалить ВСІ записи про донати з бази даних!")
    print("Ви впевнені, що хочете продовжити? (так/ні)")
    
    confirmation = input().lower()
    if confirmation in ('так', 'yes', 'y', 't'):
        print("Видаляємо всі донати...")
        reset_donations()
    else:
        print("❌ Операцію скасовано.")
