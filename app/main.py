from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from .graph_ml import graph_ml_report
from .load_data import load_graph
from .models import QueryRequest
from .retrieval import build_evidence


app = FastAPI(
    title="Threat Intelligence Knowledge Graph",
    version="0.2.0",
    description="Defensive graph-based CTI retrieval, correlation, and analyst-gated graph ML reference implementation.",
)

graph = load_graph()


@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Threat Intelligence Knowledge Graph</title>
  <style>
    body { font-family: ui-sans-serif, system-ui; max-width: 1050px; margin: 38px auto; padding: 0 20px; }
    textarea { width: 100%; min-height: 90px; padding: 10px; }
    button { padding: 10px 16px; margin-top: 8px; cursor:pointer; }
    pre { background:#111; color:#eee; padding:16px; border-radius:8px; overflow:auto; }
  </style>
</head>
<body>
  <h1>Threat Intelligence Knowledge Graph</h1>
  <p>Graph traversal + evidence retrieval + analyst-gated link prediction for cyber threat intelligence.</p>

  <textarea id="q">Which campaigns use token theft and overlap with our finance telemetry?</textarea>
  <br/>
  <button onclick="ask()">Build evidence</button>
  <button onclick="links()">Rank missing links</button>

  <h2>Graph stats</h2>
  <pre id="stats"></pre>

  <h2>Evidence / ML candidates</h2>
  <pre id="result">Run a query or rank missing links.</pre>

<script>
async function loadStats() {
  const r = await fetch('/graph/stats');
  document.getElementById('stats').textContent = JSON.stringify(await r.json(), null, 2);
}
async function ask() {
  const question = document.getElementById('q').value;
  const r = await fetch('/query', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({question, top_k:8})
  });
  document.getElementById('result').textContent = JSON.stringify(await r.json(), null, 2);
}
async function links() {
  const r = await fetch('/ml/link-candidates?limit=10');
  document.getElementById('result').textContent = JSON.stringify(await r.json(), null, 2);
}
loadStats();
</script>
</body>
</html>
"""


@app.get("/graph/stats")
def graph_stats():
    return graph.stats()


@app.get("/entity/{entity_id}")
def entity(entity_id: str):
    result = graph.neighborhood(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="entity not found")
    return result


@app.get("/paths")
def paths(source: str, target: str, cutoff: int = 5):
    return [p.model_dump() for p in graph.simple_paths(source, target, cutoff=min(max(cutoff, 1), 7))]


@app.post("/query")
def query(req: QueryRequest):
    return build_evidence(graph, req.question, req.top_k).model_dump()


@app.get("/ml/link-candidates")
def ml_link_candidates(limit: int = 10):
    return graph_ml_report(graph, limit=min(max(limit, 1), 25))


@app.get("/observations")
def observations():
    results = []
    for entity_id, node in graph.g.nodes(data=True):
        if node.get("type") == "observation":
            results.append(graph.neighborhood(entity_id))
    return results
