import chromadb
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
chroma = chromadb.Client()
collection = chroma.create_collection("transportation_hybrid")

docs = [
    "We offer airport sedan service for $150. Available 24/7.",
    "Airport SUV service costs $200. Fits up to 6 passengers.",
    "Hourly sedan rental is $100 per hour. Minimum 2 hours.",
    "Hourly SUV rental is $150 per hour. Great for events.",
    "Night surcharge of 25% applies between 10 PM and 6 AM.",
    "Weekend surcharge of 15% applies on Saturday and Sunday.",
    "VIP clients receive 10% discount on all services.",
    "We serve all major LA airports: LAX, BUR, LGB, ONT.",
    "Cancellations must be made 2 hours before pickup.",
    "All drivers are licensed and insured. Background checked.",
]

def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

print("Loading knowledge base...")
for i, doc in enumerate(docs):
    collection.add(
        documents=[doc],
        embeddings=[get_embedding(doc)],
        ids=[f"doc_{i}"]
    )

def semantic_search(query, n=3):
    embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=n
    )
    return results["documents"][0]

def keyword_search(query, n=3):
    keywords = query.lower().split()
    scores = []
    for doc in docs:
        score = sum(1 for k in keywords if k in doc.lower())
        scores.append((score, doc))
    scores.sort(reverse=True)
    return [doc for score, doc in scores[:n] if score > 0]

def hybrid_search(query, n=3):
    semantic = semantic_search(query, n)
    keyword = keyword_search(query, n)
    
    # Combine and deduplicate
    combined = list(dict.fromkeys(semantic + keyword))
    return combined[:n]

def rag_answer(question):
    results = hybrid_search(question)
    context = "\n".join(results)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"""You are a transportation concierge.
Answer using ONLY this context:

{context}

Be concise and professional."""},
            {"role": "user", "content": question}
        ]
    )
    return response.choices[0].message.content

# Test comparison
test_queries = [
    "How much is SUV to airport?",
    "late night pricing",
    "VIP discount"
]

print("\n--- Hybrid Search Test ---")
for q in test_queries:
    print(f"\nQ: {q}")
    print(f"Semantic: {semantic_search(q, 1)[0][:60]}...")
    kw = keyword_search(q, 1)
    print(f"Keyword:  {kw[0][:60] if kw else 'no results'}...")
    print(f"Answer:   {rag_answer(q)}")