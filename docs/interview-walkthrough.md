# Interview Walkthrough

## 60-second answer

"I built a threat-intelligence knowledge graph because cyber intelligence is inherently relational. A vector database can tell me two reports are similar, but it does not naturally answer multi-hop questions like which actor ran a campaign, which malware it used, which ATT&CK techniques were involved, which indicators are associated, and whether those indicators appeared in our own telemetry.

I normalize CTI into typed entities and relationships, preserve confidence and provenance on every edge, retrieve candidate entities from the analyst question, expand only the relevant graph neighborhood, score evidence paths, and pass that compact evidence subgraph to a reasoning layer. This gives better grounding and explainability than putting large threat reports directly into an LLM context window."

## Example investigation question

```text
Which campaigns use token theft and overlap with our finance telemetry?
```

Retrieval:

```text
Question
  |
  +--> T1528 token theft
  |
  +--> Finance campaign
  |
  +--> internal finance observations
```

Graph expansion:

```text
Crimson Harbor
   |
   +--uses--> T1528
   |
   +--associated_with--> 198.51.100.77
                              |
                              +--observed_as-->
                               Finance User Suspicious Sign-in
```

Now the answer can cite a concrete evidence path.

## Why not only RAG?

Traditional document RAG is good at retrieving passages.

The graph is better when:

- relationships matter
- multi-hop reasoning matters
- attribution matters
- temporal context matters
- provenance matters
- analysts need explainability

The strongest system combines both.
