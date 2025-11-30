import os
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB_NAME", "aijs_capstone")

# Separate collections for each course type
PAID_UDEMY_COLLECTION = "paid_udemy_courses"
PAID_COURSERA_COLLECTION = "paid_coursera_courses"
FREE_YOUTUBE_COLLECTION = "free_youtube_courses"


def load_csv_to_mongo(csv_path, collection_name, db, clear_first=True):
    """For smaller CSVs like Udemy."""
    print(f"\nLoading {csv_path} into collection '{collection_name}'...")
    collection = db[collection_name]

    df = pd.read_csv(csv_path)
    print(f"  → Loaded {len(df)} rows from {csv_path}")

    if clear_first:
        print("  → Clearing old data...")
        collection.delete_many({})

    print("  → Inserting into MongoDB Atlas...")
    records = df.to_dict(orient="records")
    if records:
        collection.insert_many(records)
    print(f"  ✓ Done. Inserted {len(records)} records.")


def load_large_csv_in_chunks(csv_path, collection_name, db, chunk_size=10000, clear_first=True):
    """For very large CSVs like Coursera (~691k rows)."""
    print(f"\nLoading LARGE CSV {csv_path} into collection '{collection_name}' in chunks...")
    collection = db[collection_name]

    if clear_first:
        print("  → Clearing old data...")
        collection.delete_many({})

    total_inserted = 0
    for i, chunk in enumerate(pd.read_csv(csv_path, chunksize=chunk_size)):
        records = chunk.to_dict(orient="records")
        if records:
            collection.insert_many(records)
            total_inserted += len(records)
            print(f"  → Chunk {i+1}: inserted {len(records)} rows (total {total_inserted})")

    print(f"  ✓ Done. Total inserted into '{collection_name}': {total_inserted}")


def main():
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI is not set. Check your .env file.")

    print(f"Connecting to MongoDB: {MONGO_URI}")
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    print(f"Connected to database: {DB_NAME}")

    # Load course files into separate collections
    # Note: Other course types (Udemy, Coursera) are already loaded, so skipping them
    
    # Load Free YouTube courses
    try:
        load_csv_to_mongo("data/free_youtube.csv", FREE_YOUTUBE_COLLECTION, db, clear_first=True)
    except Exception as e:
        print(f"Warning loading free YouTube: {e}")
    
    # Print summary
    print("\n" + "="*60)
    print("📊 Database Summary")
    print("="*60)
    print(f"Paid Udemy courses: {db[PAID_UDEMY_COLLECTION].count_documents({}):,}")
    print(f"Paid Coursera courses: {db[PAID_COURSERA_COLLECTION].count_documents({}):,}")
    print(f"Free YouTube courses: {db[FREE_YOUTUBE_COLLECTION].count_documents({}):,}")
    print("="*60)


if __name__ == "__main__":
    main()
