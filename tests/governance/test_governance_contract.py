"""FND-006 contract hardening: deterministic synthetic positive/negative tests."""
from __future__ import annotations
import copy
from pathlib import Path
import tempfile
import unittest

from tools import governance_contract as g


class GovernanceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope = g.read_payload(g.SCOPES)
        cls.schema = g.EVIDENCE_SCHEMA
        cls.exp_schema = g.EXPERIMENT_SCHEMA

    def evidence(self):
        return {
            "schema_version": "1.0.0",
            "task_id": "FND-006",
            "branch": "task/FND-006-operational-governance",
            "head_sha": "b" * 40,
            "pull_request": "https://github.com/m7mdehab/hieratic-ai/pull/999",
            "changed_files": ["docs/governance/REPRODUCIBILITY_GATES.md"],
            "commands": [{"command": "python -m unittest", "status": "passed", "summary": "synthetic fixture", "evidence_ref": "artifact:synthetic-ci"}],
            "acceptance": [{"criterion": "Contract schema implemented", "met": True, "evidence_ref": "artifact:synthetic-review"}],
            "artifacts": ["artifact:synthetic-report"],
            "deviations": [],
            "unresolved_risks": [],
            "licensing_provenance": {"third_party_assets_added": False, "rights_review_status": "no_external_assets", "notes": "Only repository-authored synthetic fixtures"},
            "self_awarded_progress": False
        }

    def experiment(self, status="planned"):
        return {
            "schema_version": "1.0.0",
            "id": "EXP-SYNTHETIC-001",
            "task_id": "EVAL-003",
            "status": status,
            "hypothesis": "Synthetic example; does not describe a real model run",
            "code_commit": None, "data_version": None, "split_version": None,
            "model": None, "config": None, "seeds": [], "environment": None,
            "entry_point": None, "metrics": {}, "artifacts": [],
            "result": None, "decision": None, "caveats": [],
            "provenance_review": "pending",
        }

    def test_evidence_valid(self):
        self.assertEqual([], g.validate_evidence(self.evidence()))

    def test_missing_actual_file_list_fails(self):
        item = self.evidence(); item["changed_files"] = []
        self.assertTrue(g.validate_evidence(item))

    def test_scope_outside_approved_write_area_fails(self):
        item = self.evidence(); item["changed_files"].append("PROJECT_STATE.yaml")
        self.assertTrue(any("does not authorize" in e for e in g.validate_evidence(item)))

    def test_unregistered_task_fail_closed(self):
        self.assertTrue(g.check_scope("DATA-999", ["anything.md"], self.scope))

    def test_unsafe_file_path_rejected(self):
        self.assertTrue(g.check_scope("FND-006", ["../PROJECT_STATE.yaml"], self.scope))

    def test_agent_cannot_self_award_progress(self):
        item = self.evidence(); item["self_awarded_progress"] = True
        self.assertTrue(g.validate_evidence(item))

    def test_claimed_criterion_requires_evidence_ref(self):
        item = self.evidence(); item["acceptance"][0]["evidence_ref"] = None
        self.assertTrue(g.validate_evidence(item))

    def test_branch_task_identity_matches(self):
        item = self.evidence(); item["branch"] = "task/EVAL-003-not-governance"
        self.assertTrue(any("does not match" in e for e in g.validate_evidence(item)))

    def test_uncleared_third_party_assets_rejected(self):
        item = self.evidence()
        item["licensing_provenance"]["third_party_assets_added"] = True
        item["licensing_provenance"]["rights_review_status"] = "unresolved"
        self.assertTrue(any("rights review" in e for e in g.validate_evidence(item)))

    def test_evidence_requires_test_execution_report(self):
        item = self.evidence(); item["commands"] = []
        self.assertTrue(g.validate_evidence(item))

    def test_scope_registered_active_lanes(self):
        for task, sample in [
            ("DATA-002","tools/acquisition.py"),("DATA-004","schemas/annotation.schema.json"),
            ("EVAL-004","tools/split_system.py"),("CTRL-003","dashboard/src/app/page.tsx"),
            ("EVAL-003","eval/baselines/baseline_protocol.yaml"),
            ("FND-006","tools/governance_contract.py")
        ]:
            with self.subTest(task=task):
                self.assertEqual([], g.check_scope(task,[sample],self.scope))

    def test_experiment_planned_is_not_pretended_validated(self):
        self.assertEqual([], g.validate_experiment(self.experiment()))

    def test_unjustified_validated_run_fails(self):
        item = self.experiment("validated")
        self.assertTrue(g.validate_experiment(item))

    def test_validated_requires_raw_predictions_and_scores(self):
        item=self.experiment("validated")
        item.update({
            "code_commit": "a" * 40,
            "data_version": "synthetic-v1",
            "split_version": "synthetic-sealed-v1",
            "model": "synthetic",
            "config": {"temperature": 0},
            "seeds": [1],
            "environment": "synthetic",
            "entry_point": "synthetic-command",
            "metrics": {"score": 0},
            "artifacts": [{"uri": "artifact:synthetic-scores", "sha256": "c"*64,"role":"scores"}],
            "result": "synthetic",
            "decision": "do not publish",
            "provenance_review": "approved"
        })
        errors = g.validate_experiment(item)
        self.assertTrue(any("predictions" in e for e in errors))

    def test_validated_synthetic_contract_can_be_satisfied(self):
        item=self.experiment("validated")
        item.update({
            "code_commit": "a" * 40, "data_version": "synthetic-v1",
            "split_version": "synthetic-dev-v1", "model": "synthetic-not-a-run",
            "config": {"temperature": 0}, "seeds": [0],
            "environment": "synthetic", "entry_point": "synthetic-CLI",
            "metrics": {"exact": 0.0},
            "artifacts": [{"uri": "artifact:synthetic-"+role, "sha256": "d"*64, "role": role} for role in ["raw_predictions","scores","config"]],
            "result": "only a contract test", "decision": "no scientific claim",
            "provenance_review": "approved"
        })
        self.assertEqual([], g.validate_experiment(item))

    def test_scope_report_contains_no_git_side_effects(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "evidence.yaml"
            import yaml
            path.write_text(yaml.safe_dump(self.evidence()),encoding="utf-8")
            self.assertEqual(0,g.main(["evidence","--input",str(path)]))


if __name__ == "__main__":
    unittest.main()
