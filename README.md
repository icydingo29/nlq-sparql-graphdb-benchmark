# Geographic Ontology NLQ Tester

Connects a geographic OWL ontology to a local LLM via Python.
Users ask questions in natural language; the app translates them to SPARQL via Ollama,
executes the query against GraphDB, and compares results to hand-written reference queries.

---

## Manual Prerequisites

### 1. GraphDB

1. Download and install [GraphDB Free](https://www.ontotext.com/products/graphdb/graphdb-free/).
2. Start GraphDB — it must be listening on **port 7200**.
3. Create a repository named **`geo`** with **OWL2-RL** reasoning enabled:
   - Workbench → Setup → Repositories → Create new repository
   - Type: GraphDB Repository
   - Repository ID: `geo`
   - Ruleset: **OWL2-RL** (ensures `Megacity`, `CapitalCity`, `RepublicState`, etc. are materialised)
4. Import the OWL file:
   - Import → RDF → Upload local files → select `data/3MI3400841_3MI3400791_GeoOntology.owl`
   - Import into named graph (or default graph).

### 2. Ollama

1. Download and install [Ollama](https://ollama.com/).
2. Start Ollama — it must be listening on **port 11434**.
3. Pull the model:
   ```
   ollama pull qwen2.5-coder:3b
   ```
   If results are poor, upgrade to `qwen2.5-coder:7b` and update `OLLAMA_MODEL` in `config.py`.

---

## Setup

```bash
# Activate the virtual environment (Windows)
venv\Scripts\Activate.ps1

# Install dependencies (already done if venv is fresh)
pip install -r requirements.txt
```

---

## Running

```bash
python main.py
```

The interactive menu lets you:
- Run individual test questions (numbered 1–11)
- Run all questions with a summary table (`A`)
- Ask a free-form natural language question (`F`)
- Quit (`Q`)

---

## Changing the Model

Edit **`config.py`** — only the `OLLAMA_MODEL` line:

```python
OLLAMA_MODEL = "qwen2.5-coder:7b"   # upgrade path
```

No other file needs to change.

---

## Project Structure

| File | Purpose |
|---|---|
| `config.py` | Ollama URL, model name, GraphDB endpoint — single source of truth |
| `schema.py` | Static ontology schema summary included in every prompt |
| `prompt.py` | Assembles system message + 3 few-shot examples + user question |
| `llm.py` | POSTs to Ollama `/api/chat`, extracts SPARQL from response |
| `graphdb.py` | POSTs SPARQL to GraphDB, returns result rows |
| `questions.py` | 11 reference test questions with expected results |
| `main.py` | Interactive CLI loop |

---

## Test Categories

| # | Category | What it tests |
|---|---|---|
| 1 | Direct Retrieval | Single-hop property reads, simple type lookups |
| 2 | Transitivity | Multi-hop `is_located_in` (transitive closure materialised by OWL2-RL) |
| 3 | Defined Class | Defined classes with materialised instances (Megacity, CapitalCity, …) |
| 4 | Reasoning Required | Classes with no materialised instances (LandlockedCountry) or concepts with no class at all |

## Notes

data/geo_project.py was used to generate the OWL file via owlready2. The library is not required to run the app.
