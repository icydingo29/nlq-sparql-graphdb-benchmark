import schema

_FEW_SHOT = [
    # Example 1 — direct single-property lookup (covers Cat 1 & Cat 4 patterns)
    {
        "question": "What is the depth of Lake Baikal?",
        "sparql": (
            "PREFIX geo: <http://example.org/geo_ontology_final.owl#>\n"
            "SELECT ?depth WHERE {\n"
            "  geo:Lake_Baikal geo:depth ?depth .\n"
            "}"
        ),
    },
    # Example 2 — transitive is_located_in traversal (covers Cat 2 pattern)
    {
        "question": "Which deserts are located in South America?",
        "sparql": (
            "PREFIX geo: <http://example.org/geo_ontology_final.owl#>\n"
            "SELECT ?desert WHERE {\n"
            "  ?desert a geo:Desert ;\n"
            "          geo:is_located_in geo:South_America .\n"
            "}"
        ),
    },
    # Example 3 — FILTER NOT EXISTS negation (covers Cat 7 pattern)
    {
        "question": "Which buildings are not of Gothic architecture?",
        "sparql": (
            "PREFIX geo: <http://example.org/geo_ontology_final.owl#>\n"
            "SELECT ?building WHERE {\n"
            "  ?building a geo:Building .\n"
            "  FILTER NOT EXISTS { ?building geo:has_architecture geo:Gothic_Architecture }\n"
            "}"
        ),
    },
    # Example 4 — combined numeric FILTER with && (covers Cat 3 pattern)
    {
        "question": "Which lakes have a depth greater than 100 meters and less than 5000 meters?",
        "sparql": (
            "PREFIX geo: <http://example.org/geo_ontology_final.owl#>\n"
            "SELECT ?lake WHERE {\n"
            "  ?lake a geo:Lake ;\n"
            "        geo:depth ?d .\n"
            "  FILTER(?d > 100 && ?d < 5000)\n"
            "}"
        ),
    },
    # Example 5 — COUNT aggregation (covers Cat 5 pattern)
    {
        "question": "How many peaks are there in Asia?",
        "sparql": (
            "PREFIX geo: <http://example.org/geo_ontology_final.owl#>\n"
            "SELECT (COUNT(?peak) AS ?count) WHERE {\n"
            "  ?peak a geo:Peak ;\n"
            "        geo:is_located_in geo:Asia .\n"
            "}"
        ),
    },
    # Example 6 — UNION (covers Cat 6 pattern)
    {
        "question": "Which natural locations are either rivers or lakes?",
        "sparql": (
            "PREFIX geo: <http://example.org/geo_ontology_final.owl#>\n"
            "SELECT ?place WHERE {\n"
            "  { ?place a geo:River }\n"
            "  UNION\n"
            "  { ?place a geo:Lake }\n"
            "}"
        ),
    },
    # Example 7 — OPTIONAL for partial data (covers Cat 6 pattern)
    {
        "question": "Which mountains are in Asia and what is their height if known?",
        "sparql": (
            "PREFIX geo: <http://example.org/geo_ontology_final.owl#>\n"
            "SELECT ?mountain ?height WHERE {\n"
            "  ?mountain a geo:Mountain ;\n"
            "            geo:is_located_in geo:Asia .\n"
            "  OPTIONAL { ?mountain geo:height ?height }\n"
            "}"
        ),
    },
]


def build_messages(user_question: str) -> list:
    messages = [{"role": "system", "content": schema.SCHEMA_SUMMARY}]
    for ex in _FEW_SHOT:
        messages.append({"role": "user", "content": ex["question"]})
        messages.append(
            {"role": "assistant", "content": f"```sparql\n{ex['sparql']}\n```"}
        )
    messages.append({"role": "user", "content": user_question})
    return messages
