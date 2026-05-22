import json
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()
chroma = chromadb.PersistentClient(path="./chroma_db_tnavigator")
collection = chroma.get_or_create_collection("tnavigator")

DOCUMENTS = [
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

STOP_WORDS = {"the", "and", "for", "are", "with", "that", "this", "from", "have",
              "what", "does", "your", "can", "how", "much", "about", "you", "our"}

SYSTEM_PROMPT = (
    "You are the TNavigator AI assistant, a helpful and professional concierge for "
    "TNavigator VIP Transportation in Los Angeles. "
    "Answer ONLY questions related to TNavigator services, fleet, pricing, policies, and routes. "
    "If a question is unrelated to TNavigator, politely redirect the conversation. "
    "STRICT RULE: base your answer EXCLUSIVELY on the RELEVANT DOCUMENTS provided. "
    "If the documents do not contain the answer, say exactly: "
    "'I don't have that information — please contact us directly to confirm.' "
    "Never guess, assume, or use outside knowledge. "
    "Documents marked [LOW RELEVANCE] are weak matches; do not use them to answer. "
    "Be concise, warm, and professional."
)

if collection.count() == 0:
    print("Setting up database...")
    collection.add(documents=DOCUMENTS, ids=[f"doc_{i}" for i in range(len(DOCUMENTS))])
    print(f"Added {len(DOCUMENTS)} documents.\n")
else:
    print(f"Database ready ({collection.count()} documents).\n")


def semantic_search(query, n=5):
    results = collection.query(query_texts=[query], n_results=n)
    return list(zip(results["ids"][0], results["documents"][0], results["distances"][0]))


def keyword_search(query):
    keywords = [w.lower() for w in query.split() if len(w) >= 4 and w.lower() not in STOP_WORDS]
    if not keywords:
        return []
    matches = []
    for i, doc in enumerate(DOCUMENTS):
        if any(kw in doc.lower() for kw in keywords):
            matches.append((f"doc_{i}", doc, None))
    return matches


def hybrid_search(query):
    semantic = semantic_search(query, n=5)
    keyword = keyword_search(query)

    seen = {}
    for id_, doc, dist in semantic:
        seen[id_] = (doc, dist, "semantic")
    for id_, doc, dist in keyword:
        if id_ in seen:
            seen[id_] = (seen[id_][0], seen[id_][1], "both")
        else:
            seen[id_] = (doc, None, "keyword")

    return [(id_, doc, dist, method) for id_, (doc, dist, method) in seen.items()]


def rerank(query, candidates, top_n=2):
    numbered = "\n".join(f"{i+1}. {doc}" for i, (_, doc, _, _) in enumerate(candidates))
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Rank the documents by relevance to the question. "
                        "Return a JSON array of 1-based document numbers, most relevant first. "
                        "Return ONLY the JSON array.\nExample: [3, 1, 5, 2, 4]"
                    ),
                },
                {"role": "user", "content": f"Question: {query}\n\nDocuments:\n{numbered}"},
            ],
            temperature=0,
        )
        order = json.loads(response.choices[0].message.content.strip())
        reranked = [candidates[i - 1] for i in order if 1 <= i <= len(candidates)]
        return reranked[:top_n] if reranked else candidates[:top_n]
    except Exception:
        return candidates[:top_n]


DISTANCE_THRESHOLD = 1.5

def build_context(docs):
    lines = []
    for _, doc, dist, method in docs:
        if dist is not None and dist > DISTANCE_THRESHOLD:
            lines.append(f"[{method.upper()}][LOW RELEVANCE] {doc}")
        else:
            lines.append(f"[{method.upper()}] {doc}")
    return "\n\n".join(lines)


def chat(question, history):
    candidates = hybrid_search(question)
    top_docs = rerank(question, candidates, top_n=2)
    context = build_context(top_docs)

    doc_section = f"RELEVANT DOCUMENTS:\n{context}" if context else "RELEVANT DOCUMENTS: none found for this query — if the topic is outside TNavigator services, say so politely."
    messages = [
        {
            "role": "system",
            "content": f"{SYSTEM_PROMPT}\n\n{doc_section}",
        }
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )
    answer = response.choices[0].message.content

    sources = ", ".join(
        f"[{method}]" for _, _, _, method in top_docs
    )
    return answer, sources


print("TNavigator AI Assistant")
print("Type 'quit' or 'exit' to end the conversation.\n")
print("-" * 60)

history = []

while True:
    try:
        question = input("\nYou: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n\nGoodbye!")
        break

    if not question:
        continue
    if question.lower() in {"quit", "exit"}:
        print("\nGoodbye!")
        break

    answer, sources = chat(question, history)

    print(f"\nTNavigator: {answer}")
    print(f"\n  sources: {sources}")

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})
    history = history[-10:]  # keep last 5 exchanges (10 messages)
