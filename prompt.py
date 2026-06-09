import schema

_FEW_SHOT = [
    # Example 1 — direct single-property lookup (covers Cat 1 & Cat 3 patterns)
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
    # Example 3 — FILTER NOT EXISTS negation (covers Cat 4 pattern)
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
