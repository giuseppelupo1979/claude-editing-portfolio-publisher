import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "editing-portfolio-publisher"
MANIFEST = SKILL / "references" / "integrita.json"
CHECKER = SKILL / "scripts" / "verifica_integrita.py"
SUFFIXES = {".md", ".py", ".mjs", ".json", ".yaml", ".html"}


def run(skill_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(skill_dir / "scripts" / "verifica_integrita.py")],
        text=True, capture_output=True,
    )


class IntegrityManifestTest(unittest.TestCase):
    def test_manifest_covers_every_skill_file_including_subdirectories(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        declared = {entry["path"] for entry in manifest["file"]}
        on_disk = {
            path.relative_to(SKILL).as_posix()
            for path in SKILL.rglob("*")
            if path.is_file() and path.suffix in SUFFIXES
        } - {"references/integrita.json"}
        self.assertEqual(declared, on_disk)
        self.assertIn("SKILL.md", declared)
        self.assertIn("scripts/lib/publisher-core.mjs", declared)

    def test_pristine_copy_verifies(self):
        result = run(SKILL)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Integrita: OK", result.stdout)

    def test_truncated_file_is_caught_even_though_it_still_exists(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "editing-portfolio-publisher"
            shutil.copytree(SKILL, copy)
            victim = copy / "scripts" / "genera_testi.py"
            victim.write_text("# troncato\n", encoding="utf-8")
            result = run(copy)
            self.assertEqual(result.returncode, 1)
            self.assertIn("genera_testi.py", result.stderr)

    def test_same_size_but_different_content_is_caught(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "editing-portfolio-publisher"
            shutil.copytree(SKILL, copy)
            victim = copy / "references" / "sequenza.md"
            original = victim.read_bytes()
            victim.write_bytes(b"X" + original[1:])
            result = run(copy)
            self.assertEqual(result.returncode, 1)
            self.assertIn("contenuto diverso", result.stderr)

    def test_missing_manifest_is_reported_as_a_stale_installation(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "editing-portfolio-publisher"
            shutil.copytree(SKILL, copy)
            (copy / "references" / "integrita.json").unlink()
            result = run(copy)
            self.assertEqual(result.returncode, 2)
            self.assertIn("reinstallare", result.stderr)

    def test_f0_command_in_skill_md_is_the_one_that_exists(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("python3 scripts/verifica_integrita.py", text)
        self.assertNotIn("ls agents/ scripts/ references/", text)
        self.assertTrue(CHECKER.is_file())


if __name__ == "__main__":
    unittest.main()
