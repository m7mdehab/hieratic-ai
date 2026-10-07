from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


class GovernanceCITests(unittest.TestCase):
    def test_workflow_runs_on_main_prs_and_pushes_with_read_only_permissions(self) -> None:
        workflow_path = ROOT / ".github" / "workflows" / "governance.yml"
        workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)

        self.assertEqual(["main"], workflow["on"]["pull_request"]["branches"])
        self.assertEqual(["main"], workflow["on"]["push"]["branches"])
        self.assertEqual({"contents": "read"}, workflow["permissions"])

        steps = workflow["jobs"]["governance"]["steps"]
        self.assertEqual("actions/checkout@v7", steps[0]["uses"])
        self.assertEqual("actions/setup-python@v7", steps[1]["uses"])
        self.assertEqual("3.12", steps[1]["with"]["python-version"])
        commands = [step.get("run", "") for step in steps]
        self.assertIn("python -m pip install -r requirements-projectctl.txt", commands)
        self.assertIn("python -m tools.projectctl validate", commands)
        self.assertIn("python -m unittest discover -s tests/governance -v", commands)
        self.assertTrue(all("continue-on-error" not in step for step in steps))

    def test_pull_request_template_requests_the_evidence_package(self) -> None:
        template = (ROOT / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
        for required in (
            "Task ID", "Objective", "Branch / commit", "Exact files changed", "Commands and results",
            "Acceptance criteria", "Evidence / artifact links", "Deviations from brief", "Unresolved risks",
            "Licensing / provenance impact", "Benchmark / evaluation impact", "did not self-award progress",
        ):
            with self.subTest(required=required):
                self.assertIn(required, template)

    def test_invalid_fixture_makes_cli_fail_without_changing_canonical_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copy(ROOT / "PROJECT_STATE.yaml", root / "PROJECT_STATE.yaml")
            shutil.copy(ROOT / "TASKS.yaml", root / "TASKS.yaml")
            shutil.copytree(ROOT / "schemas", root / "schemas")

            state_path = root / "PROJECT_STATE.yaml"
            state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
            state["progress"]["goal_progress"] += 1
            state_path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")

            canonical_before = (ROOT / "PROJECT_STATE.yaml").read_bytes()
            result = subprocess.run(
                [sys.executable, "-m", "tools.projectctl", "--root", str(root), "validate"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(1, result.returncode)
            self.assertIn("does not equal goal_progress", result.stderr)
            self.assertEqual(canonical_before, (ROOT / "PROJECT_STATE.yaml").read_bytes())


if __name__ == "__main__":
    unittest.main()
