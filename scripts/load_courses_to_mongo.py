import os
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB_NAME", "aijs_capstone")

# Separate collections for each course type
FREE_UDEMY_COLLECTION = "free_udemy_courses"
PAID_UDEMY_COLLECTION = "paid_udemy_courses"
FREE_COURSERA_COLLECTION = "free_coursera_courses"
PAID_COURSERA_COLLECTION = "paid_coursera_courses"


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

    # Load all course files into separate collections
    # 1) Free Udemy courses
    load_csv_to_mongo("data/free_udemy_courses.csv", FREE_UDEMY_COLLECTION, db, clear_first=True)
    
    # 2) Paid Udemy courses
    load_csv_to_mongo("data/paid_udemy.csv", PAID_UDEMY_COLLECTION, db, clear_first=True)
    
    # 3) Free Coursera courses (use chunks if large)
    try:
        # Try to check file size first
        file_size = os.path.getsize("data/free_coursera_Courses.csv")
        if file_size > 10 * 1024 * 1024:  # If larger than 10MB, use chunks
            load_large_csv_in_chunks("data/free_coursera_Courses.csv", FREE_COURSERA_COLLECTION, db, clear_first=True)
        else:
            load_csv_to_mongo("data/free_coursera_Courses.csv", FREE_COURSERA_COLLECTION, db, clear_first=True)
    except Exception as e:
        print(f"Warning loading free Coursera: {e}")
        load_csv_to_mongo("data/free_coursera_Courses.csv", FREE_COURSERA_COLLECTION, db, clear_first=True)
    
    # 4) Paid Coursera courses (use chunks if large)
    try:
        file_size = os.path.getsize("data/paid_coursera.csv")
        if file_size > 10 * 1024 * 1024:  # If larger than 10MB, use chunks
            load_large_csv_in_chunks("data/paid_coursera.csv", PAID_COURSERA_COLLECTION, db, clear_first=True)
        else:
            load_csv_to_mongo("data/paid_coursera.csv", PAID_COURSERA_COLLECTION, db, clear_first=True)
    except Exception as e:
        print(f"Warning loading paid Coursera: {e}")
        # Try chunks as fallback
        load_large_csv_in_chunks("data/paid_coursera.csv", PAID_COURSERA_COLLECTION, db, clear_first=True)
    
    # Print summary
    print("\n" + "="*60)
    print("📊 Loading Summary")
    print("="*60)
    print(f"Free Udemy courses: {db[FREE_UDEMY_COLLECTION].count_documents({}):,}")
    print(f"Paid Udemy courses: {db[PAID_UDEMY_COLLECTION].count_documents({}):,}")
    print(f"Free Coursera courses: {db[FREE_COURSERA_COLLECTION].count_documents({}):,}")
    print(f"Paid Coursera courses: {db[PAID_COURSERA_COLLECTION].count_documents({}):,}")
    print("="*60)


if __name__ == "__main__":
    main()
