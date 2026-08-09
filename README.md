# Threat Intelligence Knowledge Graph

> **Connect threat actors, campaigns, malware, ATT&CK techniques, indicators, vulnerabilities, and enterprise observations into one explainable investigation graph.**

This project is a defensive, GitHub-ready reference implementation for graph-based cyber threat intelligence (CTI). It demonstrates how fragmented security intelligence can be normalized into entities and relationships, searched semantically-ish with lightweight retrieval, traversed as evidence paths, and exposed through an analyst-friendly API.

The default demo uses **synthetic CTI data** so it is safe to publish and easy to run locally.

## What problem does this solve?

Threat intelligence commonly arrives as disconnected facts:

```text
IP address
domain
malware family
campaign name
MITRE ATT&CK technique
vulnerability
identity event
endpoint alert
```

A knowledge graph turns those facts into relationships:

```text
Threat Actor
    |
    v
 Campaign
    |
    +---------> Malware
    |             |
    |             v
    |         Technique
    |             |
    v             v
   IOC ------> Observation
                  |
                  v
               Asset
```

That lets an analyst ask:

> "Show me campaigns associated with token theft that overlap with telemetry seen in our environment."

Instead of returning isolated documents, the system returns an **evidence subgraph**.

## Core capabilities

- Typed CTI entities and relationships
- Synthetic threat actors, campaigns, malware, ATT&CK techniques, IOCs, vulnerabilities, and enterprise observations
- Graph traversal and path finding
- Entity-centric neighborhood expansion
- Lightweight text retrieval over node descriptions
- RAG-style evidence bundles
- Confidence-aware relationship scoring
- ATT&CK technique filtering
- Enterprise-observation correlation
- Explainable query results
- FastAPI
- Browser demo
- Unit tests
- Docker support
- Production architecture notes

## Architecture

```text
Threat feeds / reports / ATT&CK / SIEM / EDR
                   |
                   v
            Normalization Layer
                   |
                   v
               Entity Resolver
                   |
                   v
             Knowledge Graph
         +---------+----------+
         |                    |
         v                    v
   Graph Traversal       Text Retrieval
         |                    |
         +---------+----------+
                   |
                   v
             Evidence Builder
                   |
                   v
            Analyst Query API
                   |
                   v
          RAG / LLM reasoning layer
```

## Example question

```text
Which campaigns use token theft techniques and have indicators
that overlap with observations in our environment?
```

Example answer shape:

```json
{
  "query": "token theft campaigns seen internally",
  "entities": [
    "Crimson Harbor",
    "T1528 - Steal Application Access Token",
    "oauth-sync-login.example",
    "finance-user-signin-203"
  ],
  "evidence_paths": [
    [
      "Crimson Harbor",
      "uses",
      "T1528",
      "associated_with",
      "oauth-sync-login.example",
      "observed_as",
      "finance-user-signin-203"
    ]
  ],
  "confidence": 0.86
}
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000
```

API docs:

```text
http://localhost:8000/docs
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

## API

### `GET /graph/stats`

Returns node/edge counts and entity-type distribution.

### `GET /entity/{entity_id}`

Returns one entity plus its immediate neighborhood.

### `GET /paths?source=...&target=...`

Finds explainable relationship paths between two entities.

### `POST /query`

Builds a RAG-style evidence bundle from a natural-language question.

Example:

```json
{
  "question": "Which campaigns use token theft and overlap with our finance telemetry?",
  "top_k": 8
}
```

### `GET /observations`

Returns internal synthetic enterprise observations and correlated CTI.

## Data model

Entity types:

```text
threat_actor
campaign
malware
technique
indicator
vulnerability
asset
observation
sector
country
```

Relationship types:

```text
operates
targets
uses
associated_with
exploits
observed_as
seen_on
related_to
attributed_to
```

Every edge can carry:

- confidence
- source
- first_seen
- last_seen
- notes

## Why a graph?

A vector database is useful for semantic similarity, but CTI questions often require **explicit multi-hop relationships**.

For example:

```text
actor
  -> campaign
  -> malware
  -> technique
  -> indicator
  -> observation
  -> asset
```

A graph preserves those relationships instead of flattening them into text chunks.

## RAG design

This MVP uses a lightweight retriever that ranks nodes by token overlap and then expands the graph around the best matches.

In production:

```text
question
   |
   v
embedding retrieval
   |
   v
entity linking
   |
   v
graph expansion
   |
   v
evidence pruning
   |
   v
LLM answer generation
```

The LLM should receive **evidence paths**, not the entire graph.

That improves:

- explainability
- context efficiency
- grounding
- attribution
- analyst trust

## Production roadmap

- STIX 2.1 ingestion
- TAXII connector
- official ATT&CK ingestion
- OCSF/SIEM observation adapter
- Neo4j / Neptune / Cosmos DB graph adapter
- vector embeddings
- entity resolution and alias clustering
- temporal graph support
- confidence decay
- provenance-aware retrieval
- graph embeddings
- community detection
- campaign clustering
- LLM evidence synthesis
- analyst feedback loop
- graph-based detection features

## Example project pitch

> "I built a threat-intelligence knowledge graph that normalizes CTI entities such as actors, campaigns, malware, ATT&CK techniques, indicators, vulnerabilities, and enterprise observations into a typed graph. Instead of relying only on vector similarity, I retrieve candidate entities, expand their graph neighborhoods, score evidence paths, and give the reasoning layer a compact subgraph. That lets analysts ask multi-hop questions like which campaigns use a particular technique and whether any associated infrastructure has actually appeared in our telemetry."

## Safety

This repository is defensive. It uses synthetic threat intelligence and does not perform exploitation or provide offensive tooling.

See [SECURITY.md](SECURITY.md).

## License

MIT.
