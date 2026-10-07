"""Validate append-only annotation reviews and report transparent agreement."""
from __future__ import annotations
import argparse,hashlib,json,sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any
import yaml
from jsonschema import Draft202012Validator,FormatChecker
from tools.annotation_validation import validate_data as validate_annotation

ROOT=Path(__file__).resolve().parents[1]; SCHEMA=ROOT/"schemas/annotation_review.schema.json"; ANNOTATION_SCHEMA=ROOT/"schemas/annotation.schema.json"; REGISTRY=ROOT/"data/sources/registry.yaml"
TRANSITIONS={"assign_reviewers":("draft","assigned"),"start_review":("assigned","in_review"),"submit_disagreement":("in_review","needs_adjudication"),"submit_consensus":("in_review","reviewed"),"adjudicate":(("needs_adjudication","reviewed"),"adjudicated"),"close_case":("adjudicated","closed")}
class ReviewError(ValueError):pass

def read(path:Path)->Any:
    try:return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,yaml.YAMLError) as exc:raise ReviewError(f"{path}: {exc}") from exc

def _canonical(value:Any)->bytes:return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
def next_state(state:str,event:str)->str:
    if event not in TRANSITIONS:raise ReviewError(f"unknown event: {event}")
    origin,target=TRANSITIONS[event]; origins=(origin,) if isinstance(origin,str) else origin
    if state not in origins:raise ReviewError(f"invalid transition {state} --{event}--> {target}")
    return target

