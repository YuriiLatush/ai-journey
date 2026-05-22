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

existing = collection.count()
if existing > 0:
    print(f"Loading existing database... ({existing} documents found)")
else:
    print("Creating new database...")
    ids = [f"doc_{i}" for i in range(len(documents))]
    collection.add(documents=documents, ids=ids)
    print(f"Added {len(documents)} documents to 'tnavigator'.")

print()

question = input("Ask a question about TNavigator: ").strip()
if not question:
    print("No question entered.")
    exit()

results = collection.query(query_texts=[question], n_results=3)
retrieved_docs = results["documents"][0]
distances = results["distances"][0]

context = "\n\n".join(
    f"[Document {i+1}]: {doc}" for i, doc in enumerate(retrieved_docs)
)

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {
            "role": "system",
            "content": (
                "You are a helpful assistant for TNavigator VIP Transportation. "
                "Answer the user's question using ONLY the documents provided below. "
                "If the answer is not in the documents, say so clearly. "
                "Be concise and direct.\n\n"
                f"DOCUMENTS:\n{context}"
            ),
        },
        {"role": "user", "content": question},
    ],
)

answer = response.choices[0].message.content

print(f"\nAnswer:\n{answer}")
print("\n" + "-" * 60)
print("Sources used:")
for i, (doc, dist) in enumerate(zip(retrieved_docs, distances), 1):
    print(f"\n  [{i}] (distance: {dist:.4f})\n  {doc}")
