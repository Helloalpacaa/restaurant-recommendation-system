import json
import pandas as pd
import numpy as np
from tqdm import tqdm
import psycopg2
from psycopg2.extras import execute_batch
from sentence_transformers import SentenceTransformer
import re

def load_restaurant_data(business_path):
    """Load and filter restaurant businesses from Yelp dataset"""
    restaurants = []
    
    with open(business_path, 'r', encoding='utf-8') as f:
        for line in tqdm(f, desc="Loading businesses"):
            business = json.loads(line)
            # Filter for restaurants only - handle None categories
            categories = business.get('categories', '')
            if categories and 'Restaurants' in categories:  # Check if categories exists and contains 'Restaurants'
                # Handle missing price level data
                try:
                    price_level = len(business.get('attributes', {}).get('RestaurantsPriceRange2', '$')) if business.get('attributes') is not None else 1
                except (AttributeError, TypeError):
                    price_level = 1  # Default to lowest price level if missing
                
                restaurant = {
                    'business_id': business['business_id'],
                    'name': business['name'],
                    'address': business.get('address', ''),
                    'city': business.get('city', ''),
                    'state': business.get('state', ''),
                    'categories': categories,
                    'price_level': price_level,
                    'stars': float(business.get('stars', 0)),
                    'review_count': business.get('review_count', 0)
                }
                restaurants.append(restaurant)
                
                # Limit to first 50000 restaurants for testing
                if len(restaurants) >= 50000:
                    break
    
    return pd.DataFrame(restaurants)

def load_reviews(review_path, restaurant_ids):
    """Load reviews for restaurants"""
    reviews = []
    
    with open(review_path, 'r', encoding='utf-8') as f:
        for line in tqdm(f, desc="Loading reviews"):
            review = json.loads(line)
            if review['business_id'] in restaurant_ids:
                reviews.append({
                    'review_id': review['review_id'],
                    'business_id': review['business_id'],
                    'user_id': review['user_id'],
                    'stars': float(review['stars']),
                    'text': review['text'],
                    'date': review['date']
                })
                
                # Limit reviews per restaurant
                if len(reviews) >= 500000:
                    break
    
    return pd.DataFrame(reviews)

def generate_embeddings(df_reviews):
    """Generate embeddings for restaurants using review text"""
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    restaurant_texts = {}
    for _, row in df_reviews.iterrows():
        if row['business_id'] not in restaurant_texts:
            restaurant_texts[row['business_id']] = []
        restaurant_texts[row['business_id']].append(row['text'])
    
    embeddings = {}
    for rest_id, texts in tqdm(restaurant_texts.items(), desc="Generating embeddings"):
        # Combine all reviews and get embedding
        combined_text = " ".join(texts[:5])  # Use first 5 reviews
        embedding = model.encode(combined_text)
        embeddings[rest_id] = embedding
    
    return embeddings

def main():
    # Database connection parameters
    db_params = {
        'dbname': 'restaurant_db',
        'user': 'helloalpacaa',  # your PostgreSQL username
        'password': '',  # your PostgreSQL password if any
        'host': 'localhost'
    }
    
    # Load and process restaurant data
    print("Loading restaurant data...")
    df_restaurants = load_restaurant_data('yelp_academic_dataset_business.json')
    
    # Load reviews for restaurants
    print("Loading reviews...")
    restaurant_ids = set(df_restaurants['business_id'])
    df_reviews = load_reviews('yelp_academic_dataset_review.json', restaurant_ids)
    
    # Generate embeddings
    print("Generating embeddings...")
    embeddings = generate_embeddings(df_reviews)
    
    # Save to database
    print("Saving to database...")
    conn = psycopg2.connect(**db_params)
    cur = conn.cursor()
    
    # Insert restaurants
    restaurant_data = [
        (row['business_id'], row['name'], row['address'], row['city'], 
         row['state'], row['categories'], row['price_level'], 
         row['stars'], row['review_count'])
        for _, row in df_restaurants.iterrows()
    ]
    
    execute_batch(cur, """
        INSERT INTO restaurants 
        (restaurant_id, name, address, city, state, categories, 
         price_level, avg_rating, review_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (restaurant_id) DO NOTHING
    """, restaurant_data)
    
    # Insert reviews
    review_data = [
        (row['review_id'], row['business_id'], row['user_id'], 
         row['stars'], row['text'], row['date'])
        for _, row in df_reviews.iterrows()
    ]
    
    execute_batch(cur, """
        INSERT INTO ratings 
        (review_id, restaurant_id, user_id, rating, review_text, review_date)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (review_id) DO NOTHING
    """, review_data)
    
    # Insert embeddings
    embedding_data = [
        (rest_id, embedding.tolist())
        for rest_id, embedding in embeddings.items()
    ]
    
    execute_batch(cur, """
        INSERT INTO restaurant_embeddings (restaurant_id, embedding)
        VALUES (%s, %s)
        ON CONFLICT (restaurant_id) DO NOTHING
    """, embedding_data)
    
    conn.commit()
    conn.close()
    
    print("Processing complete!")

if __name__ == "__main__":
    main()