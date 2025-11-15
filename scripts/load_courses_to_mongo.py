import pandas as pd
from pymongo import MongoClient

def load_csv_to_mongo(filepath, collection_name, db):
    print(f"Loading {filepath} into MongoDB collection {collection_name}...")
    df = pd.read_csv(filepath)
    data = df.to_dict('records')
    collection = db[collection_name]
    collection.delete_many({})  # clear old data
    collection.insert_many(data)
    print(f"Inserted {len(data)} documents into {collection_name}.")

def main():
    client = MongoClient("mongodb://localhost:27017/")
    db = client["courses_db"]

    load_csv_to_mongo("data/udemy.csv", "udemy_courses", db)
    load_csv_to_mongo("data/coursera_reviews2025.csv", "coursera_courses", db)

if __name__ == "__main__":
    main()
