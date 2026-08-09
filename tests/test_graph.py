import unittest

from app.load_data import load_graph


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.graph = load_graph("data/sample_intel.json")

    def test_stats(self):
        stats = self.graph.stats()
        self.assertGreaterEqual(stats["nodes"], 15)
        self.assertGreaterEqual(stats["edges"], 15)
        self.assertIn("campaign", stats["entity_types"])

    def test_path_to_enterprise_observation(self):
        paths = self.graph.simple_paths(
            "campaign-harbor",
            "obs-finance-signin",
            cutoff=3,
        )
        self.assertTrue(paths)
        self.assertEqual(paths[0].nodes[0], "campaign-harbor")
        self.assertEqual(paths[0].nodes[-1], "obs-finance-signin")


if __name__ == "__main__":
    unittest.main()
