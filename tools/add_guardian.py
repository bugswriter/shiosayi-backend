import sqlite3
from datetime import datetime
import uuid

def prompt_guardian_details():
    print("\nEnter guardian details:")
    name = input("Name: ").strip()
    email = input("Email: ").strip()
    tier = input("Tier (tier1 / tier2 / tier3): ").strip()
    
    guardian_id = f"g{uuid.uuid4().hex[:6]}"
    token = uuid.uuid4().hex
    joined_at = datetime.now().isoformat()
    
    return (guardian_id, name, email, tier, token, joined_at)

def insert_guardian(db_path, data):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        INSERT INTO guardians (id, name, email, tier, token, joined_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    db_path = "shiosayi_test.db"  # Change this path if needed
    
    while True:
        data = prompt_guardian_details()
        insert_guardian(db_path, data)
        print(f"\n✅ Guardian added successfully!\nID: {data[0]}\nToken: {data[4]}")
        
        cont = input("\nDo you want to add another guardian? (y/n): ").strip().lower()
        if cont != 'y':
            break

    print("\n🎉 Done adding guardians.")

