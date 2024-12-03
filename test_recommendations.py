import psycopg2
import time

def test_recommendations(restaurant_id):
    conn = psycopg2.connect(
        dbname="restaurant_db",
        user="helloalpacaa",
        host="localhost"
    )
    cur = conn.cursor()
    
    # Get details of the target restaurant
    cur.execute("""
        SELECT name, categories, price_level, avg_rating 
        FROM restaurants 
        WHERE restaurant_id = %s
    """, (restaurant_id,))
    restaurant_details = cur.fetchone()
    print(f"\nFinding similar restaurants to: {restaurant_details[0]}")
    print(f"Categories: {restaurant_details[1]}")
    print(f"Price Level: {restaurant_details[2]}")
    print(f"Average Rating: {restaurant_details[3]}")
    
    print("\nSQL-based recommendations:")
    # SQL-based similarity
    start_time = time.time()
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
    """, (restaurant_id,))
    sql_time = time.time() - start_time
    
    for row in cur.fetchall():
        print(f"\nName: {row[0]}")
        print(f"Categories: {row[1]}")
        print(f"Price Level: {row[2]}")
        print(f"Rating: {row[3]}")
        print(f"Similarity Score: {row[4]:.3f}")
    
    print(f"\nSQL query took {sql_time:.3f} seconds")
    
    print("\nVector-based recommendations:")
    # Vector-based similarity
    start_time = time.time()
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
    """, (restaurant_id,))
    vector_time = time.time() - start_time
    
    for row in cur.fetchall():
        print(f"\nName: {row[0]}")
        print(f"Categories: {row[1]}")
        print(f"Price Level: {row[2]}")
        print(f"Rating: {row[3]}")
        print(f"Similarity Score: {row[4]:.3f}")
    
    print(f"\nVector query took {vector_time:.3f} seconds")
    
    conn.close()

if __name__ == "__main__":
    test_recommendations('XQfwVwDr-v0ZS3_CbbE5Xw')  # Turning Point of North Wales