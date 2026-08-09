import unittest

from app.load_data import load_graph
from app.retrieval import build_evidence, rank_entities


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.graph = load_graph("data/sample_intel.json")

    def test_token_theft_retrieves_t1528(self):
        results = rank_entities(
            self.graph,
            "Which campaigns use token theft?",
            top_k=8,
        )
        ids = {r["id"] for r in results}
        self.assertIn("tech-t1528", ids)

    def test_query_builds_context(self):
        result = build_evidence(
            self.graph,
            "Which token theft campaigns overlap with finance telemetry?",
            top_k=8,
        )
        self.assertTrue(result.matched_entities)
        self.assertIn("T1528", result.context)
        self.assertTrue(result.evidence_paths)


if __name__ == "__main__":
    unittest.main()
