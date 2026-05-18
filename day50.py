import chromadb
from openai import OpenAI
import os
import json
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
chroma = chromadb.Client()
collection = chroma.create_collection("transportation_rerank")

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

def semantic_search(query, n=5):
    embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=n
    )
    return results["documents"][0]

def rerank(query, candidates, top_n=3):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """You are a reranker. Given a query and candidate documents, 
return the indices of the top most relevant documents in order.
Return ONLY a JSON array of indices like: [2, 0, 1]"""},
            {"role": "user", "content": f"""Query: {query}

Candidates:
{chr(10).join(f'{i}: {doc}' for i, doc in enumerate(candidates))}

Return top {top_n} indices as JSON array."""}
        ]
    )
    try:
        indices = json.loads(response.choices[0].message.content)
        return [candidates[i] for i in indices[:top_n]]
    except:
        return candidates[:top_n]

def rag_with_rerank(question):
    # Get more candidates than needed
    candidates = semantic_search(question, n=5)
    
    # Rerank to get best ones
    reranked = rerank(question, candidates, top_n=2)
    context = "\n".join(reranked)

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
    return response.choices[0].message.content, candidates, reranked

# Test
queries = [
    "What is the cheapest option to LAX?",
    "I need a car for a wedding this Saturday night",
    "Can I cancel my booking?"
]

print("\n--- Reranking Test ---")
for q in queries:
    answer, candidates, reranked = rag_with_rerank(q)
    print(f"\nQ: {q}")
    print(f"Before rerank ({len(candidates)} docs): {candidates[0][:50]}...")
    print(f"After rerank ({len(reranked)} docs):  {reranked[0][:50]}...")
    print(f"Answer: {answer}")