def validate(payload:Any,annotation:Any,registry:Any)->tuple[list[str],dict[str,Any]]:
    schema=read(SCHEMA);errors=[f"{'.'.join(map(str,e.absolute_path)) or '<root>'}: {e.message}" for e in sorted(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(payload),key=lambda e:str(e.absolute_path))]
    if errors:return errors,{}
    errors+=validate_annotation(annotation,read(ANNOTATION_SCHEMA),registry)
    if errors:return errors,{}
    if payload["annotation_id"]!=annotation["annotation_id"]:errors.append("annotation_id does not match DATA-004 annotation")
    blind=payload["blinding"]
    if blind["enabled"] and (blind["predictions_visible"] or blind["peer_decisions_visible"]):errors.append("blinded packet cannot expose predictions or peer decisions")
    reviewers={}; reviewer_ids=set(); groups=set()
    for reviewer in payload["reviewers"]:
        rid=reviewer["reviewer_id"]
        if rid in reviewer_ids:errors.append(f"duplicate reviewer assignment: {rid}")
        reviewer_ids.add(rid);reviewers[rid]=reviewer
        if reviewer["role"]=="reviewer" and reviewer["assignment_status"]!="recused" and not reviewer["conflict_of_interest"]:groups.add(reviewer["independence_group"])
    if len(groups)<2:errors.append("at least two non-conflicted reviewer independence groups are required")
    lines={l["line_id"]:l for l in annotation["lines"]};signs={s["sign_id"]:s for s in annotation["signs"]};tokens={t["token_id"]:t for l in annotation["lines"] for t in l.get("normalized_representation",{}).get("tokens",[])}
    agreement_pairs=agreements=0;excluded=defaultdict(int);case_reports=[];case_ids=set();decision_ids=set();event_ids=set()
    for case in payload["cases"]:
        cid=case["case_id"]
        if cid in case_ids:errors.append(f"duplicate case_id: {cid}")
        case_ids.add(cid)
        target_map={"line":lines,"sign":signs,"token":tokens}[case["target_type"]];target=target_map.get(case["target_id"])
        annotation_layer=None
        if target is None:errors.append(f"{cid}: unknown DATA-004 {case['target_type']} ID {case['target_id']}")
        else:
            if case["target_type"]=="line":
                key=case["annotation_layer"];annotation_layer=target.get(key)
                if key=="normalized_representation" and annotation_layer:annotation_layer=annotation_layer.get("layer")
            elif case["target_type"]=="sign":annotation_layer=target.get("grapheme_identity") if case["annotation_layer"]=="sign_identity" else None
            else:annotation_layer=target.get("value") if case["annotation_layer"]=="token_value" else None
            if annotation_layer is None:errors.append(f"{cid}: annotation_layer does not exist for target type")
            elif annotation_layer["gold_status"]!=case["annotation_gold_status"]:errors.append(f"{cid}: annotation_gold_status disagrees with DATA-004")
        candidate_ids={value["value_id"] for value in (annotation_layer or {}).get("values",[])}
        if "none" in case["issue_flags"] and len(case["issue_flags"])>1:errors.append(f"{cid}: issue flag none cannot be combined with other flags")
        decision_by_id={};latest_by_reviewer={};seen_reviewer=set();previous_time=""
        for decision in case["decisions"]:
            did=decision["decision_id"]
            if did in decision_ids:errors.append(f"duplicate decision_id: {did}")
            decision_ids.add(did);decision_by_id[did]=decision
            rid=decision["reviewer_id"];reviewer=reviewers.get(rid)
            if reviewer is None or reviewer["role"]!="reviewer":errors.append(f"{cid}: decision reviewer is not assigned as reviewer: {rid}")
            elif reviewer["conflict_of_interest"] or reviewer["assignment_status"]=="recused":errors.append(f"{cid}: conflicted or recused reviewer cannot decide: {rid}")
            if decision["evidence_ref"].strip()=="":errors.append(f"{did}: evidence required")
            if decision["selected_reading_id"] is not None and decision["selected_reading_id"] not in candidate_ids:errors.append(f"{did}: selected reading is not a DATA-004 value in {case['annotation_layer']}")
            if not set(decision["acceptable_reading_ids"])<=candidate_ids:errors.append(f"{did}: acceptable readings must reference DATA-004 values in {case['annotation_layer']}")
            if decision["outcome"]=="certain_reading" and decision["selected_reading_id"] is None:errors.append(f"{did}: certain_reading requires a selected reading")
            if decision["outcome"]=="uncertain" and len(decision["acceptable_reading_ids"])<2:errors.append(f"{did}: uncertain outcome requires at least two preserved alternatives")
            supersedes=decision["supersedes_decision_id"]
            if supersedes:
                old=decision_by_id.get(supersedes)
                if old is None:errors.append(f"{did}: superseded decision must exist earlier; prior decisions are preserved")
                elif old["reviewer_id"]!=rid:errors.append(f"{did}: cannot supersede another reviewer's decision")
            elif rid in seen_reviewer:errors.append(f"{cid}: repeated reviewer decision must append with supersedes_decision_id; prior decision cannot be overwritten")
            seen_reviewer.add(rid);latest_by_reviewer[rid]=decision
            if previous_time and decision["submitted_at"]<previous_time:errors.append(f"{cid}: decisions must remain in append order by timestamp")
            previous_time=decision["submitted_at"]
        disagrees=False
        independent=[d for rid,d in latest_by_reviewer.items() if rid in reviewers and not reviewers[rid]["conflict_of_interest"] and reviewers[rid]["assignment_status"]!="recused"]
        independent_groups={reviewers[d["reviewer_id"]]["independence_group"] for d in independent if d["reviewer_id"] in reviewers}
        if len(independent)>=2 and len(independent_groups)<2:errors.append(f"{cid}: reviewer decisions are not independent across groups")
        if len(independent)>=2:
            keys={(d["outcome"],d["selected_reading_id"],tuple(sorted(d["acceptable_reading_ids"]))) for d in independent};disagrees=len(keys)>1
        state="draft"
        for event in case["state_history"]:
            if event["event_id"] in event_ids:errors.append(f"duplicate state event ID: {event['event_id']}")
            event_ids.add(event["event_id"])
            if event["from_state"]!=state:errors.append(f"{cid}: transition history is discontinuous at {event['event_id']}")
            try:expected=next_state(state,event["event_type"])
            except ReviewError as exc:errors.append(f"{cid}: {exc}");continue
            if event["to_state"]!=expected:errors.append(f"{cid}: event {event['event_id']} must transition to {expected}")
            if event["event_type"] in {"submit_disagreement","submit_consensus"}:
                if len(independent)<2 or len(independent_groups)<2:
                    errors.append(f"{cid}: review outcome requires at least two independent reviewer decisions")
                if any(d["submitted_at"]>event["occurred_at"] for d in independent):
                    errors.append(f"{cid}: review outcome cannot precede the recorded reviewer decisions")
            if event["event_type"]=="submit_disagreement" and not disagrees:errors.append(f"{cid}: disagreement transition requires differing independent reviewer decisions")
            if event["event_type"]=="submit_consensus" and disagrees:errors.append(f"{cid}: consensus transition contradicts reviewer decisions")
            if event["event_type"]=="adjudicate":
                adjudication=case["adjudication"]
                if adjudication is None:errors.append(f"{cid}: adjudication event requires an adjudication record")
                elif event["actor_id"]!=adjudication["adjudicator_id"]:errors.append(f"{cid}: adjudication transition actor must match adjudicator record")
                elif adjudication["adjudicator_id"] not in reviewers or reviewers[adjudication["adjudicator_id"]]["role"]!="adjudicator":errors.append(f"{cid}: adjudicator must be assigned an adjudicator role")
                elif reviewers[adjudication["adjudicator_id"]]["conflict_of_interest"] or reviewers[adjudication["adjudicator_id"]]["assignment_status"]=="recused":errors.append(f"{cid}: conflicted or recused adjudicator cannot decide")
                elif any(d["reviewer_id"]==adjudication["adjudicator_id"] for d in case["decisions"]):errors.append(f"{cid}: adjudicator must be independent of original decisions")
                elif reviewers[adjudication["adjudicator_id"]]["independence_group"] in independent_groups:errors.append(f"{cid}: adjudicator independence group overlaps an original reviewer")
            state=expected
        if state!=case["case_state"]:errors.append(f"{cid}: case_state does not match transition history ({state})")
        adjudicated_event=any(event["event_type"]=="adjudicate" for event in case["state_history"])
        if bool(case["adjudication"])!=adjudicated_event:errors.append(f"{cid}: adjudication record and state history must be preserved together")
        if case["adjudication"] and case["adjudication"]["selected_reading_id"] is not None and case["adjudication"]["selected_reading_id"] not in candidate_ids:errors.append(f"{cid}: adjudicated reading is not a DATA-004 value in {case['annotation_layer']}")
        reason=None
        if case["annotation_gold_status"] in {"illegible_unscorable","missing_annotation","adjudication_pending"}:reason=case["annotation_gold_status"]
        elif any(flag in case["issue_flags"] for flag in ("damage","missing_gold","editorial_restoration")):reason="excluded_issue:"+",".join(sorted(set(case["issue_flags"])&{"damage","missing_gold","editorial_restoration"}))
        elif len(independent)<2:reason="fewer_than_two_independent_decisions"
        elif any(d["outcome"] in {"missing_gold","illegible_damaged","editorial_restoration","adjudication_request"} for d in independent):reason="unscorable_or_incomplete_decision"
        if reason:excluded[reason]+=1
        else:
            for left,right in combinations(independent,2):
                agreement_pairs+=1
                l=(left["outcome"],left["selected_reading_id"],tuple(sorted(left["acceptable_reading_ids"])))
                r=(right["outcome"],right["selected_reading_id"],tuple(sorted(right["acceptable_reading_ids"])))
                if l==r:agreements+=1
        case_reports.append({"case_id":cid,"eligible_pair":reason is None,"exclusion_reason":reason,"independent_decision_count":len(independent),"disagreement":disagrees})
    report={"review_set_id":payload["review_set_id"],"cases_total":len(payload["cases"]),"valid_pair_denominator":agreement_pairs,"agreement_pairs":agreements,"disagreement_pairs":agreement_pairs-agreements,"exact_pair_agreement":agreements/agreement_pairs if agreement_pairs else None,"excluded_case_counts":dict(sorted(excluded.items())),"cases":case_reports,"audit_digest":hashlib.sha256(_canonical(payload)).hexdigest()}
    return errors,report

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest="cmd",required=True)
    for cmd in ("validate","report"):
        q=s.add_parser(cmd);q.add_argument("packet",type=Path);q.add_argument("--annotation",type=Path,required=True)
    q=s.add_parser("transition");q.add_argument("--state",required=True);q.add_argument("--event",required=True)
    a=p.parse_args(argv)
    try:
        if a.cmd=="transition":print(f"{a.state} --{a.event}--> {next_state(a.state,a.event)}");return 0
        payload=read(a.packet);annotation=read(a.annotation);errors,report=validate(payload,annotation,read(REGISTRY))
        if errors:raise ReviewError("\n".join(errors))
        if a.cmd=="validate":print(f"PASS: {report['cases_total']} review cases; audit digest {report['audit_digest']}")
        else:print(json.dumps(report,sort_keys=True,indent=2))
        return 0
    except (ReviewError,OSError,KeyError,TypeError,ValueError) as exc:print(f"FAIL: {exc}",file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
