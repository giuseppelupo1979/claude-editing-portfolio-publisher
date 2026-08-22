import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".py", ".mjs", ".sh", ".txt"}
SKIP_PARTS = {".git", "tests", "__pycache__"}


class RepositorySecretScanTest(unittest.TestCase):
    def test_repository_contains_no_embedded_credentials(self):
        findings = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
                continue
            if SKIP_PARTS.intersection(path.relative_to(ROOT).parts):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if re.search(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", text):
                findings.append(f"{path}: contenuto di chiave privata")
            for match in re.finditer(
                r'"(?:password|token|secret|private_key)"\s*:\s*"([^"$<{][^"]*)"',
                text,
                flags=re.IGNORECASE,
            ):
                findings.append(f"{path}: possibile segreto JSON ({match.group(1)[:8]}...)")
            if re.search(r"Authorization:\s*Bearer\s+[A-Za-z0-9._-]{16,}", text, re.IGNORECASE):
                findings.append(f"{path}: bearer token letterale")
        self.assertEqual(findings, [], "\n".join(findings))


if __name__ == "__main__":
    unittest.main()
