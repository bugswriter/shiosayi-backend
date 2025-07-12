import sqlite3
from datetime import datetime

def prompt_film_details():
    print("\nEnter film details:")
    title = input("Title: ").strip()
    year = int(input("Year: ").strip())
    plot = input("Plot: ").strip()
    poster_url = input("Poster URL: ").strip()
    region = input("Region: ").strip()
    status = input("Status (orphan / adopted / abandoned): ").strip().lower()
    guardian_id = input("Guardian ID (leave blank if none): ").strip() or None
    magnet = input("Magnet link (optional): ").strip() or None
    updated_at = datetime.now().isoformat()
    
    return (title, year, plot, poster_url, region, guardian_id, status, magnet, updated_at)

def insert_film(db_path, film_data):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        INSERT INTO films (title, year, plot, poster_url, region, guardian_id, status, magnet, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, film_data)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    db_path = "shiosayi_test.db"  # Change path if your DB is elsewhere
    
    while True:
        film_data = prompt_film_details()
        insert_film(db_path, film_data)
        print("✅ Film added successfully!\n")
        
        cont = input("Do you want to add another film? (y/n): ").strip().lower()
        if cont != 'y':
            break

    print("🎬 Done adding films.")
