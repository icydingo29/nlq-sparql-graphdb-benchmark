import requests
import config


def query(sparql: str) -> list:
    """Execute a SPARQL SELECT query and return result rows as list of dicts (var -> value string)."""
    headers = {
        "Accept": "application/sparql-results+json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    resp = requests.post(
        config.GRAPHDB_ENDPOINT,
        data={"query": sparql},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "head" not in data or "results" not in data:
        raise RuntimeError(f"Unexpected GraphDB response: {data}")
    vars_ = data["head"]["vars"]
    rows = []
    for binding in data["results"]["bindings"]:
        row = {}
        for v in vars_:
            if v in binding:
                row[v] = binding[v]["value"]
        rows.append(row)
    return rows


def extract_values(rows: list) -> set:
    """Flatten all row values into a set, stripping the geo namespace from URIs."""
    # NOTE: flattens all SELECT vars into one set, so row-level pairing is not
    # checked. Q18 (?country ?religion) is therefore slightly over-credited: a
    # correct-members / wrong-pairing result can score EXACT. Accepted (1/22).
    ns = config.GEO_NAMESPACE
    result = set()
    for row in rows:
        for val in row.values():
            result.add(val[len(ns):] if val.startswith(ns) else val)
    return result
