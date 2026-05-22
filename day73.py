import json
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()
chroma = chromadb.PersistentClient(path="./chroma_db_tnavigator")
collection = chroma.get_or_create_collection("tnavigator")

documents = [
    "TNavigator VIP Transportation offers premium chauffeur services throughout Los Angeles, including Beverly Hills, Santa Monica, Malibu, and the greater LA metro area.",
    "Our fleet includes Mercedes S-Class sedans, BMW 7 Series, Cadillac Escalade SUVs, and Mercedes Sprinter vans for groups up to 14 passengers. All vehicles are 2022 or newer.",
    "Airport transfers are available 24/7 to LAX, Burbank (BUR), Long Beach (LGB), and Van Nuys (VNY) private terminals. Drivers monitor flight status and adjust pickup time automatically.",
    "Hourly charter rates start at $150 per hour with a 2-hour minimum for sedans and $200 per hour for SUVs. Sprinter van charters start at $250 per hour with a 3-hour minimum.",
    "Corporate accounts receive a 20% discount and dedicated account manager. Invoicing is available monthly for businesses booking 15 or more rides per month.",
    "Long-distance routes include LA to San Francisco ($650), LA to San Diego ($280), LA to Palm Springs ($320), and LA to Las Vegas ($550). All quoted prices are one-way.",
    "Cancellations must be made at least 3 hours before pickup for a full refund. Cancellations within 3 hours are charged 50%. No-shows and same-day cancellations are charged in full.",
    "All vehicles include complimentary Wi-Fi, bottled water, phone chargers, and privacy screens. Premium requests such as champagne, floral arrangements, or specific music can be arranged 24 hours in advance.",
    "Red carpet and celebrity event packages are available starting at $800 for 5 hours. These include a dedicated coordinator, vehicle decoration, and a confidentiality agreement for high-profile clients.",
    "TNavigator operates under a licensed and insured California carrier permit. All chauffeurs hold a valid California TCP license, pass background checks, and complete defensive driving training annually.",
]

if collection.count() == 0:
    print("Creating new database...")
    collection.add(documents=documents, ids=[f"doc_{i}" for i in range(len(documents))])
    print(f"Added {len(documents)} documents.\n")
else:
    print(f"Loaded existing database ({collection.count()} documents).\n")


def retrieve(query, n=5):
    results = collection.query(query_texts=[query], n_results=n)
    return list(zip(results["ids"][0], results["documents"][0], results["distances"][0]))


def rerank(query, candidates):
    numbered = "\n".join(
        f"{i+1}. {doc}" for i, (_, doc, _) in enumerate(candidates)
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a relevance ranking assistant. "
                    "Given a question and a list of documents, return a JSON array "
                    "of document numbers ordered from most to least relevant to the question. "
                    "Use 1-based numbering. Return ONLY the JSON array, no explanation.\n"
                    "Example: [3, 1, 5, 2, 4]"
                ),
            },
            {
                "role": "user",
                "content": f"Question: {query}\n\nDocuments:\n{numbered}",
            },
        ],
        temperature=0,
    )
    text = response.choices[0].message.content.strip()
    order = json.loads(text)
    return [candidates[i - 1] for i in order]


def answer(query, top_docs):
    context = "\n\n".join(
        f"[Document {i+1}]: {doc}" for i, (_, doc, _) in enumerate(top_docs)
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant for TNavigator VIP Transportation. "
                    "Answer the user's question using ONLY the documents provided. "
                    "If the answer is not in the documents, say so. Be concise.\n\n"
                    f"DOCUMENTS:\n{context}"
                ),
            },
            {"role": "user", "content": query},
        ],
    )
    return response.choices[0].message.content


question = input("Ask a question about TNavigator: ").strip()
if not question:
    print("No question entered.")
    exit()

print("\n--- Step 1: Retrieve top 5 from ChromaDB ---")
retrieved = retrieve(question, n=5)
for i, (id_, doc, dist) in enumerate(retrieved, 1):
    print(f"  {i}. (distance: {dist:.4f}) {doc[:80]}...")

print("\n--- Step 2: Reranking with GPT-4o-mini ---")
reranked = rerank(question, retrieved)
for i, (id_, doc, dist) in enumerate(reranked, 1):
    original_pos = next(j + 1 for j, (oid, _, _) in enumerate(retrieved) if oid == id_)
    moved = ""
    if original_pos != i:
        moved = f"  (was #{original_pos})"
    print(f"  {i}.{moved} {doc[:80]}...")

print("\n--- Step 3: Answer using top 2 reranked documents ---")
top2 = reranked[:2]
final_answer = answer(question, top2)

print(f"\nAnswer:\n{final_answer}")
print("\n" + "-" * 60)
print("Final context (top 2 after reranking):\n")
for i, (id_, doc, dist) in enumerate(top2, 1):
    print(f"  [{i}] {doc}\n")
