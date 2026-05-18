import chromadb
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Persistent storage — saves to disk
chroma = chromadb.PersistentClient(path="./chroma_db")

def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def load_knowledge_base():
    collection = chroma.get_or_create_collection("transportation")
    
    # Only add docs if collection is empty
    if collection.count() == 0:
        print("First run — loading knowledge base...")
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
        for i, doc in enumerate(docs):
            collection.add(
                documents=[doc],
                embeddings=[get_embedding(doc)],
                ids=[f"doc_{i}"]
            )
        print(f"Loaded {len(docs)} documents")
    else:
        print(f"Knowledge base loaded — {collection.count()} documents")
    
    return collection

def rag_answer(collection, question):
    query_embedding = get_embedding(question)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )
    context = "\n".join(results["documents"][0])

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"""You are a helpful transportation concierge.
Answer using ONLY this context:

{context}

If the answer isn't in the context, say "I don't have that information."
Be concise and professional."""},
            {"role": "user", "content": question}
        ]
    )
    return response.choices[0].message.content

collection = load_knowledge_base()

print("\n🚗 Transportation RAG Assistant (Persistent)")
print("Type 'quit' to exit\n")

while True:
    question = input("You: ")
    if question.lower() == "quit":
        break
    answer = rag_answer(collection, question)
    print(f"Bot: {answer}\n")