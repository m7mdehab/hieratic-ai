from __future__ import annotations

import copy
import contextlib
import io
import shutil
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import yaml

from tools import projectctl


ROOT = Path(__file__).resolve().parents[2]


class ProjectCtlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = yaml.safe_load((ROOT / "PROJECT_STATE.yaml").read_text(encoding="utf-8"))
        self.tasks = yaml.safe_load((ROOT / "TASKS.yaml").read_text(encoding="utf-8"))

    def errors(self, *, state=None, tasks=None) -> list[str]:
        return projectctl.validate_data(
            copy.deepcopy(self.state if state is None else state),
            copy.deepcopy(self.tasks if tasks is None else tasks),
            root=ROOT,
        )

    def test_current_repository_state_passes(self) -> None:
        errors, state, tasks = projectctl.validate_repository(ROOT)
        self.assertEqual([], errors)
        validated_weight = sum(
            (Decimal(str(task["weight"])) for task in tasks["tasks"] if task["status"] == "validated"),
            Decimal("0"),
        )
        self.assertEqual(validated_weight, Decimal(str(state["progress"]["goal_progress"])))
        self.assertEqual(
            validated_weight,
            Decimal(str(tasks["rules"]["progress"]["validated_weighted_tasks_expected"])),
        )

    def test_dependency_cycle_fails(self) -> None:
        tasks = copy.deepcopy(self.tasks)
        tasks["tasks"][0]["depends_on"] = ["CTRL-002"]
        errors = self.errors(tasks=tasks)
        self.assertTrue(any("Dependency cycle" in error for error in errors), errors)

    def test_missing_dependency_fails(self) -> None:
        tasks = copy.deepcopy(self.tasks)
        tasks["tasks"][1]["depends_on"].append("FAKE-999")
        errors = self.errors(tasks=tasks)
        self.assertTrue(any("missing dependency ID FAKE-999" in error for error in errors), errors)

    def test_progress_mismatch_fails(self) -> None:
        state = copy.deepcopy(self.state)
        state["progress"]["goal_progress"] = 3.0
        self.assertTrue(any("does not equal goal_progress" in error for error in self.errors(state=state)))

    def test_phase_task_weight_mismatch_fails(self) -> None:
        tasks = copy.deepcopy(self.tasks)
        tasks["tasks"][6]["weight"] += 0.1
        errors = self.errors(tasks=tasks)
        self.assertTrue(any("task weights total" in error for error in errors), errors)

    def test_ready_task_with_blocked_dependency_fails(self) -> None:
        tasks = copy.deepcopy(self.tasks)
        tasks["tasks"][0]["status"] = "blocked"
        tasks["tasks"][1]["status"] = "active"
        errors = self.errors(tasks=tasks)
        self.assertTrue(any("requires validated dependency CTRL-001" in error for error in errors), errors)

    def test_overseer_context_includes_current_progress_and_coverage(self) -> None:
        packet = projectctl.overseer_context(ROOT, self.state, self.tasks)
        self.assertIn(
            f"Verified goal progress: {self.state['progress']['goal_progress']} / {self.state['progress']['goal_total']}",
            packet,
        )
        self.assertIn(f"Research coverage: {self.state['progress']['research_coverage']}%", packet)

    def test_ctrl_003_context_omits_unrelated_research(self) -> None:
        packet = projectctl.task_context(ROOT, "CTRL-003", self.state, self.tasks)
        self.assertIn("Execution Context Packet - CTRL-003", packet)
        self.assertIn("dashboard/", packet)
        self.assertNotIn("RESEARCH.md", packet)
        self.assertNotIn("source-verified", packet)

    def test_schema_shape_failure_is_reported(self) -> None:
        state = copy.deepcopy(self.state)
        del state["project"]["ultimate_goal"]
        errors = self.errors(state=state)
        self.assertTrue(any("ultimate_goal" in error for error in errors), errors)

    def test_unknown_status_and_ready_state_membership_fail(self) -> None:
        tasks = copy.deepcopy(self.tasks)
        tasks["tasks"][1]["status"] = "working-ish"
        state = copy.deepcopy(self.state)
        state["state"]["ready_tasks"].append("FAKE-999")
        errors = self.errors(state=state, tasks=tasks)
        self.assertTrue(any("unknown status" in error for error in errors), errors)
        self.assertTrue(any("unknown task ID FAKE-999" in error for error in errors), errors)

    def test_duplicate_task_ids_and_incompatible_state_membership_fail(self) -> None:
        tasks = copy.deepcopy(self.tasks)
        tasks["tasks"].append(copy.deepcopy(tasks["tasks"][0]))
        state = copy.deepcopy(self.state)
        duplicate_membership_id = state["state"]["ready_tasks"][0]
        state["state"]["active_tasks"].append(duplicate_membership_id)
        errors = self.errors(state=state, tasks=tasks)
        self.assertTrue(any("duplicate task ID CTRL-001" in error for error in errors), errors)
        self.assertTrue(
            any(f"{duplicate_membership_id} appears in incompatible state arrays" in error for error in errors),
            errors,
        )

    def test_negative_and_nonzero_control_plane_weights_fail(self) -> None:
        tasks = copy.deepcopy(self.tasks)
        tasks["tasks"][0]["weight"] = 1
        tasks["tasks"][1]["weight"] = -1
        errors = self.errors(tasks=tasks)
        self.assertTrue(any("control-plane tasks must have zero" in error for error in errors), errors)
        self.assertTrue(any("negative weight" in error for error in errors), errors)

    def test_p1_to_p8_weight_total_and_expected_rule_mismatch_fail(self) -> None:
        tasks = copy.deepcopy(self.tasks)
        tasks["phases"]["P8_RELEASE"]["weight"] = 6
        tasks["rules"]["progress"]["validated_weighted_tasks_expected"] = 3.5
        errors = self.errors(tasks=tasks)
        self.assertTrue(any("P1-P8 phase weights total" in error for error in errors), errors)
        self.assertTrue(any("does not equal rules.progress.validated_weighted_tasks_expected" in error for error in errors), errors)

    def test_invalid_yaml_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            invalid = Path(temporary) / "invalid.yaml"
            invalid.write_text("state: [unterminated\n", encoding="utf-8")
            with self.assertRaises(projectctl.ProjectCtlError):
                projectctl._load_yaml(invalid)

    def test_context_cli_uses_fixture_copy_without_touching_canonical_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("PROJECT_STATE.yaml", "TASKS.yaml", "START_HERE.md", "AGENTS.md", "OVERSEER_HANDOFF.md", "DECISIONS.md"):
                shutil.copy(ROOT / name, root / name)
            shutil.copytree(ROOT / "tasks", root / "tasks")
            shutil.copytree(ROOT / "schemas", root / "schemas")
            before = (root / "PROJECT_STATE.yaml").read_bytes()
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = projectctl.main(["--root", str(root), "context", "--task", "CTRL-003"])
            self.assertEqual(0, result)
            self.assertIn("CTRL-003", output.getvalue())
            self.assertEqual(before, (root / "PROJECT_STATE.yaml").read_bytes())


if __name__ == "__main__":
    unittest.main()
