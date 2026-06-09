# Reference test questions derived from data/3MI3400841_3MI3400791_GeoOntology.owl.
# expected_results are local-name strings (geo namespace stripped), matching what
# graphdb.extract_values() produces.

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
        "expected_results": {"Constitutional_Monarchy"},
    },
    {
        "question": "What is the population of France?",
        "category": 1,
        "reference_sparql": _PFX + """\
SELECT ?pop WHERE {
  geo:France geo:population ?pop .
}""",
        "expected_results": {"67000000"},
    },
    {
        "question": "Who is the head of state of Bulgaria?",
        "category": 1,
        "reference_sparql": _PFX + """\
SELECT ?person WHERE {
  geo:Bulgaria geo:has_head_of_state ?person .
}""",
        "expected_results": {"Rumen_Radev"},
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
        "expected_results": {"Himalayas"},
    },
    {
        "question": "Which peaks are located in Europe?",
        "category": 2,
        "reference_sparql": _PFX + """\
SELECT ?peak WHERE {
  ?peak a geo:Peak ;
        geo:is_located_in geo:Europe .
}""",
        "expected_results": {"Musala", "Vihren", "Mont_Blanc"},
    },
    {
        "question": "Which cities are located in South America?",
        "category": 2,
        "reference_sparql": _PFX + """\
SELECT ?city WHERE {
  ?city a geo:City ;
        geo:is_located_in geo:South_America .
}""",
        "expected_results": {"Brasilia", "Buenos_Aires", "Santiago"},
    },
    # ─── Category 3 — Defined Class (instances materialised by reasoner) ──────
    {
        "question": "Which cities are megacities?",
        "category": 3,
        "reference_sparql": _PFX + """\
SELECT ?city WHERE {
  ?city a geo:Megacity .
}""",
        "expected_results": {"Tokyo", "Beijing", "Bangkok"},
    },
    {
        "question": "Which cities are capital cities?",
        "category": 3,
        "reference_sparql": _PFX + """\
SELECT ?city WHERE {
  ?city a geo:CapitalCity .
}""",
        "expected_results": {
            "Sofia", "Paris", "Tokyo", "Washington_DC", "Berlin", "London",
            "Madrid", "Vienna", "Bern", "Beijing", "Seoul", "Bangkok",
            "Riyadh", "Jerusalem", "Cairo", "Pretoria", "Rabat", "Ottawa",
            "Mexico_City", "Brasilia", "Buenos_Aires", "Santiago", "Canberra",
            "Wellington", "Belgrade", "Bucharest", "Rome", "Monaco_City",
        },
    },
    {
        "question": "Which countries are Sunni Islamic countries?",
        "category": 3,
        "reference_sparql": _PFX + """\
SELECT ?country WHERE {
  ?country a geo:SunniIslamicCountry .
}""",
        "expected_results": {"Saudi_Arabia", "Egypt", "Morocco"},
    },
    # ─── Category 4 — Reasoning Required ──────────────────────────────────────
    # Sub-case A: defined class LandlockedCountry exists but OWL open-world
    # assumption prevents the reasoner from materialising instances from absence.
    # The reference SPARQL uses FILTER NOT EXISTS.  Since no country in the
    # ontology explicitly contains a Sea or Ocean, every country is returned.
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
        "expected_results": {
            "Bulgaria", "France", "Japan", "USA", "Germany", "United_Kingdom",
            "Spain", "Austria", "Switzerland", "China", "South_Korea", "Thailand",
            "Saudi_Arabia", "Israel", "Egypt", "South_Africa", "Morocco", "Canada",
            "Mexico", "Brazil", "Argentina", "Chile", "Australia_Country",
            "New_Zealand", "Serbia", "Romania", "Italy", "Turkey", "India",
            "Monaco", "Vatican", "Greece",
        },
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
        "expected_results": {"USA", "Canada", "Mexico"},
    },
]
