import unittest
import sys
import os

# Root of the project
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, ROOT_DIR)

from advisor_engine import InfinispanDRCAdvisor

class TestEngineSamples(unittest.TestCase):
    def setUp(self):
        self.engine = InfinispanDRCAdvisor()

    def run_sample_test(self, filename):
        """Helper to keep the structure consistent across different files."""
        path = os.path.join(ROOT_DIR, 'test', 'samples', filename)
        
        # 1. Get the sample
        with open(path, 'r') as f:
            content = f.read()

        # 2. Run the engine correctly (Step 3)
        self.engine.load_content(content)
        results = self.engine.analyze()

        # 3. Step 4: Compare/Print the output
        print(f"\n--- Engine Results for {filename} ---")
        print(results)
        
        self.assertIsInstance(results, list)
        return results

    def test_xmx_parsing(self):
        results = self.run_sample_test('xmx.yaml')
        # Here we can add specific assertions for xmx
        # e.g., self.assertTrue(any("Heap" in str(r) for r in results))

    def test_version_parsing(self):
        # Version
        results = self.run_sample_test('version.yaml')

    def test_expose_parsing(self):
        # Expose
        results = self.run_sample_test('expose.yaml')

if __name__ == '__main__':
    unittest.main()