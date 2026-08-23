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

class FrontmatterTest(unittest.TestCase):
    """Il frontmatter deve stare nei limiti che l'installazione impone.

    La description ha superato i 1024 caratteri una volta, e il fallimento non
    arriva in fase di build: arriva quando l'utente clicca su salva, cioe' il
    momento peggiore per scoprirlo.
    """

    def frontmatter(self) -> dict[str, str]:
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"), "SKILL.md deve aprire con il frontmatter")
        block = text.split("---\n", 2)[1]
        campi = {}
        for line in block.splitlines():
            if ": " in line and not line.startswith((" ", "\t")):
                key, value = line.split(": ", 1)
                campi[key.strip()] = value.strip()
        return campi

    def test_description_stays_within_the_installation_limit(self):
        description = self.frontmatter()["description"]
        self.assertLessEqual(len(description), 1024, "troppi caratteri")
        self.assertLessEqual(len(description.encode("utf-8")), 1024, "troppi byte")

    def test_name_is_a_valid_skill_identifier(self):
        name = self.frontmatter()["name"]
        self.assertEqual(name, "editing-portfolio-publisher")
        self.assertLessEqual(len(name), 64)
        self.assertRegex(name, r"^[a-z0-9][a-z0-9-]*$")

    def test_description_keeps_the_trigger_words_that_had_been_lost(self):
        description = self.frontmatter()["description"]
        for parola in ("menabò", "dummy", "quali foto tenere o scartare",
                       "cosa hanno in comune", "più di due", "gallerie",
                       "concorso", "proprio sito", "critica-fotografica"):
            self.assertIn(parola, description, f"parola gancio persa: {parola}")


class SkillDocumentTest(unittest.TestCase):
    def test_f0_command_in_skill_md_is_the_one_that_exists(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("python3 scripts/verifica_integrita.py", text)
        self.assertNotIn("ls agents/ scripts/ references/", text)
        self.assertTrue(CHECKER.is_file())


if __name__ == "__main__":
    unittest.main()
