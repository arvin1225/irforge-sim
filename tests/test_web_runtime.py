"""Keep the CI Node runtime compatible with the pinned package manager."""
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WebRuntimeTests(unittest.TestCase):
    def test_ci_node_supports_pnpm_11(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
        match = re.search(r'node-version:\s*[\"\']([0-9.]+)[\"\']', workflow)
        self.assertIsNotNone(match)
        version = tuple(int(part) for part in match[1].split('.'))
        version += (0,) * (3 - len(version))
        self.assertGreaterEqual(version, (22, 13, 0), 'pnpm 11 requires Node >=22.13')

    def test_package_declares_the_same_runtime_floor(self):
        package = json.loads((ROOT / 'web/package.json').read_text(encoding='utf-8'))
        self.assertEqual(package.get('engines', {}).get('node'), '>=22.13.0')


if __name__ == '__main__':
    unittest.main()
