import os
import sqlite3
from app import app
from models import db

# Path to the database
DB_PATH = os.path.join(app.instance_path, 'dental_clinic.db')
BACKUP_PATH = os.path.join(app.instance_path, 'dental_clinic_backup.db')

def backup_database():
    """Create a backup of the current database"""
    if os.path.exists(DB_PATH):
        # Create a backup
        print(f"Creating backup of database at {BACKUP_PATH}")
        if os.path.exists(BACKUP_PATH):
            os.remove(BACKUP_PATH)
        
        # Copy the database file
        with open(DB_PATH, 'rb') as src, open(BACKUP_PATH, 'wb') as dst:
            dst.write(src.read())
        
        print("Backup created successfully")
        return True
    return False

def migrate_data():
    """Migrate data from the old database to the new one"""
    if not os.path.exists(BACKUP_PATH):
        print("No backup database found")
        return False
    
    # Connect to the old database
    old_conn = sqlite3.connect(BACKUP_PATH)
    old_cursor = old_conn.cursor()
    
    # Connect to the new database
    new_conn = sqlite3.connect(DB_PATH)
    new_cursor = new_conn.cursor()
    
    # Get all tables from the old database
    old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = old_cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        if table_name == 'sqlite_sequence':
            continue
        
        print(f"Migrating table: {table_name}")
        
        # Get all data from the old table
        old_cursor.execute(f"SELECT * FROM {table_name}")
        rows = old_cursor.fetchall()
        
        if not rows:
            print(f"No data in table {table_name}")
            continue
        
        # Get column names from the old table
        old_cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [column[1] for column in old_cursor.fetchall()]
        
        # Get column names from the new table
        new_cursor.execute(f"PRAGMA table_info({table_name})")
        new_columns = [column[1] for column in new_cursor.fetchall()]
        
        # Find common columns
        common_columns = [col for col in columns if col in new_columns]
        
        if not common_columns:
            print(f"No common columns found for table {table_name}")
            continue
        
        # Create placeholders for the INSERT statement
        placeholders = ", ".join(["?" for _ in common_columns])
        columns_str = ", ".join(common_columns)
        
        # Insert data into the new table
        for row in rows:
            # Extract values for common columns
            values = [row[columns.index(col)] for col in common_columns]
            
            try:
                new_cursor.execute(f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})", values)
            except sqlite3.Error as e:
                print(f"Error inserting into {table_name}: {e}")
                continue
        
        new_conn.commit()
        print(f"Migrated {len(rows)} rows from table {table_name}")
    
    old_conn.close()
    new_conn.close()
    print("Data migration completed successfully")
    return True

def main():
    """Main migration function"""
    print("Starting database migration...")
    
    # Create a backup of the current database
    if not backup_database():
        print("No existing database to backup")
    
    # Remove the current database to create a new one with the updated schema
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Removed old database")
    
    # Create a new database with the updated schema
    with app.app_context():
        db.create_all()
        print("Created new database with updated schema")
    
    # Migrate data from the old database to the new one
    if os.path.exists(BACKUP_PATH):
        migrate_data()
    
    print("Migration completed successfully!")

if __name__ == "__main__":
    main()
