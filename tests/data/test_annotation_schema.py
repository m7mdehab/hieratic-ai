from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import yaml

from tools import annotation_validation


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "data/examples"


class AnnotationSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = json.loads((ROOT / "schemas/annotation.schema.json").read_text(encoding="utf-8"))
        self.registry = yaml.safe_load((ROOT / "data/sources/registry.yaml").read_text(encoding="utf-8"))
        self.minimal = yaml.safe_load((EXAMPLES / "annotation_minimal.yaml").read_text(encoding="utf-8"))
        self.ambiguous = yaml.safe_load((EXAMPLES / "annotation_ambiguous.yaml").read_text(encoding="utf-8"))

    def errors(self, annotation=None, registry=None) -> list[str]:
        return annotation_validation.validate_data(
            copy.deepcopy(self.minimal if annotation is None else annotation),
            self.schema,
            copy.deepcopy(self.registry if registry is None else registry),
        )

    def test_minimal_and_ambiguous_synthetic_fixtures_validate(self) -> None:
        self.assertEqual([], self.errors(self.minimal))
        self.assertEqual([], self.errors(self.ambiguous))

    def test_sequence_only_line_does_not_require_sign_segmentation(self) -> None:
        self.assertEqual([], self.errors(self.minimal))
        self.assertEqual([], self.minimal["signs"])

    def test_duplicate_ids_within_annotation_scope_fail(self) -> None:
        annotation = copy.deepcopy(self.ambiguous)
        annotation["signs"][1]["sign_id"] = annotation["signs"][0]["sign_id"]
        errors = self.errors(annotation)
        self.assertTrue(any("duplicate sign ID" in error for error in errors), errors)

    def test_child_pointing_to_missing_parent_fails(self) -> None:
        annotation = copy.deepcopy(self.ambiguous)
        annotation["pages"][0]["regions"][1]["parent_region_id"] = "missing-parent"
        errors = self.errors(annotation)
        self.assertTrue(any("parent region missing-parent does not exist" in error for error in errors), errors)

    def test_parent_region_cycle_fails_even_when_edges_are_reciprocal(self) -> None:
        annotation = copy.deepcopy(self.ambiguous)
        regions = annotation["pages"][0]["regions"]
        regions[0]["parent_region_id"] = regions[1]["region_id"]
        regions[1]["child_region_ids"] = [regions[0]["region_id"]]
        errors = self.errors(annotation)
        self.assertTrue(any("parent-region cycle detected" in error for error in errors), errors)

    def test_duplicate_page_reading_order_entry_fails_schema(self) -> None:
        annotation = copy.deepcopy(self.ambiguous)
        annotation["pages"][0]["reading_order"] = ["region-2", "region-2"]
        errors = self.errors(annotation)
        self.assertTrue(any("reading_order" in error and "unique" in error for error in errors), errors)

    def test_invalid_coordinate_geometry_fails(self) -> None:
        annotation = copy.deepcopy(self.ambiguous)
        annotation["pages"][0]["regions"][0]["geometry"]["vertices"] = [[0.1, 0.1], [1.1, 0.1]]
        errors = self.errors(annotation)
        self.assertTrue(any("polygon geometry has invalid vertex count" in error for error in errors), errors)
        self.assertTrue(any("normalized coordinates must be within 0..1" in error for error in errors), errors)

    def test_invalid_gold_status_fails_schema(self) -> None:
        annotation = copy.deepcopy(self.minimal)
        annotation["lines"][0]["grapheme_sequence"]["gold_status"] = "certain-ish"
        self.assertTrue(any("gold_status" in error for error in self.errors(annotation)))

    def test_certain_layer_with_unresolved_alternatives_fails(self) -> None:
        annotation = copy.deepcopy(self.minimal)
        annotation["lines"][0]["grapheme_sequence"]["values"].append({
            "value_id": "grapheme-sequence-value-2",
            "value": ["SYNTH-GRAPHEME-C"],
            "confidence": None,
            "equivalent_to_selected": False,
            "evidence_ref": None,
        })
        errors = self.errors(annotation)
        self.assertTrue(any("certain layer has unresolved alternative values" in error for error in errors), errors)

    def test_certain_layer_requires_an_existing_selected_value(self) -> None:
        annotation = copy.deepcopy(self.minimal)
        annotation["lines"][0]["grapheme_sequence"]["selected_value_id"] = None
        errors = self.errors(annotation)
        self.assertTrue(any("certain layer requires a selected value" in error for error in errors), errors)

    def test_certain_equivalent_alternatives_require_selected_anchor(self) -> None:
        annotation = copy.deepcopy(self.minimal)
        layer = annotation["lines"][0]["grapheme_sequence"]
        layer["values"].append({
            "value_id": "grapheme-sequence-equivalent-2",
            "value": ["SYNTH-GRAPHEME-A-ALIAS"],
            "confidence": None,
            "equivalent_to_selected": True,
            "evidence_ref": None,
        })
        layer["selected_value_id"] = None
        errors = self.errors(annotation)
        self.assertTrue(any("certain layer requires a selected value" in error for error in errors), errors)

    def test_certain_equivalent_alternatives_are_representable(self) -> None:
        annotation = copy.deepcopy(self.minimal)
        layer = annotation["lines"][0]["grapheme_sequence"]
        layer["values"].append({
            "value_id": "grapheme-sequence-equivalent-2",
            "value": ["SYNTH-GRAPHEME-A-ALIAS"],
            "confidence": None,
            "equivalent_to_selected": True,
            "evidence_ref": None,
        })
        self.assertEqual([], self.errors(annotation))

    def test_illegible_unscorable_single_certain_value_without_explanation_fails(self) -> None:
        annotation = copy.deepcopy(self.minimal)
        layer = annotation["lines"][0]["grapheme_sequence"]
        layer["gold_status"] = "illegible_unscorable"
        layer["selected_value_id"] = None
        layer["explanation"] = None
        errors = self.errors(annotation)
        self.assertTrue(any("illegible_unscorable requires an explanation" in error for error in errors), errors)

    def test_ligature_constituent_reference_must_exist(self) -> None:
        annotation = copy.deepcopy(self.ambiguous)
        annotation["sign_groups"][0]["constituent_sign_ids"][1] = "missing-sign"
        errors = self.errors(annotation)
        self.assertTrue(any("constituent sign missing-sign does not exist" in error for error in errors), errors)

    def test_normalized_token_must_reference_existing_line_or_sequence(self) -> None:
        annotation = copy.deepcopy(self.ambiguous)
        line = annotation["lines"][0]
        line["normalized_representation"]["tokens"] = [{
            "token_id": "token-1",
            "value": {"gold_status": "certain", "values": [{"value_id": "token-value-1", "value": "SYNTH-TOKEN", "confidence": None, "equivalent_to_selected": False, "evidence_ref": None}], "selected_value_id": "token-value-1", "explanation": None},
            "sequence_ref": "absent-sequence",
            "gold_status": "certain",
            "acceptable_lemmas": [],
            "morphology_bundles": [],
        }]
        errors = self.errors(annotation)
        self.assertTrue(any("sequence_ref absent-sequence does not exist" in error for error in errors), errors)

    def test_normalized_token_cannot_reference_an_unrelated_existing_line(self) -> None:
        annotation = copy.deepcopy(self.ambiguous)
        line = annotation["lines"][0]
        other_line = copy.deepcopy(line)
        other_line["line_id"] = "line-other"
        other_line["sequence_id"] = "sequence-other"
        other_line["reading_order"] = 1
        other_line["region_id"] = None

        def rewrite_ids(value: object) -> None:
            if isinstance(value, dict):
                if "value_id" in value:
                    value["value_id"] = f"other-{value['value_id']}"
                if "token_id" in value:
                    value["token_id"] = f"other-{value['token_id']}"
                if value.get("sequence_ref") in {line["line_id"], line["sequence_id"]}:
                    value["sequence_ref"] = "sequence-other"
                for nested in value.values():
                    rewrite_ids(nested)
            elif isinstance(value, list):
                for nested in value:
                    rewrite_ids(nested)

        rewrite_ids(other_line)
        annotation["lines"].append(other_line)
        line["normalized_representation"]["tokens"] = [{
            "token_id": "token-foreign-sequence",
            "value": {
                "gold_status": "certain",
                "values": [{"value_id": "token-value-foreign-sequence", "value": "SYNTH-TOKEN", "confidence": None, "equivalent_to_selected": False, "evidence_ref": None}],
                "selected_value_id": "token-value-foreign-sequence",
                "explanation": None,
            },
            "sequence_ref": "sequence-other",
            "gold_status": "certain",
            "acceptable_lemmas": [],
            "morphology_bundles": [],
        }]
        errors = self.errors(annotation)
        self.assertTrue(any("sequence_ref sequence-other belongs to a different line" in error for error in errors), errors)

    def test_invalid_reviewer_state_transition_fails(self) -> None:
        annotation = copy.deepcopy(self.minimal)
        review = annotation["reviews"][0]
        review["review_status"] = "adjudicated"
        review["reviewer_id"] = "reviewer-1"
        review["adjudicator_id"] = "adjudicator-1"
        review["status_history"] = [{"from": "draft", "to": "adjudicated", "changed_at": "2026-10-08T11:00:00Z", "actor_id": "adjudicator-1"}]
        errors = self.errors(annotation)
        self.assertTrue(any("invalid status transition draft -> adjudicated" in error for error in errors), errors)

    def test_source_registry_reference_must_exist(self) -> None:
        annotation = copy.deepcopy(self.minimal)
        annotation["provenance"]["source_registry_id"] = "SRC-NOT-IN-REGISTRY"
        errors = self.errors(annotation)
        self.assertTrue(any("does not match DATA-001" in error for error in errors), errors)

    def test_examples_are_synthetic_metadata_only(self) -> None:
        for path in EXAMPLES.glob("annotation_*"):
            self.assertIn(path.suffix.lower(), {".yaml", ".yml"}, path)


if __name__ == "__main__":
    unittest.main()
