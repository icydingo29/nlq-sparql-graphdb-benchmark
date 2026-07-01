# Geographic Ontology NLQ Tester

Connects a geographic OWL ontology to a local LLM via Python.
Users ask questions in natural language; the app translates them to SPARQL via Ollama,
executes the query against GraphDB, and compares the results to reference queries run live against the triplestore.

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
   - Ruleset: **OWL2-RL** (materialises defined classes like `Megacity`, `CapitalCity`, `RepublicState`, etc.)
   - Entity ID size: **40** (handles large ontologies without hash collisions)
   - Leave all other settings at their defaults, then click **Create**.
5. Import the OWL file:
   - Import → RDF → Upload local files
   - Select `data/GeoOntology.owl`
   - Click **Import** and confirm with the default settings (imports into the default graph).
6. Verify reasoning is active: after import, the Explore tab should show instances of `geo:Megacity`, `geo:CapitalCity`, `geo:RepublicState`, etc.

### 3. Ollama

1. Download and install [Ollama](https://ollama.com/).
2. Start Ollama — it must be listening on **port 11434**.
3. Pull the model(s) you intend to use:
   ```
   ollama pull qwen2.5-coder:3b
   ollama pull qwen2.5-coder:7b
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

The interactive menu offers four options:

| Key | Action |
|-----|--------|
| `S` | Run a single test question with full output (LLM SPARQL, results, reference, match label) |
| `F` | Ask a free-form natural language question and see the SPARQL and results |
| `B` | Benchmark mode — runs questions N times silently, reports per-category and overall accuracy |
| `Q` | Quit |

### Benchmark mode

After selecting `B`, you will be prompted for:

1. **Scope** — `S` single question, `C` one category, `A` all 22 questions
2. **Runs** — number of repetitions (default: 10)
3. **Output mode**:
   - `P` — progress only: one line per run showing exact matches (default)
   - `F` — failure patterns: after the summary, prints every unique failing SPARQL per question with its count and LLM vs. reference results
   - `V` — verbose: one result line per question per run

---

## Changing the Model

Edit **`config.py`** — only the `OLLAMA_MODEL` line:

```python
OLLAMA_MODEL = "qwen2.5-coder:3b"   # faster, lower accuracy
# OLLAMA_MODEL = "qwen2.5-coder:7b" # slower, higher accuracy
```

Then pull the model in Ollama if you have not already:

```
ollama pull qwen2.5-coder:3b
```

No other file needs to change.

---

## Project Structure

| File | Purpose |
|------|---------|
| `config.py` | Ollama URL, model name, GraphDB endpoint — single source of truth |
| `schema.py` | Full ontology schema (class hierarchy, properties, named individuals) + 11 SPARQL generation rules; included as the system prompt in every LLM call |
| `prompt.py` | 7 few-shot examples (one per core SPARQL construct); assembles system + few-shot + user message list |
| `llm.py` | POSTs to Ollama `/api/chat`, extracts SPARQL from the response; `fix()` retries on syntax errors |
| `graphdb.py` | POSTs SPARQL to GraphDB, parses SPARQL 1.1 JSON results, strips the geo namespace from URIs |
| `questions.py` | 22 reference test questions across 7 categories; reference SPARQL is executed live against GraphDB at test time — no hardcoded expected results |
| `main.py` | Interactive CLI — menu, single-question runner, benchmark mode, free-form mode |
| `data/` | OWL ontology file (`GeoOntology.owl`) |

---

## Test Categories and Questions

| Cat | Name | Q# | What it tests |
|-----|------|----|---------------|
| 1 | Direct Retrieval | Q1–Q3 | Single-hop property reads: form of government, population, head of state |
| 2 | Transitivity | Q4–Q6 | `is_located_in` with OWL2-RL transitive closure (mountains in Asia, peaks in Europe, cities in South America) |
| 3 | Numeric Filter | Q7–Q9 | `FILTER` with `>`, `<`, and combined `&&` conditions on height and population |
| 4 | Defined Class | Q10–Q12 | OWL2-RL materialised classes: `Megacity`, `CapitalCity`; and `FILTER EXISTS` workaround for `SunniIslamicCountry` |
| 5 | Aggregation | Q13–Q16 | `COUNT`, `MAX`, `MIN`, `AVG` with `AS ?alias` |
| 6 | Compositional | Q17–Q19 | `UNION` (mountains or volcanoes), `OPTIONAL` (countries + religion), `MINUS` (capital cities not megacities) |
| 7 | Reasoning Required | Q20–Q22 | `FILTER NOT EXISTS` on transitive location (volcanoes not in Europe); named individual spelling (`North_America`); `FILTER IN` on form of government (republics) |

---

## How Scoring Works

Each run of a question is scored by comparing the LLM result set against the reference result set:

| Label | Meaning |
|-------|---------|
| `EXACT` | LLM result set equals the reference result set exactly |
| `PARTIAL` | Sets overlap but are not equal — shows how many correct values out of how many expected |
| `NONE` | No overlap between LLM results and reference results |
| `EXTRACTION FAILED` | LLM response contained no SPARQL code block |

Benchmark accuracy is reported as the percentage of `EXACT` matches.

---

## Syntax Retry

On an HTTP 400 response from GraphDB (malformed SPARQL), the app automatically asks the LLM to fix the query and retries up to **2 times**. Retries do not trigger on semantic errors (e.g., empty result sets). The total retry count is reported at the end of each benchmark run.

---

## Notes

- Benchmark results vary between runs due to LLM non-determinism. Use benchmark mode with at least 10 runs for reliable accuracy statistics.
- `is_located_in` is transitive — OWL2-RL materialises the full closure, so a query for `geo:is_located_in geo:Asia` correctly returns entities in countries that are themselves in Asia.
- Classes like `EuropeanCountry` and `LandlockedCountry` are defined in the ontology but have **no materialised instances** under OWL2-RL. Always use `geo:is_located_in geo:Europe` for location queries.
- `SunniIslamicCountry` similarly has no materialised instances; queries for it use `FILTER EXISTS { ?c geo:has_main_religion geo:Islam_Sunni }` instead.
