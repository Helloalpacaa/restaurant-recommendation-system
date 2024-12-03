import psycopg2
import numpy as np
from tqdm import tqdm
from collections import defaultdict
from decimal import Decimal

def convert_decimal(value):
    """Convert decimal to float if needed"""
    return float(value) if isinstance(value, Decimal) else value

def calculate_metrics(original, recommendations):
    """Calculate multiple evaluation metrics for recommendations"""
    metrics = {
        'category_match': 0.0,
        'price_level_accuracy': 0.0,
        'rating_similarity': 0.0,
        'location_relevance': 0.0,
        'variety_score': 0.0
    }
    
    # Convert decimal values to float
    original = {k: convert_decimal(v) for k, v in original.items()}
    recommendations = [{k: convert_decimal(v) for k, v in rec.items()} 
                      for rec in recommendations]
    
    # Category matching
    orig_cats = set(original['categories'].split(', '))
    category_scores = []
    unique_categories = set()
    
    for rec in recommendations:
        rec_cats = set(rec['categories'].split(', '))
        overlap = len(orig_cats.intersection(rec_cats))
        category_scores.append(overlap / len(orig_cats) if len(orig_cats) > 0 else 0)
        unique_categories.update(rec_cats)
    
    # Price level accuracy
    price_scores = [1 - abs(rec['price_level'] - original['price_level'])/4 
                   for rec in recommendations]
    
    # Rating similarity
    rating_scores = [1 - abs(rec['avg_rating'] - original['avg_rating'])/5 
                    for rec in recommendations]
    
    # Location relevance
    location_scores = [1.0 if rec['city'] == original['city'] and rec['state'] == original['state']
                      else 0.5 if rec['state'] == original['state']
                      else 0.0 
                      for rec in recommendations]
    
    # Calculate metrics
    metrics['category_match'] = float(np.mean(category_scores))
    metrics['price_level_accuracy'] = float(np.mean(price_scores))
    metrics['rating_similarity'] = float(np.mean(rating_scores))
    metrics['location_relevance'] = float(np.mean(location_scores))
    metrics['variety_score'] = float(len(unique_categories) / (len(recommendations) * 3))
    
    # Calculate overall score
    weights = {
        'category_match': 0.3,
        'price_level_accuracy': 0.2,
        'rating_similarity': 0.2,
        'location_relevance': 0.2,
        'variety_score': 0.1
    }
    
    metrics['overall_score'] = sum(float(metrics[metric]) * weights[metric] 
                                 for metric in weights.keys())
    
    return metrics

def evaluate_recommendations():
    conn = psycopg2.connect(
        dbname="restaurant_db",
        user="helloalpacaa",
        host="localhost"
    )
    cur = conn.cursor()
    
    # Get sample restaurants
    cur.execute("""
        SELECT DISTINCT r.restaurant_id, r.name, r.categories, r.price_level, 
               r.avg_rating, r.city, r.state
        FROM restaurants r
        JOIN restaurant_embeddings re ON r.restaurant_id = re.restaurant_id
        LIMIT 50
    """)
    test_restaurants = cur.fetchall()
    
    sql_metrics = defaultdict(list)
    vector_metrics = defaultdict(list)
    
    print("Evaluating recommendations...")
    for rest_data in tqdm(test_restaurants):
        rest_id = rest_data[0]
        original = {
            'categories': rest_data[2],
            'price_level': rest_data[3],
            'avg_rating': rest_data[4],
            'city': rest_data[5],
            'state': rest_data[6]
        }
        
        # SQL recommendations
        cur.execute("""
            SELECT 
                r2.name, r2.categories, r2.price_level, r2.avg_rating,
                r2.city, r2.state
            FROM restaurants r1
            JOIN restaurants r2 ON r1.restaurant_id != r2.restaurant_id
            WHERE r1.restaurant_id = %s
            ORDER BY (
                CASE WHEN r1.categories = r2.categories THEN 0.3 ELSE 0 END +
                (1 - ABS(r1.price_level - r2.price_level)::float/4) * 0.3 +
                (1 - ABS(r1.avg_rating - r2.avg_rating)::float/5) * 0.4
            ) DESC
            LIMIT 5
        """, (rest_id,))
        sql_recs = [dict(zip(['name', 'categories', 'price_level', 'avg_rating', 'city', 'state'], 
                            rec)) for rec in cur.fetchall()]
        
        # Vector recommendations
        cur.execute("""
            SELECT 
                r.name, r.categories, r.price_level, r.avg_rating,
                r.city, r.state
            FROM restaurant_embeddings re1
            JOIN restaurant_embeddings re2 ON re1.restaurant_id != re2.restaurant_id
            JOIN restaurants r ON re2.restaurant_id = r.restaurant_id
            WHERE re1.restaurant_id = %s
            ORDER BY 1 - (re1.embedding <=> re2.embedding) DESC
            LIMIT 5
        """, (rest_id,))
        vector_recs = [dict(zip(['name', 'categories', 'price_level', 'avg_rating', 'city', 'state'], 
                               rec)) for rec in cur.fetchall()]
        
        # Calculate metrics
        if sql_recs:
            sql_result = calculate_metrics(original, sql_recs)
            for metric, value in sql_result.items():
                sql_metrics[metric].append(value)
        
        if vector_recs:
            vector_result = calculate_metrics(original, vector_recs)
            for metric, value in vector_result.items():
                vector_metrics[metric].append(value)
    
    # Print results
    print("\nComprehensive Evaluation Results:")
    print("\nMetric                  SQL-based          Vector-based")
    print("=" * 60)
    
    for metric in sql_metrics.keys():
        sql_avg = np.mean(sql_metrics[metric])
        vector_avg = np.mean(vector_metrics[metric])
        print(f"{metric:<20} {sql_avg:>10.4f}        {vector_avg:>10.4f}")
    
    conn.close()

if __name__ == "__main__":
    evaluate_recommendations()