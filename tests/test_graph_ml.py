import unittest

from app.graph_ml import FEATURE_NAMES, graph_ml_report, rank_missing_links, train_link_predictor
from app.load_data import load_graph


class GraphMLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = load_graph()

    def test_heldout_metrics_are_bounded(self):
        _, metrics, _ = train_link_predictor(self.graph)
        self.assertGreater(metrics["heldout_pairs"], 0)
        for key in ("precision", "recall", "f1", "roc_auc"):
            self.assertGreaterEqual(metrics[key], 0.0)
            self.assertLessEqual(metrics[key], 1.0)

    def test_ranked_candidates_are_missing_edges(self):
        rows = rank_missing_links(self.graph, limit=8)
        self.assertTrue(rows)
        for row in rows:
            self.assertFalse(self.graph.g.has_edge(row.source, row.target))
            self.assertGreaterEqual(row.probability, 0.0)
            self.assertLessEqual(row.probability, 1.0)

    def test_features_are_structural_and_label_free(self):
        self.assertNotIn("label", {name.lower() for name in FEATURE_NAMES})
        self.assertIn("two_hop_paths", FEATURE_NAMES)
        self.assertIn("type_pair_prior", FEATURE_NAMES)

    def test_report_keeps_analyst_gate(self):
        report = graph_ml_report(self.graph, limit=5)
        self.assertEqual(len(report["candidate_links"]), 5)
        self.assertIn("never writes", report["decision_boundary"])


if __name__ == "__main__":
    unittest.main()
