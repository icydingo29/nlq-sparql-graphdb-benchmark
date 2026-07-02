# Natural Language Querying over a Geographic OWL Ontology

## Abstract

This report presents the design, implementation, and evaluation of a Natural Language Querying (NLQ) system for a geographic OWL2 ontology. The system translates free-text questions into SPARQL queries using locally-hosted large language models (qwen2.5-coder:3b and qwen2.5-coder:7b via Ollama) and executes them against a GraphDB triplestore with OWL2-RL reasoning enabled. Twenty-two reference questions across seven query categories, ordered by inference complexity, evaluate reliability. In a 10-run benchmark across all 22 questions, the 3B model achieves **82% overall exact-match accuracy** (180/220) and the 7B model achieves **93%** (204/220). Category 2 (Transitivity) reaches 100% for both models; Category 7 (Reasoning Required) reaches 87% (7B) but only 30% (3B). The report analyses where OWL2-RL inference aids querying, where it falls short, how prompt engineering choices affect output quality, and how the two model sizes compare.

---

## Contents

1. [Introduction](#1-introduction)
2. [Technical Setup](#2-technical-setup)
3. [The Geographic Ontology](#3-the-geographic-ontology)
4. [Prompt Engineering](#4-prompt-engineering)
5. [Query Categories](#5-query-categories)
6. [Query Analysis: Natural Language vs. SPARQL](#6-query-analysis-natural-language-vs-sparql)
7. [OWL2-RL Inference Analysis](#7-owl2-rl-inference-analysis)
8. [Experimental Results](#8-experimental-results)
9. [Failure Mode Analysis](#9-failure-mode-analysis)
10. [Discussion](#10-discussion)
11. [Conclusions](#11-conclusions)

---

## 1. Introduction

Ontologies provide structured, machine-readable representations of domain knowledge. A fundamental usability challenge is that querying an ontology requires knowledge of SPARQL — a formal query language unfamiliar to most end users. Natural Language Querying (NLQ) addresses this by allowing questions to be asked in plain language, with the system producing the corresponding SPARQL automatically.

This project implements a NLQ pipeline for a geographic ontology covering countries, cities, mountains, rivers, and their relationships. A local large language model (LLM) is connected to a GraphDB triplestore using few-shot prompting to guide SPARQL generation. The work evaluates both the reliability of this approach and the role of OWL2-RL reasoning in producing correct answers.

The system runs entirely on locally-hosted, open-source components: a GraphDB triplestore for OWL2-RL reasoning and Ollama-hosted language models with no cloud API dependency. The primary model is a 3-billion parameter model that fits within 4 GB of VRAM; a 7-billion parameter model is benchmarked as a comparison to quantify the effect of model scale. Together, these constraints test how much NLQ capability can be achieved within practical resource limits.

---

## 2. Technical Setup

### 2.1 Components

| Component | Technology | Configuration |
|-----------|-----------|---------------|
| Knowledge Graph | GraphDB Free 10.x | OWL2-RL reasoning; repository `geo`; port 7200 |
| Language Model (baseline) | Ollama / qwen2.5-coder:3b | Locally hosted; port 11434; 3B parameters; ~4 s/question on RTX 3050 4 GB |
| Language Model (comparison) | Ollama / qwen2.5-coder:7b | Locally hosted; port 11434; 7B parameters; ~7 s/question; partially spills to CPU RAM |
| Orchestration | Python 3.10+ | `requests` for HTTP; no ML frameworks required |

### 2.2 System Architecture

```
User question (natural language)
        │
        ▼
   LLM (Ollama)        ← system prompt: ontology schema + 11 SPARQL rules
   few-shot examples   ← 7 worked examples, one per SPARQL construct
        │
        ▼  SPARQL query (extracted from code block)
   GraphDB (OWL2-RL)
        │
        ▼  SPARQL 1.1 JSON results
   Result parser + namespace stripper
        │
        ▼
   Answer (set of values)
```

The LLM receives a system prompt containing the full ontology schema and SPARQL generation rules, followed by seven worked examples. The user's question is appended and the model returns a SPARQL query inside a fenced code block. That query is executed against GraphDB. If GraphDB returns HTTP 400 (syntax error), the LLM is asked to fix the query, with up to two retry attempts.

### 2.3 Evaluation Scoring

Each LLM result set is compared against a reference answer produced by executing a hand-written reference SPARQL query live against GraphDB at evaluation time. Scoring uses set equality:

| Label | Meaning |
|-------|---------|
| EXACT | LLM result set equals reference result set |
| PARTIAL | Partial overlap between result sets |
| NONE | No overlap |
| EXTRACTION FAILED | LLM returned no SPARQL code block |

Using live reference execution (rather than hardcoded expected answers) ensures that OWL2-RL inferred results are automatically included in the expected answer, and that any changes to the ontology data are reflected immediately.

---

## 3. The Geographic Ontology

The ontology (`GeoOntology.owl`) models geographic entities and their relationships. It was loaded into GraphDB with OWL2-RL reasoning enabled.

### 3.1 Class Hierarchy

```
owl:Thing
├── Place
│   ├── PopulatedPlace
│   │   ├── Village
│   │   │   └── SmallVillage       — Village with population ≤ 500
│   │   └── City  (disjoint with Village)
│   │       ├── Megacity           — City with population ≥ 10,000,000
│   │       ├── CapitalCity        — City with is_capital = true
│   │       └── ModernMetropolis   — City containing a Building with Modernism architecture
│   ├── Landmark
│   │   ├── NaturalLandmark
│   │   └── CulturalLandmark
│   │       └── Building
│   │           ├── Castle
│   │           ├── Temple
│   │           │   ├── Monastery, Mosque, BuddhistTemple, Church
│   │           ├── AncientBuilding — Building with construction_date ≤ 1000
│   │           └── GothicTemple    — Temple with Gothic architecture
│   └── NaturalLocation
│       ├── WaterNaturalLocation
│       │   ├── River, Lake, Sea, Ocean
│       │   ├── DeepWater           — WaterNaturalLocation with depth ≥ 5000
│       │   └── SaltWaterBody       — WaterNaturalLocation with is_saltwatered = true
│       └── LandNaturalLocation
│           ├── Mountain, Desert, Forest
│           ├── Peak
│           │   └── HighPeak        — Peak with height ≥ 8000
│           ├── Volcano
│           └── Island
│               └── TropicalIsland  — Island in an Ocean with temperature ≥ 25
├── Continent
├── Country
│   ├── AbsMonarchyState            — Country with Absolute_Monarchy government
│   ├── RepublicState               — Country with Parliamentary_Republic or Federal_Republic government
│   ├── OrthodoxChristianCountry    — Country with Eastern_Orthodoxy religion
│   ├── SunniIslamicCountry         — Country with Islam_Sunni religion
│   ├── ShiaIslamicCountry          — Country with Islam_Shia religion
│   ├── LandlockedCountry           — Country containing no Sea or Ocean
│   └── MountainousCountry          — Country containing a Mountain
├── Religion
├── Form_of_Government
├── Architecture
└── Person
```

Leaf classes annotated with `—` are *defined classes* — their membership is specified by logical conditions via `owl:equivalentClass`. Whether instances are queryable depends on both whether explicit `rdf:type` assertions exist in the OWL file and whether OWL2-RL inference can materialise membership:

| Defined Class | Condition | Explicitly typed? | Query returns results? |
|--------------|-----------|-------------------|----------------------|
| `Megacity` | City with population ≥ 10,000,000 | **Yes** | **Yes** |
| `CapitalCity` | City with is_capital = true | **Yes** | **Yes** |
| `RepublicState` | Country with Parliamentary_Republic or Federal_Republic government | **Yes** (15 instances) | **Yes** |
| `HighPeak` | Peak with height ≥ 8000 | **Yes** | **Yes** |
| `LandlockedCountry` | Country containing no Sea or Ocean (negation) | No | **No** — open-world assumption |
| `SunniIslamicCountry` | Country with has_main_religion Islam_Sunni | No | **No** — OWL2-RL inference also fails (individual filler) |

Whether and why each category materialises is examined in Section 7.

### 3.2 Key Properties

The most important property for querying is `is_located_in`, declared **Transitive** in OWL2. This means:

```
Musala  is_located_in  Rila         (asserted)
Rila    is_located_in  Bulgaria     (asserted)
Bulgaria is_located_in Europe       (asserted)
```

Under OWL2-RL, the reasoner materialises the inferred triples:

```
Musala  is_located_in  Bulgaria     (inferred)
Musala  is_located_in  Europe       (inferred)
```

This transitive closure is what makes geographic containment queries possible without requiring explicit property paths.

Sub-properties `is_peak_in` (Peak → Mountain) and `is_island_in` (Island → WaterNaturalLocation) both inherit transitivity as sub-properties of `is_located_in`.

### 3.3 Named Individuals

The ontology contains approximately 150 named individuals across all types:

| Type | Count | Examples |
|------|-------|---------|
| Continents | 7 | Europe, Asia, North_America, Australia_Continent |
| Oceans / Seas / Lakes / Rivers | 13 | Pacific_Ocean, Mediterranean_Sea, Lake_Baikal, Danube_River |
| Countries | 32 | Bulgaria, Japan, USA, Brazil, Australia_Country |
| Cities | 30 | Sofia, Tokyo, Paris, Cairo, Washington_DC |
| Mountains / Peaks / Volcanoes | 13 | Himalayas, Everest, Mount_Fuji |
| Deserts / Forests / Islands | 11 | Sahara_Desert, Amazon_Rainforest, Sicily |
| Cultural Landmarks | 9 | Eiffel_Tower, Colosseum, Rila_Monastery |
| Persons | 13 | Rumen_Radev, Emmanuel_Macron, Xi_Jinping |
| Religions | 9 | Eastern_Orthodoxy, Islam_Sunni, Hinduism |
| Forms of Government | 6 | Parliamentary_Republic, Absolute_Monarchy |
| Architecture Styles | 6 | Gothic_Architecture, Modernism_Architecture |

Individual names are case-sensitive and use underscores: `North_America`, `Islam_Sunni`, `Eastern_Orthodoxy`. This naming convention is the source of Q21's 3B failure (see Section 9).

---

## 4. Prompt Engineering

### 4.1 System Prompt

The system prompt (`schema.py`) contains:

1. **Class hierarchy** — the full OWL class tree with defined class conditions
2. **Object and datatype properties** — domains, ranges, and key flags (Transitive, Functional, Symmetric)
3. **Named individuals** — grouped by type, so the LLM knows exact individual names
4. **11 SPARQL generation rules** — explicit instructions covering: prefix usage, individual naming conventions, transitive queries, defined class queries, negation patterns, numeric filters, aggregation functions, UNION, OPTIONAL, and MINUS

### 4.2 Few-Shot Examples

Seven worked examples are included in the prompt, one per core SPARQL construct pattern tested:

| # | SPARQL construct | Example question |
|---|----------------|-----------------|
| 1 | Direct property lookup | "What is the depth of Lake Baikal?" |
| 2 | Transitive `is_located_in` | "Which deserts are located in South America?" |
| 3 | `FILTER NOT EXISTS` negation | "Which buildings are not of Gothic architecture?" |
| 4 | Numeric `FILTER` combined with multiple triple patterns | "Which cities in Asia have a population greater than 5 million?" |
| 5 | `COUNT` aggregation | "How many peaks are there in Asia?" |
| 6 | `UNION` | "Which natural locations are either rivers or lakes?" |
| 7 | `OPTIONAL` | "Which mountains are in Asia and what is their height if known?" |

The examples cover seven distinct SPARQL constructs rather than mapping one-to-one to test categories. Notably, Cat 4 (Defined Class) has no dedicated example — the model relies on Rule 4 in the schema (`?x a geo:ClassName`) rather than a worked example. Cat 6 (Compositional) is covered by two examples (UNION and OPTIONAL) because its three questions each use a different combinator. Example 3 (FILTER NOT EXISTS) covers the Cat 7 negation pattern.

The number of examples was held at seven. Increasing the count risks *attention dilution* on a 3B model, where the model attends to the wrong example when generating a query. Each example was added only when the LLM reliably needed it for a genuinely new SPARQL construct.

### 4.3 Design Iterations

Several prompt choices evolved through experimentation:

**Inverse properties removed.** The ontology defines inverse pairs (`has_head_of_state` / `is_head_of_state`, `contains` / `is_located_in`). Including both directions in the schema caused the LLM to use the wrong direction approximately 30% of the time. Removing the inverse *names* while keeping a brief `inverse:` annotation reduced this failure to 0%.

**Self-verification rule removed.** An early schema rule instructed the LLM to verify its generated query before returning it. This did not improve accuracy (75% → 76% without it) and caused the LLM to introduce syntax errors during "verification," triggering unnecessary retries. It was removed.

**Location-derived defined classes removed.** The ontology defines `EuropeanCountry ≡ Country ∩ is_located_in some Europe` and `AsianCountry ≡ Country ∩ is_located_in some Asia`. Including these in the schema caused the LLM to generate queries like `?x a geo:EuropeanCountry`, which return empty results because OWL2-RL does not materialise instances of these classes (see Section 7.4). Removing them from the schema forces the LLM to generate the working `is_located_in` pattern. A full OWL-DL reasoner (e.g. Pellet or HermiT) could close this gap by handling the combination of an existential restriction over a transitive property with a named individual filler; however, the project stack specifies GraphDB with OWL2-RL, so the schema-side workaround was the appropriate fix within that constraint.

---

## 5. Query Categories

Twenty-two test questions are organised into seven categories ordered by *increasing inference complexity* — the amount of reasoning the LLM must perform to map the natural language question to the correct SPARQL construct:

| Cat | Name | Q# | LLM Inference Required |
|-----|------|----|------------------------|
| 1 | Direct Retrieval | Q1–Q3 | Vocabulary lookup: identify the correct property name |
| 2 | Transitivity | Q4–Q6 | Vocabulary + graph pattern; transitive reasoning performed by GraphDB |
| 3 | Numeric Filter | Q7–Q9 | Syntactic mapping: comparison operators → `FILTER`, `&&` |
| 4 | Defined Class | Q10–Q12 | Concept-to-class mapping: domain term → OWL class name |
| 5 | Aggregation | Q13–Q16 | Intent mapping: aggregate question → `COUNT`/`MAX`/`MIN`/`AVG` |
| 6 | Compositional | Q17–Q19 | Logical connective mapping: OR → `UNION`, conditional → `OPTIONAL`, difference → `MINUS` |
| 7 | Reasoning Required | Q20–Q22 | Ontological reasoning: absence/negation over transitive properties, exact individual naming, FILTER IN vs class usage |

Category 1 requires the least inference — the answer is an explicit triple and the LLM only needs the right property name. Each successive category adds a layer of reasoning: understanding transitivity (Cat 2), translating numeric language to filter syntax (Cat 3), mapping domain vocabulary to OWL class names (Cat 4), choosing the correct aggregation function from question intent (Cat 5), combining multiple graph patterns with logical connectives (Cat 6), and finally reasoning about data absence under the open-world assumption (Cat 7).

---

## 6. Query Analysis: Natural Language vs. SPARQL

This section demonstrates how natural language questions map to SPARQL for each category, in order of increasing inference complexity.

### Category 1 — Direct Retrieval

**Question:** "What is the form of government of Japan?"

```sparql
PREFIX geo: <http://example.org/geo_ontology_final.owl#>
SELECT ?gov WHERE {
  geo:Japan geo:has_form_of_government ?gov .
}
```

A single subject–predicate–object triple. The LLM must identify the correct property name (`has_form_of_government`) and use the named individual directly (`geo:Japan`). No reasoning is involved — the answer is an explicitly asserted triple.

---

### Category 2 — Transitivity

**Question:** "Which peaks are located in Europe?"

```sparql
PREFIX geo: <http://example.org/geo_ontology_final.owl#>
SELECT ?peak WHERE {
  ?peak a geo:Peak ;
        geo:is_located_in geo:Europe .
}
```

This query does not ask for peaks directly asserted to be in Europe. It relies on OWL2-RL having materialised the full transitive closure of `is_located_in`. A peak is in a mountain, which is in a country, which is in a continent — the chain spans three hops. Without reasoning, this query returns no results.

---

### Category 3 — Numeric Filter

**Question:** "Which peaks are higher than 5000 meters?"

```sparql
PREFIX geo: <http://example.org/geo_ontology_final.owl#>
SELECT ?peak WHERE {
  ?peak a geo:Peak ;
        geo:height ?h .
  FILTER(?h > 5000)
}
```

A single-threshold numeric filter. The `height` property is a `xsd:decimal` datatype property. `FILTER` is required because RDF/OWL properties cannot carry comparison operators directly — `?peak geo:height > 5000` is not valid SPARQL syntax. The LLM must introduce an intermediate variable (`?h`), bind it, and then filter on it.

**Question:** "Which cities have a population of more than 1 million?"

```sparql
PREFIX geo: <http://example.org/geo_ontology_final.owl#>
SELECT ?city WHERE {
  ?city a geo:City ;
        geo:population ?pop .
  FILTER(?pop > 1000000)
}
```

The same `FILTER` pattern combined with additional triple conditions. The critical point is that the numeric property (`population`) must be bound to a variable even when other triple patterns are present — the LLM must not place the comparison inside the triple directly as `geo:population > 1000000`.

**Question:** "Which peaks have a height between 3000 and 8000 meters?"

```sparql
PREFIX geo: <http://example.org/geo_ontology_final.owl#>
SELECT ?peak WHERE {
  ?peak a geo:Peak ;
        geo:height ?h .
  FILTER(?h > 3000 && ?h < 8000)
}
```

The `&&` operator combines two inequality conditions on the same variable. The LLM must map the natural language phrase "between X and Y" to two FILTER conditions joined by `&&`.

---

### Category 4 — Defined Class

**Question:** "Which cities are megacities?"

```sparql
PREFIX geo: <http://example.org/geo_ontology_final.owl#>
SELECT ?city WHERE {
  ?city a geo:Megacity .
}
```

`Megacity` is defined as any City with population ≥ 10,000,000. Instances are explicitly typed with `rdf:type geo:Megacity` in the OWL file, so the query returns results regardless of reasoning. The LLM must recognise that a defined class exists and use it directly, rather than writing a manual `FILTER(?pop >= 10000000)`.

**Question:** "Which countries are Sunni Islamic countries?"

```sparql
PREFIX geo: <http://example.org/geo_ontology_final.owl#>
SELECT ?country WHERE {
  ?country a geo:Country .
  FILTER EXISTS { ?country geo:has_main_religion geo:Islam_Sunni }
}
```

`SunniIslamicCountry` is a defined class in the ontology, but OWL2-RL does not materialise its instances. The reference query therefore uses `FILTER EXISTS` directly on the underlying property — querying `a geo:SunniIslamicCountry` returns an empty result set.

The root cause is that `SunniIslamicCountry` instances are never explicitly typed in the OWL file, and OWL2-RL inference also fails. The definition uses `someValuesFrom Islam_Sunni` where `Islam_Sunni` is a named individual referenced directly — OWL2-RL's `cls-svf1` rule fires only when the filler is an OWL class, not a named individual. Contrast this with `RepublicState`, whose 15 instances are explicitly typed with `rdf:type` assertions in the OWL file. Additionally, `RepublicState`'s definition wraps its fillers in `owl:oneOf {Parliamentary_Republic, Federal_Republic}` — an anonymous enumeration class — which would also allow OWL2-RL to infer membership via the `cls-oo` + `cls-svf1` chain even without explicit typing. Note that `Parliamentary_Republic` and `Federal_Republic` are named individuals (instances of `Form_of_Government`), not OWL classes; it is the `owl:oneOf` wrapper that creates an anonymous class expression, making the filler compatible with `cls-svf1`.

---

### Category 5 — Aggregation

**Question:** "How many countries are there in Europe?"

```sparql
PREFIX geo: <http://example.org/geo_ontology_final.owl#>
SELECT (COUNT(?country) AS ?count) WHERE {
  ?country a geo:Country ;
           geo:is_located_in geo:Europe .
}
```

`COUNT` returns a single row containing the number of matching bindings. The aggregate expression must be wrapped as `SELECT (COUNT(?var) AS ?alias)` — unlike direct SELECT queries, no list of individuals is returned. The `is_located_in geo:Europe` pattern relies on the transitive closure materialised by OWL2-RL (same as Category 2).

**Question:** "What is the maximum height among peaks in Asia?"

```sparql
PREFIX geo: <http://example.org/geo_ontology_final.owl#>
SELECT (MAX(?h) AS ?maxHeight) WHERE {
  ?peak a geo:Peak ;
        geo:is_located_in geo:Asia ;
        geo:height ?h .
}
```

`MAX()` is applied to a bound numeric variable and returns a single value. The same `SELECT (AGG(?var) AS ?alias)` syntax applies to all four aggregation functions used in this category: `COUNT` ("how many"), `MAX` ("maximum"), `MIN` ("minimum"), and `AVG` ("average"). The LLM must infer the correct function from question intent.

---

### Category 6 — Compositional

**Question:** "Which places are either mountains or volcanoes?"

```sparql
PREFIX geo: <http://example.org/geo_ontology_final.owl#>
SELECT ?place WHERE {
  { ?place a geo:Mountain }
  UNION
  { ?place a geo:Volcano }
}
```

`UNION` combines two graph patterns. A single triple pattern with a single class cannot express OR conditions — each alternative must be placed in its own group graph pattern.

**Question:** "List all countries in Europe and their main religion if one is defined."

```sparql
PREFIX geo: <http://example.org/geo_ontology_final.owl#>
SELECT ?country ?religion WHERE {
  ?country a geo:Country ;
           geo:is_located_in geo:Europe .
  OPTIONAL { ?country geo:has_main_religion ?religion }
}
```

`OPTIONAL` includes rows where the optional pattern does not match. Countries without a `has_main_religion` triple appear in the results with `?religion` unbound. Without `OPTIONAL`, countries with no defined religion would be silently excluded.

**Question:** "Which capital cities are not megacities?"

```sparql
PREFIX geo: <http://example.org/geo_ontology_final.owl#>
SELECT ?city WHERE {
  { ?city a geo:CapitalCity }
  MINUS
  { ?city a geo:Megacity }
}
```

`MINUS` subtracts from the first graph pattern any results that also match the second. Unlike `FILTER NOT EXISTS`, which operates within a single pattern, `MINUS` operates between two independent graph patterns. Both are valid here; `MINUS` is the idiomatic choice when the two sets are structurally separate.

---

### Category 7 — Reasoning Required

**Question:** "Which volcanoes are not located in Europe?"

```sparql
PREFIX geo: <http://example.org/geo_ontology_final.owl#>
SELECT ?volcano WHERE {
  ?volcano a geo:Volcano .
  FILTER NOT EXISTS { ?volcano geo:is_located_in geo:Europe }
}
```

No class like `NonEuropeanVolcano` exists. The correct query uses `FILTER NOT EXISTS` on the `is_located_in` property, combined with the transitive closure that OWL2-RL materialises — Etna and Vesuvius are inferred to be `is_located_in geo:Europe` via the transitive closure: Etna → Sicily → Europe, Vesuvius → Italy → Europe. The query therefore correctly returns only Mount_Fuji. The LLM must reason that "not located in Europe" maps to negation over a location property rather than inverting a class name.

**Question:** "Which countries are in North America?"

```sparql
PREFIX geo: <http://example.org/geo_ontology_final.owl#>
SELECT ?country WHERE {
  ?country a geo:Country ;
           geo:is_located_in geo:North_America .
}
```

No class like `NorthAmericanCountry` exists. The LLM must use the `is_located_in` property with the exact individual name `geo:North_America`. The model frequently abbreviates this to `geo:N_America`, which does not exist and returns empty results.

**Question:** "Which countries are republics?"

```sparql
PREFIX geo: <http://example.org/geo_ontology_final.owl#>
SELECT ?country WHERE {
  ?country a geo:Country ;
           geo:has_form_of_government ?gov .
  FILTER(?gov IN (geo:Parliamentary_Republic, geo:Federal_Republic))
}
```

`RepublicState` is a defined class in the ontology (Country with form of government Parliamentary_Republic or Federal_Republic). Unlike `SunniIslamicCountry` or `EuropeanCountry`, it returns results — empirically, `?x a geo:RepublicState` returns 15 countries — because those 15 countries are explicitly typed with `rdf:type RepublicState` in the OWL file. The reference query nonetheless uses `FILTER IN` for clarity. The LLM's failure modes are structural rather than empty-class: adding a `geo:name` constraint that has no matching triples, misplacing `UNION` outside the SELECT block, using pipe (`|`) syntax in a WHERE clause, or AND-conjoining two `has_form_of_government` triples (logically impossible for a single entity).

---

## 7. OWL2-RL Inference Analysis

### 7.1 What OWL2-RL Provides

OWL2-RL is a tractable profile of OWL2 designed for scalable rule-based reasoning. When enabled in GraphDB, it materialises inferred triples — writing them into the repository so that SPARQL queries can find them. The system operates entirely through standard SPARQL SELECT; no property paths or SPARQL reasoning extensions are used. All inference work is done by the reasoner at load time.

### 7.2 Demonstration — Transitive Closure (Category 2)

The `is_located_in` property is declared Transitive. Consider peak `Musala`:

| Triple | Status |
|--------|--------|
| `Musala is_located_in Rila` | Asserted |
| `Rila is_located_in Bulgaria` | Asserted |
| `Bulgaria is_located_in Europe` | Asserted |
| `Musala is_located_in Bulgaria` | **Inferred by OWL2-RL** |
| `Musala is_located_in Europe` | **Inferred by OWL2-RL** |

**With OWL2-RL ON:** The query "Which peaks are located in Europe?" returns all peaks whose chain of `is_located_in` triples eventually reaches `geo:Europe`. For this ontology: `Musala`, `Vihren`, `Mont_Blanc`.

**With OWL2-RL OFF:** The same SPARQL query searches only asserted triples. Since peaks are asserted to be in mountains, not directly in Europe, the query returns an empty result set.

This is the clearest demonstration of OWL2-RL value in this project: an identical SPARQL query produces correct results with reasoning and empty results without it.

### 7.3 Demonstration — Defined Class Materialisation (Category 4)

`Megacity ≡ City ∩ population ≥ 10,000,000`

In this ontology, instances of `Megacity`, `CapitalCity`, `RepublicState`, and `HighPeak` are **explicitly typed** with `rdf:type` assertions in the OWL file — the ontology author asserted class membership directly rather than relying purely on inference. As a result, queries like `?city a geo:Megacity` return results regardless of whether OWL2-RL is enabled. The equivalentClass definitions are logically correct, and OWL2-RL would in principle materialise additional instances through inference (`CapitalCity` via the `cls-hv2` rule for `owl:hasValue`; `RepublicState` via `cls-oo` + `cls-svf1` because its form-of-government fillers are wrapped in `owl:oneOf`), but since all instances are already explicitly asserted, this inference is redundant in practice.

The meaningful contrast is with `SunniIslamicCountry`: its instances are **not** explicitly typed anywhere in the OWL file, so the query depends entirely on OWL2-RL inference — which fails (see Section 7.4). This is why `?country a geo:SunniIslamicCountry` returns empty results while `?city a geo:Megacity` returns three cities.

### 7.4 OWL2-RL Limitation — Location-Derived Defined Classes

The ontology also defines `EuropeanCountry ≡ Country ∩ is_located_in some Europe`. Despite OWL2-RL being enabled and all European countries being correctly asserted with `is_located_in geo:Europe`, this class has **zero materialised instances** in GraphDB.

Querying `?x a geo:EuropeanCountry` returns no results, while the equivalent `?x a geo:Country ; geo:is_located_in geo:Europe` returns 13 countries.

The cause is the same root issue as `SunniIslamicCountry`: the `someValuesFrom` filler is a named individual (`Europe`) referenced directly, and OWL2-RL's `cls-svf1` rule requires the filler to be an OWL class. Since `EuropeanCountry` instances are also not explicitly typed in the OWL file, there is no fallback — both inference and explicit assertion are absent. OWL2-RL is a *strict subset* of full OWL2 reasoning; some inference patterns that a full OWL2-DL reasoner (Pellet, HermiT) would complete are intentionally excluded for scalability.

**Impact on the NLQ system:** The LLM correctly identifies `EuropeanCountry` as semantically relevant for questions about European countries. It generates syntactically valid SPARQL using the class. The query executes without error and returns zero results. This is a failure caused by a gap between the ontology's definition and the reasoner's execution — not by incorrect language understanding on the LLM's part.

**Workaround:** `EuropeanCountry` and `AsianCountry` were removed from the schema presented to the LLM. Without seeing these class names, the LLM generates `is_located_in` queries, which work correctly. This is a prompt engineering workaround, not a fix to the underlying issue. A proper fix would require either upgrading to a full OWL2-DL reasoner or adding explicit `rdf:type EuropeanCountry` assertions to the ontology for each European country.

### 7.5 The Open-World Assumption and Absence Queries

OWL's open-world assumption states that the absence of a triple does not imply its negation. The `LandlockedCountry` class is defined as a country that contains no Sea or Ocean. The reasoner cannot materialise instances of this class because, under the open-world assumption, it cannot conclude that a country *has no sea* merely from the fact that no `contains Sea` triple has been asserted.

This is not a limitation of OWL2-RL specifically — no OWL-based reasoner under the open-world assumption would materialise `LandlockedCountry` instances. The correct query pattern for this type of question is `FILTER NOT EXISTS` on the raw data, which performs a closed-world check at query time rather than relying on inference.

---

## 8. Experimental Results

### 8.1 Prompt Engineering Evolution — Direct Retrieval, Transitivity, Defined Class, Reasoning Required

Three iterative benchmark runs were conducted on 11 questions covering Direct Retrieval (Cat 1), Transitivity (Cat 2), Defined Class (Cat 4), and Reasoning Required (Cat 7) — the categories introduced first. At this stage, Cat 7 comprised only Q20 (a landlocked-country question, later replaced) and Q21; Q22 had not yet been added. Each run of 10 repetitions per question tested one schema change against the previous baseline.

| Run | Change | Overall | Cat 1 (Direct) | Cat 2 (Transit.) | Cat 4 (Defined) | Cat 7 (Reasoning) | Retries |
|-----|--------|---------|----------------|------------------|-----------------|-------------------|---------|
| 1 | Baseline (self-verify rule, inverse properties in schema) | 75% | 80% | 100% | 87% | 10% | 2 |
| 2 | Self-verify rule removed | 76% | 87% | 100% | 93% | 0% | 0 |
| 3 | Inverse properties removed from schema | **78%** | 90% | 100% | 90% | 10% | 0 |

Each change produced a small but consistent improvement. The self-verify rule removal eliminated spurious syntax retries. Removing inverse property names from the schema eliminated the direction-confusion failure in Category 1.

### 8.2 Baseline Benchmark — qwen2.5-coder:3b, 20 Questions (10 runs)

After Numeric Filter (Cat 3), Aggregation (Cat 5), and Compositional (Cat 6) questions were introduced and the `EuropeanCountry`/`AsianCountry` schema fix was applied, a 10-run benchmark was conducted across the initial 20 questions (Q1–Q18 plus the original Q20 (landlocked) and Q21 (North America); Q19 (MINUS) and Q22 (RepublicState) had not yet been added; 200 total question-runs).

| Category | Questions | Exact | Accuracy |
|----------|-----------|-------|----------|
| 1 — Direct Retrieval | 3 | 26/30 | 87% |
| 2 — Transitivity | 3 | 30/30 | **100%** |
| 3 — Numeric Filter | 3 | 30/30 | **100%** |
| 4 — Defined Class | 3 | 23/30 | 77% |
| 5 — Aggregation | 4 | 27/40 | 68% |
| 6 — Compositional | 2 | 16/20 | 80% |
| 7 — Reasoning Required | 2 | 1/20 | 5% |
| **Overall** | **20** | **153/200** | **76%** |

Syntax retries: 4 across all 200 runs.

### 8.3 Model Comparison — qwen2.5-coder:3b vs qwen2.5-coder:7b, 22 Questions (10 runs)

Two questions were added to complete the category set: Q19 (MINUS, Cat 6) and Q22 (RepublicState, Cat 7). Before the final benchmark run, Q20 was revised — the original landlocked-country question was replaced with a volcanoes-not-in-Europe question that correctly tests `FILTER NOT EXISTS` over the materialised transitive closure. OWL mathematical set notation (∪, ∩, ¬) was also removed from the schema to prevent notation bleed into generated SPARQL. Both models were benchmarked on the full 22-question set across 10 runs (220 total question-runs each).

| Category | Questions | 3b Exact | 3b % | 7b Exact | 7b % |
|----------|-----------|----------|------|----------|------|
| 1 — Direct Retrieval | 3 | 29/30 | 97% | 30/30 | **100%** |
| 2 — Transitivity | 3 | 30/30 | **100%** | 30/30 | **100%** |
| 3 — Numeric Filter | 3 | 30/30 | **100%** | 24/30 | 80% |
| 4 — Defined Class | 3 | 24/30 | 80% | 26/30 | 87% |
| 5 — Aggregation | 4 | 31/40 | 78% | 40/40 | **100%** |
| 6 — Compositional | 3 | 27/30 | 90% | 28/30 | 93% |
| 7 — Reasoning Required | 3 | 9/30 | 30% | 26/30 | 87% |
| **Overall** | **22** | **180/220** | **82%** | **204/220** | **93%** |

Syntax retries: 2 (3B), 1 (7B).

### 8.4 Per-Question Breakdown

| Q | 3b rate | 7b rate | Question |
|---|---------|---------|----------|
| Q1 | 100% | 100% | What is the form of government of Japan? |
| Q2 | 90% | 100% | What is the population of France? |
| Q3 | 100% | 100% | Who is the head of state of Bulgaria? |
| Q4 | 100% | 100% | Which mountains are located in Asia? |
| Q5 | 100% | 100% | Which peaks are located in Europe? |
| Q6 | 100% | 100% | Which cities are located in South America? |
| Q7 | 100% | **50%** | Which peaks are higher than 5000 meters? |
| Q8 | 100% | 90% | Which cities have a population of more than 1 million? |
| Q9 | 100% | 100% | Which peaks have a height between 3000 and 8000 meters? |
| Q10 | 90% | 100% | Which cities are megacities? |
| Q11 | 80% | 90% | Which cities are capital cities? |
| Q12 | 70% | 70% | Which countries are Sunni Islamic countries? |
| Q13 | 100% | 100% | How many countries are there in Europe? |
| Q14 | 70% | 100% | What is the maximum height among peaks in Asia? |
| Q15 | 70% | 100% | What is the minimum population of a country in Africa? |
| Q16 | 70% | 100% | What is the average population of countries in Europe? |
| Q17 | 100% | 100% | Which places are either mountains or volcanoes? |
| Q18 | **100%** | 90% | List all countries in Europe and their main religion if one is defined. |
| Q19 | 70% | 90% | Which capital cities are not megacities? |
| Q20 | 70% | **100%** | Which volcanoes are not located in Europe? |
| Q21 | **0%** | 100% | Which countries are in North America? |
| Q22 | **20%** | 60% | Which countries are republics? |

### 8.5 Model Comparison Analysis

The 7B model outperforms the 3B model by 11 percentage points overall (93% vs 82%), with improvements concentrated in specific categories.

**Where 7B is clearly better:**

- **Aggregation (Cat 5): 100% vs 78%.** The most significant gain. The 3B model wraps the property variable in `OPTIONAL` in Q14–Q16, causing aggregate functions over unbound variables to return no results roughly 30% of the time. The 7B model binds the property correctly in all cases, achieving 100% across Q13–Q16.

- **Reasoning Required (Cat 7): 87% vs 30%.** The sharpest category gap. Q20 (Volcanoes not in Europe) reaches 100% for the 7B model but only 70% for the 3B model. Q21 (North America) remains 0% for the 3B model — it abbreviates `North_America` — but 100% for the 7B model. Q22 (Republics) is the weakest question for both models: 20% (3B) and 60% (7B).

**Where 3B performs comparably:**

- **Numeric Filter (Cat 3): 100% vs 80%.** The 3B model remains perfect across all three numeric filter questions. The 7B model drops to 50% on Q7 ("peaks higher than 5000 meters"), and achieves 90% on Q8 ("cities with population > 1 million"), where a small number of runs still use an invalid property-value triple instead of `FILTER`.

- **Compositional (Cat 6): 90% vs 93%.** Both models perform similarly. A revised few-shot example (combining a location triple with additional triple conditions) improved 3B's Q18 from 40% to 100%, and Q19 from 30% to 70%. The 7B model is marginally ahead due to Q19 (90% vs 70%).

**The persistent hard failure is Q12** (Sunni Islamic countries, 70%/70%) — equally limited by OWL2-RL materialisation for both models. Q22 (Republics) is the second hard failure, particularly for 3B (20%), where the model tends to use `RepublicState` as a property value rather than a class type.

---

## 9. Failure Mode Analysis

| Question | 3b rate | 7b rate | Root cause |
|----------|---------|---------|-----------|
| Q7 — Peaks > 5000m | 100% | **50%** | 7B regression: drops `FILTER` and uses comparison as a property triple; identical pattern across failures |
| Q11 — Capital cities | 80% | 90% | 3B adds bogus constraints (`geo:name ?name`, `geo:is_located_in geo:Country`); 7B occasionally generates extra conditions |
| Q12 — Sunni Islamic countries | 70% | 70% | LLM uses `a geo:SunniIslamicCountry`; OWL2-RL does not materialise `someValuesFrom` over a named individual |
| Q14 — MAX peak height | 70% | 100% | 3B wraps height property in `OPTIONAL`, causing `MAX` over unbound variable → no results; also uses `Mountain` instead of `Peak` |
| Q15 — MIN population | 70% | 100% | 3B omits `geo:population ?pop` binding from WHERE clause; aggregate over unbound variable returns no results |
| Q16 — AVG population | 70% | 100% | 3B: diverse failures (wrong class name, missing binding); both models improved from prior run |
| Q19 — MINUS capitals/megacities | 70% | 90% | 3B abandons MINUS in ~30% of runs; 7B occasionally adds unnecessary constraints |
| Q20 — Volcanoes not in Europe | 70% | 100% | 3B occasionally misapplies `FILTER NOT EXISTS` scope or uses the wrong property in the negation pattern |
| Q21 — North America | **0%** | 100% | 3B abbreviates `North_America` → `N_America` (9/10) or `N.America` (1/10); 7B uses the full individual name correctly |
| Q22 — Republics | **20%** | 60% | 3B uses `RepublicState` as a property value rather than a class type; 7B: structural errors (pipe syntax, UNION outside SELECT) |

### Failure Type 1: Using a defined class that has no instances

Q12 involves a defined class where OWL2-RL materialisation is unreliable: `SunniIslamicCountry` uses `someValuesFrom` over a named individual, which the OWL2-RL rule chain does not fire for. The LLM's choice to use the class name is semantically correct but produces empty results — the failure is in the gap between the ontology's definition and the triplestore's execution. Both models achieve 70% on Q12 in the final benchmark — an improvement for the 3B model over earlier runs. The fundamental OWL2-RL limitation remains regardless of model size.

### Failure Type 2: Individual name precision

The 3B model abbreviates individual names: `North_America` becomes `N_America` (9 out of 10 runs) or `N.America` (1 out of 10). Neither individual exists in the ontology; the query executes but returns no results. Q21 achieves 0% for the 3B model despite explicit schema rules listing the full name. The 7B model resolves this completely (100%), demonstrating that individual name precision improves with model size.

### Failure Type 3: Property name confusion

In earlier benchmarks, the 7B model occasionally generated `has_created` (who founded Bulgaria) instead of `has_head_of_state` (who currently leads it), reducing Q3 accuracy to 90%. In the final benchmark both models achieve 100% on Q3, suggesting this was sampling noise rather than a stable failure mode. It is noted here as a potential risk: the larger model's broader vocabulary can introduce semantic confusion on property selection when a plausible but incorrect alternative exists.

### Failure Type 4: OPTIONAL wrapping in aggregation

For Q14–Q16, the 3B model wraps the property variable in `OPTIONAL { ?x geo:height ?h }`. This makes the binding optional, meaning the variable may be unbound for some results. SPARQL aggregates over an unbound variable return no results, causing a complete failure even though the surrounding query structure is correct — roughly 30% of runs fail for this reason. The 7B model binds the property directly in all cases and achieves 100% across all four aggregation questions.

### Failure Type 5: Named individual treated as a class

For Q18, earlier benchmarks showed the 3B model generating `?country a geo:Europe` in approximately two-thirds of failing runs — treating the continent individual as an OWL class. A revised few-shot example demonstrating how to combine a location pattern with other triple conditions resolved this failure: Q18 reaches 100% for the 3B model in the final benchmark. The fix illustrates that targeted few-shot examples can eliminate specific structural failure modes entirely.

### Failure Type 6: Numeric comparison as property triple

The 7B model occasionally places a numeric comparison directly in the WHERE clause as a property-value triple (`geo:height > 5000`) rather than binding the value to a variable and using `FILTER(?h > 5000)`. This is syntactically invalid SPARQL. In the final benchmark this failure appears on Q7 (50% for 7B) while the 3B model is unaffected — the 3B model benefits from a few-shot example that explicitly combines a location triple with a numeric variable binding and `FILTER`, reinforcing the correct pattern.

### Failure Type 7: Context confusion producing unrelated output

For Q19 (capital cities not megacities), earlier 3B benchmarks produced queries entirely unrelated to the question — lakes/rivers or Asian mountain heights. The revised few-shot example reduced this to 70% accuracy for 3B (up from 30%), with remaining failures being structural errors rather than full context loss. The 7B model reaches 90% on Q19.

---

## 10. Discussion

### What the 3B model handles well

The qwen2.5-coder:3b model demonstrates strong performance on queries with direct structural parallels in the few-shot examples: single-triple lookups, transitive location queries, numeric filters, and aggregation functions. The few-shot prompting approach is effective — the model generalises well from one example per category to multiple questions of the same structural pattern.

The model is also effective at extracting SPARQL from its own responses reliably. In all three benchmark runs, EXTRACTION FAILED was never observed — the model consistently wrapped its output in a SPARQL code block.

### What it struggles with

The model's main difficulties are:

1. **Recognising when negation is required without a class name to lean on.** The 7B model handles `FILTER NOT EXISTS` reliably when a clear few-shot example matches (Q20: 100%); the 3B model succeeds in most but not all cases (Q20: 70%). The deeper difficulty arises when no matching class exists and the model must independently decide that the question requires negation — a reasoning step beyond pattern matching.

2. **Exact individual names.** With the 3B model, occasional spelling abbreviation of long individual names (`North_America`) persists despite explicit rules (Q21: 0%). The 7B model resolves this completely (Q21: 100%), confirming that individual name precision scales with model size.

3. **Shortcut class usage.** When a defined class name is visible in the schema and semantically matches the question, the model consistently uses it — even when schema rules say not to. The only reliable fix was removing the class names from the schema entirely.

### On the model size comparison

The 3B model was chosen as the baseline for practical reasons: it runs efficiently on consumer hardware (fits fully in 4GB VRAM) and generates responses in approximately 4 seconds per question. The 7B model requires ~7 seconds per question on the same hardware and partially spills to CPU RAM.

The comparison benchmark confirms that the 7B model provides a substantial overall improvement (+11pp, 93% vs 82%), with the largest gains in Aggregation (Cat 5: 100% vs 78%) and Reasoning Required (Cat 7: 87% vs 30%). Q21 (North America) remains 0% for 3B and 100% for 7B. Q20 (Volcanoes not in Europe) reaches 100% for 7B but only 70% for 3B. Conversely, the 3B model is stronger on Numeric Filter (Cat 3: 100% vs 80%), and the two models are nearly equal on Compositional (Cat 6: 90% vs 93%) — confirming that larger models have a different, not uniformly better, failure distribution.

The two hard failures that persist regardless of model size are Q12 (Sunni Islamic countries, 70%/70%) — an OWL2-RL materialisation limitation — and Q22 (Republics, 20%/60%), where both models struggle with the structural complexity of querying a defined class whose instances depend on explicit typing.

---

## 11. Conclusions

This project demonstrates that locally-hosted small language models can reliably translate natural language geographic questions into valid SPARQL for a medium-complexity OWL ontology under the right prompting conditions. In a 10-run benchmark across all 22 questions, the 3B model achieves **82% overall exact-match accuracy** (180/220) and the 7B model achieves **93%** (204/220). Category 2 (Transitivity) reaches 100% for both models; Category 7 (Reasoning Required) reaches 87% for the 7B model but only 30% for the 3B model.

The main findings are:

**1. OWL2-RL transitivity inference is essential for geographic containment queries.** The same SPARQL query returns correct results with reasoning enabled and empty results without it. Transitive closure materialisation is the single most important reasoning feature for this ontology.

**2. Not all defined classes are materialised by OWL2-RL.** Classes like `Megacity`, `CapitalCity`, and `RepublicState` return results correctly because their instances are **explicitly typed** in the OWL file — they would work even with OWL2-RL disabled. `SunniIslamicCountry` fails on both counts: its instances are not explicitly typed, and OWL2-RL inference also fails because the `someValuesFrom` restriction references `Islam_Sunni` as a direct named individual, which `cls-svf1` cannot handle. `EuropeanCountry` fails for the same reason — `someValuesFrom Europe` with a direct individual filler, and no explicit type assertions. `LandlockedCountry` is never materialised under the open-world assumption regardless of reasoner. These gaps must be understood and worked around in both the prompt and the reference queries.

**3. Prompt engineering choices have measurable, consistent impact.** Each of the three schema changes — removing inverse properties, removing the self-verify rule, removing non-materialising defined classes — produced a measurable accuracy improvement. The lesson is that the schema presented to the LLM should describe the *usable query interface*, not be a faithful dump of the OWL file. Features that are valid in the ontology but produce empty results in practice should be excluded from the prompt.

**4. The open-world assumption creates a hard barrier for negation-based queries against non-asserted data.** The `LandlockedCountry` class — defined as a country containing no Sea or Ocean — cannot be materialised by any OWL reasoner under the open-world assumption, because the absence of a `contains Sea` triple does not entail that no sea exists. The correct query pattern is `FILTER NOT EXISTS`, which performs a closed-world check at query time. Q20 demonstrates that this pattern is largely learnable from a single few-shot example: the 7B model achieves 100% and the 3B model achieves 70% on "Which volcanoes are not located in Europe?" — a question that uses `FILTER NOT EXISTS` over the materialised transitive closure. The difficulty is not the SPARQL construct itself but identifying *when* to use it without a matching class name in the schema.

**5. The NLQ failure mode for defined classes is subtle.** When the LLM uses `a geo:EuropeanCountry`, the query is syntactically valid, executes without error, and returns empty results. This type of failure — semantically correct reasoning producing incorrect results — is harder to detect and explain than a syntax error. It is caused by a gap between ontology definition and reasoner execution, not by LLM reasoning failure.

**6. Scaling model size improves overall accuracy but changes, not eliminates, the failure distribution.** The 7B model scores 11 percentage points higher overall (93% vs 82%) and eliminates the OPTIONAL-wrapping aggregation failure (Cat 5: 100% vs 78%) and the individual name abbreviation in Q21 (100% vs 0%). However, it introduces a regression on Q7 (50% vs 100%) and performs worse on Q22 (60% vs 20%). The two persistent hard limits are Q12 (Sunni Islamic, 70%/70%) — an OWL2-RL materialisation gap — and Q22 (Republics), which is a hard failure for the 3B model (20%) and a moderate challenge for the 7B model (60%).
