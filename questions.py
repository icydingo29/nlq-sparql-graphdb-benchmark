# Reference test questions derived from data/3MI3400841_3MI3400791_GeoOntology.owl.
# reference_sparql is executed live against GraphDB at test time — no hardcoded expected results.

_PFX = "PREFIX geo: <http://example.org/geo_ontology_final.owl#>\n"

QUESTIONS = [
    # ─── Category 1 — Direct Retrieval ────────────────────────────────────────
    {
        "question": "What is the form of government of Japan?",
        "category": 1,
        "reference_sparql": _PFX + """\
SELECT ?gov WHERE {
  geo:Japan geo:has_form_of_government ?gov .
}""",
    },
    {
        "question": "What is the population of France?",
        "category": 1,
        "reference_sparql": _PFX + """\
SELECT ?pop WHERE {
  geo:France geo:population ?pop .
}""",
    },
    {
        "question": "Who is the head of state of Bulgaria?",
        "category": 1,
        "reference_sparql": _PFX + """\
SELECT ?person WHERE {
  geo:Bulgaria geo:has_head_of_state ?person .
}""",
    },
    # ─── Category 2 — Transitivity and Inversion ──────────────────────────────
    {
        "question": "Which mountains are located in Asia?",
        "category": 2,
        "reference_sparql": _PFX + """\
SELECT ?mountain WHERE {
  ?mountain a geo:Mountain ;
            geo:is_located_in geo:Asia .
}""",
    },
    {
        "question": "Which peaks are located in Europe?",
        "category": 2,
        "reference_sparql": _PFX + """\
SELECT ?peak WHERE {
  ?peak a geo:Peak ;
        geo:is_located_in geo:Europe .
}""",
    },
    {
        "question": "Which cities are located in South America?",
        "category": 2,
        "reference_sparql": _PFX + """\
SELECT ?city WHERE {
  ?city a geo:City ;
        geo:is_located_in geo:South_America .
}""",
    },
    # ─── Category 3 — Defined Class (instances materialised by reasoner) ──────
    {
        "question": "Which cities are megacities?",
        "category": 3,
        "reference_sparql": _PFX + """\
SELECT ?city WHERE {
  ?city a geo:Megacity .
}""",
    },
    {
        "question": "Which cities are capital cities?",
        "category": 3,
        "reference_sparql": _PFX + """\
SELECT ?city WHERE {
  ?city a geo:CapitalCity .
}""",
    },
    {
        "question": "Which countries are Sunni Islamic countries?",
        "category": 3,
        "reference_sparql": _PFX + """\
SELECT ?country WHERE {
  ?country a geo:Country .
  FILTER EXISTS { ?country geo:has_main_religion geo:Islam_Sunni }
}""",
    },
    # ─── Category 4 — Reasoning Required ──────────────────────────────────────
    # Sub-case A: LandlockedCountry has no materialised instances due to OWL
    # open-world assumption. Reference uses FILTER NOT EXISTS on raw data.
    {
        "question": "Which countries are landlocked?",
        "category": 4,
        "reference_sparql": _PFX + """\
SELECT ?country WHERE {
  ?country a geo:Country .
  FILTER NOT EXISTS {
    ?country geo:contains ?water .
    { ?water a geo:Sea } UNION { ?water a geo:Ocean }
  }
}""",
    },
    # Sub-case B: no class exists for "North American countries"; model must
    # identify the is_located_in property and the North_America individual.
    {
        "question": "Which countries are in North America?",
        "category": 4,
        "reference_sparql": _PFX + """\
SELECT ?country WHERE {
  ?country a geo:Country ;
           geo:is_located_in geo:North_America .
}""",
    },
]
