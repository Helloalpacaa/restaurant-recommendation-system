import psycopg2
import time

def find_perfect_matches(restaurant_id):
    conn = psycopg2.connect(
        dbname="restaurant_db",
        user="helloalpacaa",
        host="localhost"
    )
    cur = conn.cursor()
    
    # First get the original restaurant details
    cur.execute("""
        SELECT name, categories, price_level, avg_rating 
        FROM restaurants 
        WHERE restaurant_id = %s
    """, (restaurant_id,))
    original = cur.fetchone()
    print(f"\nLooking for perfect matches for: {original[0]}")
    print(f"Categories: {original[1]}")
    print(f"Price Level: {original[2]}")
    print(f"Average Rating: {original[3]}")
    
    # Look for perfect matches
    cur.execute("""
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
        FROM restaurants r1
        JOIN restaurants r2 ON r1.restaurant_id != r2.restaurant_id
        WHERE r1.restaurant_id = %s
        AND r1.categories = r2.categories
        AND r1.price_level = r2.price_level
        AND r1.avg_rating = r2.avg_rating
        ORDER BY similarity_score DESC
    """, (restaurant_id,))
    
    perfect_matches = cur.fetchall()
    
    if perfect_matches:
        print("\nPerfect Matches Found:")
        for match in perfect_matches:
            print(f"\nName: {match[0]}")
            print(f"Categories: {match[1]}")
            print(f"Price Level: {match[2]}")
            print(f"Rating: {match[3]}")
            print(f"Similarity Score: {match[4]}")
    else:
        print("\nNo perfect matches found.")
        
        # Let's see what's close
        cur.execute("""
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
            FROM restaurants r1
            JOIN restaurants r2 ON r1.restaurant_id != r2.restaurant_id
            WHERE r1.restaurant_id = %s
            ORDER BY similarity_score DESC
            LIMIT 5
        """, (restaurant_id,))
        
        close_matches = cur.fetchall()
        print("\nClosest matches:")
        for match in close_matches:
            print(f"\nName: {match[0]}")
            print(f"Categories: {match[1]}")
            print(f"Price Level: {match[2]}")
            print(f"Rating: {match[3]}")
            print(f"Similarity Score: {match[4]}")
    
    conn.close()

# Use the same restaurant ID we used before
find_perfect_matches('XQfwVwDr-v0ZS3_CbbE5Xw')  # Turning Point