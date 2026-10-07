import copy,unittest
from tools.annotation_review import ROOT,read,validate,next_state,ReviewError

class AnnotationReviewTests(unittest.TestCase):
    def setUp(self):
        self.packet=read(ROOT/"data/review/examples/disagreement.synthetic.yaml")
        self.annotation=read(ROOT/"data/examples/annotation_ambiguous.yaml")
        self.registry=read(ROOT/"data/sources/registry.yaml")
    def test_blinded_disagreement_and_denominator_report(self):
        errors,report=validate(self.packet,self.annotation,self.registry)
        self.assertEqual([],errors);self.assertEqual(1,report["valid_pair_denominator"]);self.assertEqual(0,report["agreement_pairs"]);self.assertEqual(1,report["disagreement_pairs"])
    def test_adjudication_requires_independent_assigned_expert_and_evidence(self):
        p=copy.deepcopy(self.packet);case=p["cases"][0];case["adjudication"]={"adjudicator_id":"adjudicator-c","outcome":"uncertain","selected_reading_id":None,"rationale":"Alternatives remain unresolved.","evidence_ref":"synthetic:adjudication","decided_at":"2026-10-08T12:30:00Z"};case["state_history"].append({"event_id":"event-4","from_state":"needs_adjudication","to_state":"adjudicated","event_type":"adjudicate","actor_id":"adjudicator-c","evidence_ref":"synthetic:adjudication","occurred_at":"2026-10-08T12:30:00Z"});case["case_state"]="adjudicated"
        self.assertEqual([],validate(p,self.annotation,self.registry)[0])
        p["reviewers"][2]["conflict_of_interest"]=True
        self.assertTrue(any("conflicted or recused adjudicator" in e for e in validate(p,self.annotation,self.registry)[0]))
    def test_duplicate_reviewers_and_unblinded_packet_rejected(self):
        p=copy.deepcopy(self.packet);p["reviewers"].append(copy.deepcopy(p["reviewers"][0]));self.assertTrue(any("duplicate reviewer assignment" in e for e in validate(p,self.annotation,self.registry)[0]))
        p=copy.deepcopy(self.packet);p["blinding"]["peer_decisions_visible"]=True;self.assertTrue(any("cannot expose" in e for e in validate(p,self.annotation,self.registry)[0]))
    def test_missing_evidence_invalid_transition_and_supersede_preservation(self):
        p=copy.deepcopy(self.packet);p["cases"][0]["decisions"][0]["evidence_ref"]="";self.assertTrue(validate(p,self.annotation,self.registry)[0])
        p=copy.deepcopy(self.packet);p["cases"][0]["state_history"][0]["to_state"]="closed";self.assertTrue(any("must transition to assigned" in e for e in validate(p,self.annotation,self.registry)[0]))
        p=copy.deepcopy(self.packet);decisions=p["cases"][0]["decisions"];new=copy.deepcopy(decisions[0]);new.update(decision_id="decision-a-2",outcome="uncertain",selected_reading_id=None,acceptable_reading_ids=["grapheme-reading-a","grapheme-reading-b"],submitted_at="2026-10-08T12:10:00Z",supersedes_decision_id="decision-a-1");decisions.append(new)
        # Preserve and link the old event, and move the state to consensus because the latest opinions now agree.
        p["cases"][0]["state_history"][-1].update(to_state="reviewed",event_type="submit_consensus",occurred_at="2026-10-08T12:11:00Z");p["cases"][0]["case_state"]="reviewed"
        self.assertEqual([],validate(p,self.annotation,self.registry)[0])
        decisions.pop(0);self.assertTrue(any("must exist earlier" in e for e in validate(p,self.annotation,self.registry)[0]))
    def test_exclusions_are_counted_not_silently_dropped(self):
        p=copy.deepcopy(self.packet);p["cases"][0]["issue_flags"]=["damage"]
        errors,report=validate(p,self.annotation,self.registry);self.assertEqual([],errors);self.assertEqual(0,report["valid_pair_denominator"]);self.assertEqual({"excluded_issue:damage":1},report["excluded_case_counts"])
    def test_consensus_requires_two_independent_decisions_and_event_after_review(self):
        p=copy.deepcopy(self.packet)
        case=p["cases"][0]
        case["decisions"]=[]
        case["state_history"][-1]["event_type"]="submit_consensus"
        case["state_history"][-1]["to_state"]="reviewed"
        case["case_state"]="reviewed"
        self.assertTrue(any("requires at least two independent reviewer decisions" in e for e in validate(p,self.annotation,self.registry)[0]))

        p=copy.deepcopy(self.packet)
        p["cases"][0]["state_history"][-1]["occurred_at"]="2026-10-08T11:10:00Z"
        self.assertTrue(any("cannot precede" in e for e in validate(p,self.annotation,self.registry)[0]))

    def test_state_transition_cli_contract_is_deterministic(self):
        self.assertEqual("assigned",next_state("draft","assign_reviewers"))
        with self.assertRaises(ReviewError):next_state("draft","close_case")

if __name__=="__main__":unittest.main()
