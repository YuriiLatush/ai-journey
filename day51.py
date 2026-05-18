import chromadb
from openai import OpenAI
import os
import json
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
chroma = chromadb.PersistentClient(path="./chroma_db_51")

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
    "We accept cash, credit cards, and Venmo.",
    "Child seats available on request at no extra charge.",
]

def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def load_knowledge_base():
    collection = chroma.get_or_create_collection("transportation_v2")
    if collection.count() == 0:
        print("Loading knowledge base...")
        for i, doc in enumerate(docs):
            collection.add(
                documents=[doc],
                embeddings=[get_embedding(doc)],
                ids=[f"doc_{i}"]
            )
        print(f"Loaded {len(docs)} documents")
    else:
        print(f"Knowledge base ready — {collection.count()} documents")
    return collection

def hybrid_search(collection, query, n=5):
    # Semantic
    embedding = get_embedding(query)
    semantic = collection.query(
        query_embeddings=[embedding],
        n_results=n
    )["documents"][0]

    # Keyword
    keywords = query.lower().split()
    keyword_results = []
    for doc in docs:
        score = sum(1 for k in keywords if k in doc.lower())
        if score > 0:
            keyword_results.append((score, doc))
    keyword_results.sort(reverse=True)
    keyword_docs = [doc for _, doc in keyword_results[:n]]

    # Combine
    combined = list(dict.fromkeys(semantic + keyword_docs))
    return combined[:n]

def rerank(query, candidates, top_n=3):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Return ONLY a JSON array of indices of the most relevant documents. Example: [2, 0, 1]"},
            {"role": "user", "content": f"Query: {query}\n\nCandidates:\n" + 
             "\n".join(f"{i}: {doc}" for i, doc in enumerate(candidates)) +
             f"\n\nReturn top {top_n} indices."}
        ]
    )
    try:
        indices = json.loads(response.choices[0].message.content)
        return [candidates[i] for i in indices[:top_n]]
    except:
        return candidates[:top_n]

def answer(collection, question, history=[]):
    candidates = hybrid_search(collection, question)
    best_docs = rerank(question, candidates, top_n=3)
    context = "\n".join(best_docs)

    messages = [
        {"role": "system", "content": f"""You are an elite transportation concierge for LA.
Use ONLY this context to answer:

{context}

Be professional, concise, and helpful."""}
    ] + history + [{"role": "user", "content": question}]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    return response.choices[0].message.content

# Main
collection = load_knowledge_base()
history = []

print("\n🚗 Elite Transportation RAG System v2")
print("Hybrid search + Reranking + Memory")
print("Type 'quit' to exit\n")

while True:
    question = input("You: ")
    if question.lower() == "quit":
        break
    reply = answer(collection, question, history)
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": reply})
    if len(history) > 10:
        history = history[-10:]
    print(f"Bot: {reply}\n")