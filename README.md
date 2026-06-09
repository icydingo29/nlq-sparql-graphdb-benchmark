# Geographic Ontology NLQ Tester

Connects a geographic OWL ontology to a local LLM via Python.
Users ask questions in natural language; the app translates them to SPARQL via Ollama,
executes the query against GraphDB, and compares results to reference queries run live against the triplestore.

---

## Prerequisites

### 1. Python 3.10+

Download from [python.org](https://www.python.org/downloads/). Verify with:

```
python --version
```

### 2. GraphDB Free

1. Download and install [GraphDB Free](https://www.ontotext.com/products/graphdb/graphdb-free/).
2. Start GraphDB — it must be listening on **port 7200**.
3. Open the Workbench at `http://localhost:7200`.
4. Create a repository:
   - Setup → Repositories → Create new repository
   - Type: **GraphDB Repository**
   - Repository ID: **`geo`**
   - Ruleset: **OWL2-RL** (materialises defined classes like `Megacity`, `CapitalCity`, `EuropeanCountry`, etc.)
   - Entity ID size: **40** (handles large ontologies without hash collisions)
   - Leave all other settings at their defaults, then click **Create**.
5. Import the OWL file:
   - Import → RDF → Upload local files
   - Select `data/3MI3400841_3MI3400791_GeoOntology.owl`
   - Click **Import** and confirm with the default settings (imports into the default graph).
6. Verify reasoning is active: after import, the Explore tab should show instances of `geo:Megacity`, `geo:CapitalCity`, etc.

### 3. Ollama

1. Download and install [Ollama](https://ollama.com/).
2. Start Ollama — it must be listening on **port 11434**.
3. Pull the model:
   ```
   ollama pull qwen2.5-coder:3b
   ```

---

## Setup

```powershell
# 1. Clone / extract the project, then open a terminal in the project folder.

# 2. Create a virtual environment
python -m venv venv

# 3. Activate it (PowerShell)
venv\Scripts\Activate.ps1

# If execution policy blocks the script, run once:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 4. Install dependencies
pip install -r requirements.txt
```

---

## Running

Make sure GraphDB and Ollama are running, then:

```powershell
# Activate the venv if not already active
venv\Scripts\Activate.ps1

python main.py
```

The interactive menu lets you:

| Key | Action |
|-----|--------|
| `1`–`11` | Run a single test question with full output |
| `A` | Run all questions with full output and a summary |
| `S` | Run all questions — prints one line for each EXACT match, full block for failures |
| `B` | Benchmark mode — runs all questions N times silently, reports per-category accuracy |
| `F` | Ask a free-form natural language question |
| `Q` | Quit |

---

## Changing the Model

Edit **`config.py`** — only the `OLLAMA_MODEL` line:

```python
OLLAMA_MODEL = "qwen2.5-coder:7b"   # upgrade for better accuracy
```

Then pull the new model in Ollama:

```
ollama pull qwen2.5-coder:7b
```

No other file needs to change.

---

## Project Structure

| File | Purpose |
|------|---------|
| `config.py` | Ollama URL, model name, GraphDB endpoint — single source of truth |
| `schema.py` | Ontology schema summary included in every LLM prompt |
| `prompt.py` | Assembles system message + 3 few-shot examples + user question |
| `llm.py` | POSTs to Ollama `/api/chat`, extracts SPARQL from response; retries on syntax errors |
| `graphdb.py` | POSTs SPARQL to GraphDB, parses SPARQL 1.1 JSON results |
| `questions.py` | 11 reference test questions; reference SPARQL is executed live against GraphDB |
| `main.py` | Interactive CLI — menu, test runner, benchmark mode |
| `data/` | OWL ontology file (not tracked by git if large; add manually) |

---

## Test Categories

| # | Category | What it tests |
|---|----------|---------------|
| 1 | Direct Retrieval | Single-hop property reads (population, form of government, head of state) |
| 2 | Transitivity | Multi-hop `is_located_in` — transitive closure materialised by OWL2-RL |
| 3 | Defined Class | Classes with materialised instances (`Megacity`, `CapitalCity`, `SunniIslamicCountry`) |
| 4 | Reasoning Required | `LandlockedCountry` (no materialised instances due to open-world assumption); concepts with no dedicated class |

---

## Notes

- `data/geo_project.py` was used to generate the OWL file via owlready2. The library is **not** required to run the app.
- On syntax errors (HTTP 400 from GraphDB), the app automatically asks the LLM to fix the query and retries up to 2 times.
- Benchmark results vary between runs due to LLM non-determinism. Use mode `B` with at least 10 runs for reliable accuracy statistics.
