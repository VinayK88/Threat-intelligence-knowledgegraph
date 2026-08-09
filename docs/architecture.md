# Production Architecture

## Reference design

```text
Open CTI / commercial feeds / internal reports
                   |
                   v
            Ingestion adapters
              STIX / TAXII
                   |
                   v
             Normalization
                   |
                   v
            Entity resolution
       aliases / IDs / confidence
                   |
                   v
         Temporal knowledge graph
                   |
         +---------+----------+
         |                    |
         v                    v
 Vector index           Graph queries
         |                    |
         +---------+----------+
                   |
                   v
           Evidence subgraph
                   |
                   v
            LLM / analyst UI
```

## Key design decisions

### Entity resolution

The same actor, malware, or infrastructure can appear under multiple names.

Do not create a new canonical entity for every source string.

Use:

- stable external IDs
- aliases
- normalized indicator values
- similarity scoring
- analyst overrides
- provenance

### Provenance

Every relationship should retain:

- source
- confidence
- first seen
- last seen
- evidence reference
- ingestion timestamp

This allows conflicting intelligence to coexist rather than forcing premature certainty.

### Temporal graph

Threat intelligence changes.

An IP that belonged to one campaign six months ago may be unrelated today.

Edges should support time ranges so queries can ask:

```text
What was true at incident time?
```

### Retrieval

Do not send the entire graph to an LLM.

Retrieve:

1. semantic candidate entities
2. linked graph neighborhood
3. strongest evidence paths
4. relevant observations
5. provenance

Then prune to an evidence subgraph.

### Storage

Possible graph backends:

- Neo4j
- Amazon Neptune
- Azure Cosmos DB Gremlin
- JanusGraph
- PostgreSQL + recursive queries for smaller systems

Vector search can live beside the graph rather than replacing it.
