import psycopg2
import numpy as np
from tqdm import tqdm

def calculate_category_accuracy(original_categories, recommended_categories):
    """
    Calculate similarity score between original and recommended restaurant categories
    """
    # Convert category strings to sets
    orig_cats = set(original_categories.split(', '))
    rec_cats = set(recommended_categories.split(', '))
    
    # Calculate overlap
    overlap = len(orig_cats.intersection(rec_cats))
    
    # Return score as percentage of matching categories
    if len(orig_cats) == 0:
        return 0.0
    return overlap / len(orig_cats)

def evaluate_recommendations():
    # Connect to database
    conn = psycopg2.connect(
        dbname="restaurant_db",
        user="helloalpacaa",
        host="localhost"
    )
    cur = conn.cursor()
    
    # Get sample restaurants for testing
    cur.execute("""
        SELECT DISTINCT r.restaurant_id, r.name, r.categories
        FROM restaurants r
        JOIN restaurant_embeddings re ON r.restaurant_id = re.restaurant_id
        LIMIT 50
    """)
    test_restaurants = cur.fetchall()
    
    sql_scores = []
    vector_scores = []
    
    print("Evaluating recommendations...")
    for rest_id, name, categories in tqdm(test_restaurants):
        # Get SQL-based recommendations
        cur.execute("""
            WITH RestaurantMetrics AS (
                SELECT 
                    r.restaurant_id,
                    r.name,
                    r.categories,
                    r.price_level,
                    r.avg_rating
                FROM restaurants r
            )
            SELECT 
                r2.name,
                r2.categories
            FROM RestaurantMetrics r1
            JOIN RestaurantMetrics r2 ON r1.restaurant_id != r2.restaurant_id
            WHERE r1.restaurant_id = %s
            ORDER BY (
                CASE WHEN r1.categories = r2.categories THEN 0.3 ELSE 0 END +
                (1 - ABS(r1.avg_rating - r2.avg_rating)::float/5) * 0.7
            ) DESC
            LIMIT 5
        """, (rest_id,))
        sql_recs = cur.fetchall()
        
        # Get vector-based recommendations
        cur.execute("""
            SELECT 
                r.name,
                r.categories
            FROM restaurant_embeddings re1
            JOIN restaurant_embeddings re2 ON re1.restaurant_id != re2.restaurant_id
            JOIN restaurants r ON re2.restaurant_id = r.restaurant_id
            WHERE re1.restaurant_id = %s
            ORDER BY 1 - (re1.embedding <=> re2.embedding) DESC
            LIMIT 5
        """, (rest_id,))
        vector_recs = cur.fetchall()
        
        # Calculate average category match scores
        if sql_recs:
            sql_score = np.mean([calculate_category_accuracy(categories, rec[1]) for rec in sql_recs])
            sql_scores.append(sql_score)
            
        if vector_recs:
            vector_score = np.mean([calculate_category_accuracy(categories, rec[1]) for rec in vector_recs])
            vector_scores.append(vector_score)
    
    # Print results
    print("\nCategory Matching Score Results:")
    print(f"SQL-based Average Score: {np.mean(sql_scores):.4f}")
    print(f"SQL-based Score Range: {np.min(sql_scores):.4f} - {np.max(sql_scores):.4f}")
    print(f"\nVector-based Average Score: {np.mean(vector_scores):.4f}")
    print(f"Vector-based Score Range: {np.min(vector_scores):.4f} - {np.max(vector_scores):.4f}")
    
    conn.close()

if __name__ == "__main__":
    evaluate_recommendations()