import unittest
import sys
import os
import re
from io import StringIO
from unittest.mock import patch

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, ROOT_DIR)

from advisor_ui import run_ui

class TestUI(unittest.TestCase):

    def strip_ansi(self, text):
        """Removes shell color codes for clean text matching."""
        return re.sub(r'\x1b\[[0-9;]*m', '', text)

    def run_sample_test(self, filename, expected):
        """Helper to run UI and verify summary counts."""
        sample_path = os.path.join(ROOT_DIR, 'test', 'samples', filename)
        captured_output = StringIO()
        
        with patch('sys.stdout', new=captured_output):
            with patch('sys.argv', ['advisor_ui.py', sample_path]):
                run_ui()

        output = self.strip_ansi(captured_output.getvalue())
        
        # Verify the Summary counts from your CLI runs
        self.assertTrue(re.search(fr"Critical Risks:\s+{expected['C']}", output), f"{filename} Critical mismatch")
        self.assertTrue(re.search(fr"Important:\s+{expected['I']}", output), f"{filename} Important mismatch")
        self.assertTrue(re.search(fr"Warnings:\s+{expected['W']}", output), f"{filename} Warnings mismatch")
        self.assertTrue(re.search(fr"General Notes:\s+{expected['N']}", output), f"{filename} Notes mismatch")

    def test_all_samples(self):
        """
        Step 4: Comprehensive comparison of all samples.
        Data mapped directly from your terminal output.
        """
        samples = {
            "xmx.yaml":              {"C": 1, "I": 4, "W": 3, "N": 0},
            "expose.yaml":           {"C": 2, "I": 4, "W": 3, "N": 0},
            "version.yaml":          {"C": 0, "I": 4, "W": 3, "N": 0},
            "infinispan-cache.yaml": {"C": 3, "I": 3, "W": 4, "N": 0},
            "infinispan-full.yaml":  {"C": 2, "I": 2, "W": 2, "N": 1},
        }

        print("\n--- Running Automated UI Validation for all Samples ---")
        for filename, expected in samples.items():
            with self.subTest(sample=filename):
                self.run_sample_test(filename, expected)
                print(f"  [OK] {filename.ljust(22)} (C:{expected['C']} I:{expected['I']} W:{expected['W']} N:{expected['N']})")

if __name__ == '__main__':
    unittest.main()