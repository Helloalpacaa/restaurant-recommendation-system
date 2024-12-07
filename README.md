# Restaurant Recommendation System: SQL vs Vector Comparison

## Project Overview
This project implements and compares traditional SQL and vector-based approaches for restaurant recommendations using the Yelp Academic Dataset.

## Project Setup

### Database System
- **PostgreSQL 17**
  - Installation: [PostgreSQL Download](https://www.postgresql.org/download/)
- **pgvector Extension**
  ```bash
  brew install pgvector
  ```
### Python Dependencies
```bash
pip install pandas numpy tqdm psycopg2-binary sentence-transformers
```

## Data Preparation

### Data Source
1. Download the Yelp Academic Dataset from Yelp Dataset
2. Required files:
     - yelp_academic_dataset_business.json
     - yelp_academic_dataset_review.json

### Database Setup
1. Create database and required tables:
```bash
CREATE DATABASE restaurant_db;
\c restaurant_db

CREATE EXTENSION vector;

-- Create restaurants table
CREATE TABLE restaurants (
    restaurant_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255),
    address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    categories TEXT,
    price_level INTEGER,
    avg_rating DECIMAL(3,2),
    review_count INTEGER
);

-- Create ratings table
CREATE TABLE ratings (
    review_id VARCHAR(255) PRIMARY KEY,
    restaurant_id VARCHAR(255),
    user_id VARCHAR(255),
    rating DECIMAL(3,2),
    review_text TEXT,
    review_date DATE,
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id)
);

-- Create restaurant_embeddings table
CREATE TABLE restaurant_embeddings (
    restaurant_id VARCHAR(255) PRIMARY KEY,
    embedding vector(384),
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id)
);
```
2. Load data using provided script:
```bash
python load_yelp_data.py
```


## Running the Project

### 1. Basic Recommendation Test
```bash
python test_recommendations.py
```
Shows SQL vs vector-based recommendations for a sample restaurant with execution times.
### 2. Comprehensive Evaluation:
```bash
python relevant_metrics.py
```
Provides detailed metrics comparing both approaches:
 - Category matching
 - Price accuracy
 - Rating similarity
 - Location relevance
 - Variety score
### 3. SQL Perfect Match Testing
```bash
python find_perfect_matches.py
```
Demonstrates SQL matching capabilities and limitations.

## Expected Results
The system will show:

Recommendations from both methods
Performance metrics
Similarity scores
Execution time comparison

## Implementation Details
### Data Processing
 - Filters for restaurant businesses
 - Processes 50,000 restaurants and 500,000 reviews
 - Generates 384-dimensional vectors using SentenceTransformer
### Vector Generation
 - Uses 'all-MiniLM-L6-v2' model
 - Combines multiple reviews per restaurant
 - Creates 384-dimensional embeddings
### Comparison Methods
### 1. SQL-based:
 - Uses weighted combination of category, price, and rating matching
 - Direct attribute comparison
 - Traditional database approach
### 2. Vector-based:
 - Uses pgvector for similarity search
 - Cosine similarity between embeddings
 - Captures semantic similarities

## Results Summary
- Vector approach is 2.6x faster
- Vector better at category matching and location relevance
- SQL better at exact matches (price, rating)
- Both approaches have specific use cases

## References
 - pgvector: GitHub
 - SentenceTransformer: Documentation
 - Yelp Dataset: Documentation