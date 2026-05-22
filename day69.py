import chromadb

client = chromadb.Client()
collection = client.get_or_create_collection("knowledge_base")

documents = [
    "We offer premium VIP airport transfers in luxury Mercedes S-Class and BMW 7 Series vehicles. All drivers are professionally trained and meet clients at arrivals with a name sign.",
    "Our hourly charter service starts at $120 per hour with a 2-hour minimum. This includes a dedicated chauffeur and unlimited stops within the city.",
    "Corporate accounts receive a 15% discount on all bookings and priority dispatch. Monthly invoicing is available for businesses with 10 or more rides per month.",
    "We operate 24 hours a day, 7 days a week including all public holidays. Advance bookings are recommended but same-day requests are accepted subject to availability.",
    "Our fleet includes Mercedes S-Class, BMW 7 Series, Cadillac Escalade SUVs, and Mercedes Sprinter vans for groups of up to 14 passengers.",
    "Cancellations made more than 24 hours before pickup are fully refunded. Cancellations within 24 hours incur a 50% charge. No-shows are charged in full.",
    "We serve all major airports including JFK, LaGuardia, Newark, and private FBO terminals. Meet-and-greet service is included on all airport pickups.",
    "Long-distance transfers to cities within 300 miles are available. Popular routes include New York to Washington DC ($450), New York to Boston ($380), and New York to Philadelphia ($220).",
    "All vehicles are equipped with Wi-Fi, bottled water, phone chargers, and privacy partitions. Newspapers and refreshments can be arranged on request.",
    "Wedding and event packages include decorated vehicles, red carpet service, and a dedicated coordinator. Packages start at $600 for 4 hours.",
]

ids = [f"doc_{i}" for i in range(len(documents))]

collection.add(documents=documents, ids=ids)
print(f"Loaded {len(documents)} documents into 'knowledge_base'.\n")

query = input("Enter your search query: ").strip()
if not query:
    print("No query entered.")
    exit()

results = collection.query(query_texts=[query], n_results=3)

print(f"\nTop 3 results for: \"{query}\"\n")
print("-" * 60)

docs = results["documents"][0]
distances = results["distances"][0]

for i, (doc, dist) in enumerate(zip(docs, distances), 1):
    print(f"Result {i}  (distance: {dist:.4f})")
    print(f"{doc}")
    print()
