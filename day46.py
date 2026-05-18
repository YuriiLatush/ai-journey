import chromadb
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
chroma = chromadb.Client()
collection = chroma.create_collection("transportation")

# Knowledge base
docs = [
    "We offer airport sedan service for $150. Available 24/7.",
    "Airport SUV service costs $200. Fits up to 6 passengers.",
    "Hourly sedan rental is $100 per hour. Minimum 2 hours.",
    "Hourly SUV rental is $150 per hour. Great for events.",
    "Night surcharge of 25% applies between 10 PM and 6 AM.",
    "Weekend surcharge of 15% applies on Saturday and Sunday.",
    "VIP clients receive 10% discount on all services.",
    "We serve all major LA airports: LAX, BUR, LGB, ONT.",
]

def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

# Add docs to ChromaDB
print("Loading knowledge base...")
for i, doc in enumerate(docs):
    embedding = get_embedding(doc)
    collection.add(
        documents=[doc],
        embeddings=[embedding],
        ids=[f"doc_{i}"]
    )
print(f"Loaded {len(docs)} documents")

# Search function
def search(query, n=3):
    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n
    )
    return results["documents"][0]

# Test
queries = [
    "How much does airport pickup cost?",
    "Do you have discounts?",
    "What about late night rides?"
]

print("\n--- Semantic Search Test ---")
for q in queries:
    print(f"\nQ: {q}")
    results = search(q)
    for r in results:
        print(f"  → {r}")