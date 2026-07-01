# Reference test questions derived from data/GeoOntology.owl.
# reference_sparql is executed live against GraphDB at test time — no hardcoded expected results.

_PFX = "PREFIX geo: <http://example.org/geo_ontology_final.owl#>\n"

QUESTIONS = [
    # ─── Category 1 — Direct Retrieval ────────────────────────────────────────
    {
        "number": 1,
        "question": "What is the form of government of Japan?",
        "category": 1,
        "reference_sparql": _PFX + """\
SELECT ?gov WHERE {
  geo:Japan geo:has_form_of_government ?gov .
}""",
    },
    {
        "number": 2,
        "question": "What is the population of France?",
        "category": 1,
        "reference_sparql": _PFX + """\
SELECT ?pop WHERE {
  geo:France geo:population ?pop .
}""",
    },
    {
        "number": 3,
        "question": "Who is the head of state of Bulgaria?",
        "category": 1,
        "reference_sparql": _PFX + """\
SELECT ?person WHERE {
  geo:Bulgaria geo:has_head_of_state ?person .
}""",
    },
    # ─── Category 2 — Transitivity ────────────────────────────────────────────
    {
        "number": 4,
        "question": "Which mountains are located in Asia?",
        "category": 2,
        "reference_sparql": _PFX + """\
SELECT ?mountain WHERE {
  ?mountain a geo:Mountain ;
            geo:is_located_in geo:Asia .
}""",
    },
    {
        "number": 5,
        "question": "Which peaks are located in Europe?",
        "category": 2,
        "reference_sparql": _PFX + """\
SELECT ?peak WHERE {
  ?peak a geo:Peak ;
        geo:is_located_in geo:Europe .
}""",
    },
    {
        "number": 6,
        "question": "Which cities are located in South America?",
        "category": 2,
        "reference_sparql": _PFX + """\
SELECT ?city WHERE {
  ?city a geo:City ;
        geo:is_located_in geo:South_America .
}""",
    },
    # ─── Category 3 — Numeric Filter ──────────────────────────────────────────
    {
        "number": 7,
        "question": "Which peaks are higher than 5000 meters?",
        "category": 3,
        "reference_sparql": _PFX + """\
SELECT ?peak WHERE {
  ?peak a geo:Peak ;
        geo:height ?h .
  FILTER(?h > 5000)
}""",
    },
    {
        "number": 8,
        "question": "Which cities have a population of more than 1 million?",
        "category": 3,
        "reference_sparql": _PFX + """\
SELECT ?city WHERE {
  ?city a geo:City ;
        geo:population ?pop .
  FILTER(?pop > 1000000)
}""",
    },
    {
        "number": 9,
        "question": "Which peaks have a height between 3000 and 8000 meters?",
        "category": 3,
        "reference_sparql": _PFX + """\
SELECT ?peak WHERE {
  ?peak a geo:Peak ;
        geo:height ?h .
  FILTER(?h > 3000 && ?h < 8000)
}""",
    },
    # ─── Category 4 — Defined Class ───────────────────────────────────────────
    {
        "number": 10,
        "question": "Which cities are megacities?",
        "category": 4,
        "reference_sparql": _PFX + """\
SELECT ?city WHERE {
  ?city a geo:Megacity .
}""",
    },
    {
        "number": 11,
        "question": "Which cities are capital cities?",
        "category": 4,
        "reference_sparql": _PFX + """\
SELECT ?city WHERE {
  ?city a geo:CapitalCity .
}""",
    },
    {
        "number": 12,
        "question": "Which countries are Sunni Islamic countries?",
        "category": 4,
        "reference_sparql": _PFX + """\
SELECT ?country WHERE {
  ?country a geo:Country .
  FILTER EXISTS { ?country geo:has_main_religion geo:Islam_Sunni }
}""",
    },
    # ─── Category 5 — Aggregation ─────────────────────────────────────────────
    {
        "number": 13,
        "question": "How many countries are there in Europe?",
        "category": 5,
        "reference_sparql": _PFX + """\
SELECT (COUNT(?country) AS ?count) WHERE {
  ?country a geo:Country ;
           geo:is_located_in geo:Europe .
}""",
    },
    {
        "number": 14,
        "question": "What is the maximum height among peaks in Asia?",
        "category": 5,
        "reference_sparql": _PFX + """\
SELECT (MAX(?h) AS ?maxHeight) WHERE {
  ?peak a geo:Peak ;
        geo:is_located_in geo:Asia ;
        geo:height ?h .
}""",
    },
    {
        "number": 15,
        "question": "What is the minimum population of a country in Africa?",
        "category": 5,
        "reference_sparql": _PFX + """\
SELECT (MIN(?pop) AS ?minPop) WHERE {
  ?country a geo:Country ;
           geo:is_located_in geo:Africa ;
           geo:population ?pop .
}""",
    },
    {
        "number": 16,
        "question": "What is the average population of countries in Europe?",
        "category": 5,
        "reference_sparql": _PFX + """\
SELECT (AVG(?pop) AS ?avgPop) WHERE {
  ?country a geo:Country ;
           geo:is_located_in geo:Europe ;
           geo:population ?pop .
}""",
    },
    # ─── Category 6 — Compositional (UNION, OPTIONAL) ─────────────────────────
    {
        "number": 17,
        "question": "Which places are either mountains or volcanoes?",
        "category": 6,
        "reference_sparql": _PFX + """\
SELECT ?place WHERE {
  { ?place a geo:Mountain }
  UNION
  { ?place a geo:Volcano }
}""",
    },
    {
        "number": 18,
        "question": "List all countries in Europe and their main religion if one is defined.",
        "category": 6,
        "reference_sparql": _PFX + """\
SELECT ?country ?religion WHERE {
  ?country a geo:Country ;
           geo:is_located_in geo:Europe .
  OPTIONAL { ?country geo:has_main_religion ?religion }
}""",
    },
    {
        "number": 19,
        "question": "Which capital cities are not megacities?",
        "category": 6,
        "reference_sparql": _PFX + """\
SELECT ?city WHERE {
  { ?city a geo:CapitalCity }
  MINUS
  { ?city a geo:Megacity }
}""",
    },
    # ─── Category 7 — Reasoning Required ──────────────────────────────────────
    # Sub-case A: FILTER NOT EXISTS on transitive is_located_in. No class like
    # "NonEuropeanVolcano" exists; the LLM must use negation on location.
    {
        "number": 20,
        "question": "Which volcanoes are not located in Europe?",
        "category": 7,
        "reference_sparql": _PFX + """\
SELECT ?volcano WHERE {
  ?volcano a geo:Volcano .
  FILTER NOT EXISTS { ?volcano geo:is_located_in geo:Europe }
}""",
    },
    # Sub-case B: no class exists for "North American countries"; model must
    # identify the is_located_in property and the North_America individual.
    {
        "number": 21,
        "question": "Which countries are in North America?",
        "category": 7,
        "reference_sparql": _PFX + """\
SELECT ?country WHERE {
  ?country a geo:Country ;
           geo:is_located_in geo:North_America .
}""",
    },
    # Sub-case C: RepublicState IS materialised by OWL2-RL (empirically returns 14
    # countries). Main failure mode was schema notation bleed (∪ copied into SPARQL).
    # Reference SPARQL uses FILTER IN to avoid `a geo:RepublicState` ambiguity.
    {
        "number": 22,
        "question": "Which countries are republics?",
        "category": 7,
        "reference_sparql": _PFX + """\
SELECT ?country WHERE {
  ?country a geo:Country ;
           geo:has_form_of_government ?gov .
  FILTER(?gov IN (geo:Parliamentary_Republic, geo:Federal_Republic))
}""",
    },
]

CAT_LABELS = {
    1: "Direct Retrieval",
    2: "Transitivity",
    3: "Numeric Filter",
    4: "Defined Class",
    5: "Aggregation",
    6: "Compositional",
    7: "Reasoning Required",
}
