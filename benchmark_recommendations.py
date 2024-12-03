import psycopg2
import time
from tqdm import tqdm
import pandas as pd
from datetime import datetime

def get_sample_restaurants(conn, n=100):
    """Get random restaurants that have embeddings"""
    cur = conn.cursor()
    cur.execute("""
        SELECT r.restaurant_id, r.name, r.categories 
        FROM restaurants r
        JOIN restaurant_embeddings re ON r.restaurant_id = re.restaurant_id
        ORDER BY RANDOM()
        LIMIT %s
    """, (n,))
    return cur.fetchall()

def run_benchmark():
    # Connect to database
    conn = psycopg2.connect(
        dbname="restaurant_db",
        user="helloalpacaa",
        host="localhost"
    )
    
    # Get sample restaurants
    print("Getting sample restaurants...")
    sample_restaurants = get_sample_restaurants(conn)
    
    results = []
    
    print("Running benchmarks...")
    for rest_id, rest_name, categories in tqdm(sample_restaurants):
        # Test SQL-based recommendations
        cur = conn.cursor()
        
        # SQL timing
        sql_start = time.time()
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
                r2.categories,
                r2.price_level,
                r2.avg_rating,
                (
                    CASE WHEN r1.categories = r2.categories THEN 0.3 ELSE 0 END +
                    (1 - ABS(r1.price_level - r2.price_level)::float/4) * 0.3 +
                    (1 - ABS(r1.avg_rating - r2.avg_rating)::float/5) * 0.4
                ) as similarity_score
            FROM RestaurantMetrics r1
            JOIN RestaurantMetrics r2 ON r1.restaurant_id != r2.restaurant_id
            WHERE r1.restaurant_id = %s
            ORDER BY similarity_score DESC
            LIMIT 5
        """, (rest_id,))
        sql_results = cur.fetchall()
        sql_time = time.time() - sql_start
        
        # Vector timing
        vector_start = time.time()
        cur.execute("""
            SELECT 
                r.name,
                r.categories,
                r.price_level,
                r.avg_rating,
                1 - (re1.embedding <=> re2.embedding) as similarity_score
            FROM restaurant_embeddings re1
            JOIN restaurant_embeddings re2 ON re1.restaurant_id != re2.restaurant_id
            JOIN restaurants r ON re2.restaurant_id = r.restaurant_id
            WHERE re1.restaurant_id = %s
            ORDER BY similarity_score DESC
            LIMIT 5
        """, (rest_id,))
        vector_results = cur.fetchall()
        vector_time = time.time() - vector_start
        
        results.append({
            'restaurant_id': rest_id,
            'restaurant_name': rest_name,
            'categories': categories,
            'sql_time': sql_time,
            'vector_time': vector_time,
            'sql_top_match': sql_results[0][0] if sql_results else None,
            'sql_similarity': sql_results[0][4] if sql_results else None,
            'vector_top_match': vector_results[0][0] if vector_results else None,
            'vector_similarity': vector_results[0][4] if vector_results else None
        })
    
    conn.close()
    return results

def main():
    # Run benchmark
    print("Starting benchmark...")
    results = run_benchmark()
    
    # Convert to DataFrame
    df = pd.DataFrame(results)
    
    # Generate summary statistics
    print("\nBenchmark Results:")
    print(f"Number of restaurants tested: {len(df)}")
    print("\nTiming Results (seconds):")
    print(f"SQL Average: {df['sql_time'].mean():.4f}")
    print(f"SQL Max: {df['sql_time'].max():.4f}")
    print(f"SQL Min: {df['sql_time'].min():.4f}")
    print(f"\nVector Average: {df['vector_time'].mean():.4f}")
    print(f"Vector Max: {df['vector_time'].max():.4f}")
    print(f"Vector Min: {df['vector_time'].min():.4f}")
    
    print("\nSimilarity Scores:")
    print(f"SQL Average: {df['sql_similarity'].mean():.4f}")
    print(f"Vector Average: {df['vector_similarity'].mean():.4f}")
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    df.to_csv(f'benchmark_results_{timestamp}.csv', index=False)
    print(f"\nDetailed results saved to benchmark_results_{timestamp}.csv")

if __name__ == "__main__":
    main()