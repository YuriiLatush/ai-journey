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


def semantic_search(query, n=3):
    results = collection.query(query_texts=[query], n_results=n)
    return list(zip(results["ids"][0], results["documents"][0], results["distances"][0]))


STOP_WORDS = {"the", "and", "for", "are", "with", "that", "this", "from", "have", "what", "does", "your", "can", "how", "much", "about"}

def keyword_search(query):
    keywords = [w.lower() for w in query.split() if len(w) >= 4 and w.lower() not in STOP_WORDS]
    if not keywords:
        return []
    matches = []
    for i, doc in enumerate(documents):
        doc_lower = doc.lower()
        if any(kw in doc_lower for kw in keywords):
            matches.append((f"doc_{i}", doc))
    return matches


def hybrid_search(query):
    semantic = semantic_search(query, n=3)
    keyword = keyword_search(query)

    semantic_ids = {id_ for id_, _, _ in semantic}
    keyword_ids = {id_ for id_, _ in keyword}

    combined = {}
    for id_, doc, dist in semantic:
        combined[id_] = {"doc": doc, "dist": dist, "method": "semantic"}

    for id_, doc in keyword:
        if id_ in combined:
            combined[id_]["method"] = "both"
        else:
            combined[id_] = {"doc": doc, "dist": None, "method": "keyword"}

    return combined


question = input("Ask a question about TNavigator: ").strip()
if not question:
    print("No question entered.")
    exit()

combined = hybrid_search(question)

context_parts = []
for id_, item in combined.items():
    context_parts.append(f"[{item['method'].upper()}] {item['doc']}")
context = "\n\n".join(context_parts)

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

print(f"\nAnswer:\n{response.choices[0].message.content}")
print("\n" + "-" * 60)
print(f"Sources used ({len(combined)} total):\n")

label_order = {"both": 0, "semantic": 1, "keyword": 2}
for id_, item in sorted(combined.items(), key=lambda x: label_order[x[1]["method"]]):
    tag = f"[{item['method']}]"
    dist = f"  distance: {item['dist']:.4f}" if item["dist"] is not None else ""
    print(f"  {tag}{dist}\n  {item['doc']}\n")
