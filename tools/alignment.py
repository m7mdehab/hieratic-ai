"""Validate DATA-002/DATA-004-linked alignments and compute score eligibility."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from typing import Any
import yaml
from jsonschema import Draft202012Validator,FormatChecker
from tools.annotation_validation import validate_data as validate_annotation
from tools.acquisition import validate_data as validate_acquisition

ROOT=Path(__file__).resolve().parents[1]
ALIGN_SCHEMA=ROOT/"schemas/alignment_manifest.schema.json"
W9_RIME_REFERENCE_SCHEMA=ROOT/"data/alignment/w9_rime/reference_geometry.schema.json"
W9_RIME_REFERENCE_PACKET=ROOT/"data/alignment/w9_rime/CAT1883-CAT2095-recto-reference-geometry.json"
W10_LINE_PAIR_SCHEMA=ROOT/"data/alignment/w10_lawful_line_pair/source_exact_line_pair.schema.json"
W10_LINE_PAIR_PACKET=ROOT/"data/alignment/w10_lawful_line_pair/CAT1883-CAT2095-verso-pleyte-line-2.json"
ACQ_SCHEMA=ROOT/"schemas/acquisition_manifest.schema.json"
ANNOTATION_SCHEMA=ROOT/"schemas/annotation.schema.json"
REGISTRY=ROOT/"data/sources/registry.yaml"
class AlignmentError(ValueError):pass

W10_EXPECTED_IMAGE={
    "source_object_id":"Cat.1883 + Cat.2095",
    "physical_support_group":"Cat.1883 + Cat.2095 (one joined five-fragment support)",
    "view":"verso",
    "figure_number":8,
    "file_url":"https://rivista.museoegizio.it/wp-content/themes/annotum-base/assets/articles/4418/content/8/original.tif",
    "sha256":"506e0b536aa5824bbd18cb0a0b372e057a67e48218a02004ad464ca0958bbeb1",
    "byte_size":41686648,
    "dimensions":[6595,4710],
    "mime_type":"image/tiff",
}
W10_EXPECTED_EDITION={
    "edition_id":"PLEYTE-ROSSI-PAPYRUS-DE-TURIN-1876",
    "witness_source_object_id":"Cat.1883 + Cat.2095",
    "citation":"W. Pleyte and F. Rossi, Papyrus de Turin, vol. 1, printed p. 41, numbered item 2; vol. 2, Plate XXIX (1869–1876)",
    "printed_page":41,
    "numbered_item":2,
    "plate":"XXIX",
}

def validate_w10_line_pair(packet:Any,schema_path:Path=W10_LINE_PAIR_SCHEMA)->list[str]:
    """Validate a rights-cleared but unreviewed image-to-edition line-reference pilot.

    This intentionally does not produce a DATA-004 alignment or gold label. The
    fixed identities below bind the research packet to the exact W10 evidence;
    a YAML/JSON claim cannot change the source or review authority.
    """
    errors=schema_errors(packet,schema_path)
    if errors:return errors
    source=packet["source"]
    image=source["image"]
    for key,value in W10_EXPECTED_IMAGE.items():
        observed=source.get(key) if key in {"source_object_id","physical_support_group","view","figure_number"} else image.get(key)
        if observed!=value:errors.append(f"W10 source identity mismatch for {key}")
    if image.get("license_id")!="CC-BY-2.0" or image.get("license_evidence_status")!="verified":
        errors.append("W10 image reuse rights must remain explicitly verified for the exact figure")
    if image.get("coordinate_asset_sha256")!=image.get("sha256"):
        errors.append("W10 coordinates must bind to the exact source TIFF bytes; derivative/hash mismatch")
    edition=packet["edition"]
    for key,value in W10_EXPECTED_EDITION.items():
        if edition.get(key)!=value:errors.append(f"W10 edition/source line identity mismatch for {key}")
    if edition.get("license_id")!="PDM-1.0" or edition.get("license_evidence_status")!="verified":
        errors.append("W10 edition text rights must remain verified as public-domain source material")
    if edition.get("line_text_embedded") is not False:
        errors.append("W10 public packet must not embed the edition's line text")
    if edition.get("witness_source_object_id")!=source.get("source_object_id"):
        errors.append("W10 cross-collection/source witness collision")
    pair=packet["line_pair_candidate"]
    if pair.get("edition_line_locator")!="vol. 1, printed p. 41, numbered item 2; vol. 2, Plate XXIX":
        errors.append("W10 line locator is not supported by the cited edition evidence")
    geometry=pair["geometry"]
    x0,y0,x1,y1=geometry["bounds"]
    width,height=image["dimensions"]
    if x0<0 or y0<0 or x1<=x0 or y1<=y0 or x1>width or y1>height:
        errors.append("W10 candidate line geometry is empty or outside exact source image")
    if geometry.get("coordinate_asset_sha256")!=image.get("sha256"):
        errors.append("W10 candidate line coordinates reference a different image/derivative")
    if pair.get("mapping_state")!="proposed_unreviewed_candidate":
        errors.append("W10 line correspondence is a candidate and cannot be self-marked verified")
    if pair.get("review_state")!="unreviewed" or pair.get("reviewer_id") is not None:
        errors.append("W10 line correspondence requires an independent human review")
    if pair.get("gold_scoreable") is not False or packet.get("gold_eligible") is not False:
        errors.append("W10 source investigation cannot promote this candidate to gold")
    if pair.get("line_text_embedded") is not False:
        errors.append("W10 line text must remain a bibliographic pointer only")
    if packet.get("data004_annotation_id") is not None:
        errors.append("W10 investigation has no DATA-004 annotation identity")
    if packet.get("benchmark_overlap")!="unresolved_quarantined" or packet.get("training_admission")!="blocked":
        errors.append("W10 benchmark/source admission remains blocked pending independent review")
    return errors

def validate_reference_geometry(packet:Any,schema_path:Path=W9_RIME_REFERENCE_SCHEMA)->list[str]:
    """Validate image-linked bibliographic pointers that are expressly not DATA-006 gold alignments."""
    errors=schema_errors(packet,schema_path)
    if errors:return errors
    regions=packet["geometry_regions"]
    ids=[region["region_id"] for region in regions]
    if len(ids)!=len(set(ids)):errors.append("duplicate reference geometry region_id")
    for region in regions:
        x0,y0,x1,y1=region["source_bounds"]
        if x1<=x0 or y1<=y0:errors.append(f"{region['region_id']}: empty or reversed source bounds")
    if packet.get("line_level_alignment") is not False or packet.get("data004_annotation_id") is not None:
        errors.append("reference-only geometry cannot claim DATA-004 line alignment")
    return errors

def read(path:Path)->Any:
    try:
        raw=path.read_text(encoding="utf-8")
        return json.loads(raw) if path.suffix.lower()==".json" else yaml.safe_load(raw)
    except (OSError,UnicodeError,yaml.YAMLError,json.JSONDecodeError) as exc:raise AlignmentError(f"{path}: {exc}") from exc

def schema_errors(data:Any,path:Path)->list[str]:
    return [f"{'.'.join(map(str,e.absolute_path)) or '<root>'}: {e.message}" for e in sorted(Draft202012Validator(read(path),format_checker=FormatChecker()).iter_errors(data),key=lambda e:str(e.absolute_path))]

def validate(alignment:Any,acquisition:Any,annotation:Any,registry:Any)->tuple[list[str],dict[str,bool]]:
    errors=schema_errors(alignment,ALIGN_SCHEMA)
    if errors:return errors,{}
    errors += schema_errors(acquisition,ACQ_SCHEMA)
    errors += validate_annotation(annotation,read(ANNOTATION_SCHEMA),registry)
    if errors:return errors,{}
    if alignment["acquisition_manifest_id"]!=acquisition["manifest_id"]:errors.append("acquisition_manifest_id does not match DATA-002 manifest")
    if alignment["annotation_id"]!=annotation["annotation_id"]:errors.append("annotation_id does not match DATA-004 annotation")
    item=next((x for x in acquisition["items"] if x["source_object_id"]==alignment["acquisition_item_source_object_id"]),None)
    if item is None:errors.append("acquisition item source_object_id not found")
    if item:
        if item["source_id"]!=annotation["provenance"]["source_registry_id"]:errors.append("acquisition and annotation source_id differ")
        synthetic=item["is_synthetic_fixture"]
        source_map={x["source_id"]:x for x in registry["sources"]}; source=source_map.get(item["source_id"])
        if source is None:errors.append(f"unknown DATA-001 source_id: {item['source_id']}")
        elif source.get("benchmark_quarantine") or source["source_id"]=="SRC-HIERATICBENCH":errors.append("benchmark-contaminated source is excluded from alignment gold scoring")
        if item["benchmark_quarantine"]:errors.append("benchmark-quarantined acquisition item is excluded")
        if not synthetic:
            acquisition_errors,_=validate_acquisition(acquisition,registry,read(ACQ_SCHEMA))
            errors.extend(f"DATA-002 manifest policy: {e}" for e in acquisition_errors)
            use=item["intended_use"]
            if item["acquisition_status"]!="complete" or item["source_rights_snapshot"]["use_decision"]!="allowed":errors.append("real acquisition input must be complete with an allowed DATA-002 use decision")
            if source and (use not in {"training","development"} or source.get(f"{use}_use")!="allowed"):
                errors.append("real alignment input must have an allowed DATA-001 training/development decision")
    page_map={p["page_id"]:p for p in annotation["pages"]}
    regions={r["region_id"]:(p,r) for p in annotation["pages"] for r in p["regions"]}
    lines={l["line_id"]:l for l in annotation["lines"]}
    signs={s["sign_id"]:s for s in annotation["signs"]}
    tokens={t["token_id"]:(line,t) for line in annotation["lines"] for t in line.get("normalized_representation",{}).get("tokens",[])}
    align_by_id={}; dependencies={}; resolved_region_targets={}; eligible={}; covered_regions=set()
    for entry in alignment["alignments"]:
        aid=entry["alignment_id"]
        if aid in align_by_id:errors.append(f"duplicate alignment_id: {aid}")
        align_by_id[aid]=entry;dependencies[aid]=entry["depends_on_alignment_ids"]
        page=page_map.get(entry["page_id"])
        if page is None:errors.append(f"{aid}: unknown page_id {entry['page_id']}")
        region_order=[]
        for rid in entry["region_ids"]:
            covered_regions.add(rid)
            found=regions.get(rid)
            if found is None:errors.append(f"{aid}: broken region reference {rid}");continue
            rpage,region=found
            if rpage["page_id"]!=entry["page_id"]:errors.append(f"{aid}: region {rid} belongs to a different page")
            elif page:region_order.append(page["reading_order"].index(rid) if rid in page["reading_order"] else -1)
        if region_order!=sorted(region_order):errors.append(f"{aid}: region list contradicts page reading order")
        target_orders=[]
        seen_targets=set()
        for target in entry["targets"]:
            typ,tid=target["target_type"],target["target_id"]
            if (typ,tid) in seen_targets:errors.append(f"{aid}: duplicate target reference {typ}:{tid}")
            seen_targets.add((typ,tid))
            if typ=="line":
                obj=lines.get(tid)
                if obj is None:errors.append(f"{aid}: unknown DATA-004 line_id {tid}")
                elif obj["page_id"]!=entry["page_id"]:errors.append(f"{aid}: target line {tid} belongs to another page")
                else:target_orders.append(obj["reading_order"])
            elif typ=="sign":
                obj=signs.get(tid)
                if obj is None:errors.append(f"{aid}: unknown DATA-004 sign_id {tid}")
                elif obj["line_id"] not in lines or lines[obj["line_id"]]["page_id"]!=entry["page_id"]:errors.append(f"{aid}: sign {tid} is not on declared page")
                else:target_orders.append(lines[obj["line_id"]]["reading_order"])
            elif typ=="token":
                obj=tokens.get(tid)
                if obj is None:errors.append(f"{aid}: unknown DATA-004 token_id {tid}")
                elif obj[0]["page_id"]!=entry["page_id"]:errors.append(f"{aid}: token {tid} is not on declared page")
                else:target_orders.append(obj[0]["reading_order"])
        if target_orders!=sorted(target_orders):errors.append(f"{aid}: target list contradicts DATA-004 reading order")
        nr,nt=len(entry["region_ids"]),len(entry["targets"])
        expected={"one_to_one":nr==1 and nt==1,"one_to_many":nr==1 and nt>=2,"many_to_one":nr>=2 and nt==1,"ligature":nr>=1 and nt>=1,"omission":nr>=1 and nt==0,"gap":nt==0,"damage":nr>=1 and nt==0,"editorial_restoration":nt>=1,"unresolved":True}[entry["relation"]]
        if not expected:errors.append(f"{aid}: region/target cardinality contradicts relation {entry['relation']}")
        for hypothesis in entry["hypotheses"]:
            hyp_seen=set()
            for target in hypothesis["targets"]:
                typ,tid=target["target_type"],target["target_id"]
                if (typ,tid) in hyp_seen:errors.append(f"{aid}/{hypothesis['hypothesis_id']}: duplicate hypothesis target {typ}:{tid}")
                hyp_seen.add((typ,tid))
                pool={"line":lines,"sign":signs,"token":tokens}[typ]
                if tid not in pool:errors.append(f"{aid}/{hypothesis['hypothesis_id']}: broken DATA-004 hypothesis reference {typ}:{tid}")
                elif typ=="line" and pool[tid]["page_id"]!=entry["page_id"]:errors.append(f"{aid}/{hypothesis['hypothesis_id']}: hypothesis line is on another page")
                elif typ=="sign" and (pool[tid]["line_id"] not in lines or lines[pool[tid]["line_id"]]["page_id"]!=entry["page_id"]):errors.append(f"{aid}/{hypothesis['hypothesis_id']}: hypothesis sign is on another page")
                elif typ=="token" and tokens[tid][0]["page_id"]!=entry["page_id"]:errors.append(f"{aid}/{hypothesis['hypothesis_id']}: hypothesis token is on another page")
        if not entry["targets"] and entry["relation"] not in {"omission","gap","damage","unresolved"}:errors.append(f"{aid}: empty target requires omission/gap/damage/unresolved relation")
        if entry["relation"] in {"omission","gap","damage"} and entry["targets"]:errors.append(f"{aid}: {entry['relation']} alignment must not invent a reading target")
        target_key=tuple((t["target_type"],t["target_id"]) for t in entry["targets"])
        for rid in entry["region_ids"]:
            previous=resolved_region_targets.get(rid)
            if entry["status"]=="resolved":
                if previous is not None and previous!=target_key:
                    errors.append(f"{aid}: contradictory resolved mapping for region {rid}")
                else:
                    resolved_region_targets[rid]=target_key
        targets_certain=True
        for target in entry["targets"]:
            if target["target_type"]=="line":
                line=lines.get(target["target_id"])
                targets_certain &= bool(line and line["grapheme_sequence"]["gold_status"]=="certain")
            elif target["target_type"]=="sign":
                sign=signs.get(target["target_id"])
                targets_certain &= bool(sign and sign["grapheme_identity"]["gold_status"]=="certain")
            else:
                token=tokens.get(target["target_id"])
                targets_certain &= bool(token and token[1]["gold_status"]=="certain" and token[1]["value"]["gold_status"]=="certain")
        eligible[aid]=(not item or not item["is_synthetic_fixture"]) and (not errors) and (entry["status"]=="resolved" and entry["review_state"] in {"reviewed","adjudicated"} and bool(entry["reviewer_id"]) and entry["confidence"] is not None and bool(entry["provenance_ref"].strip()) and bool(entry["targets"]) and targets_certain and not entry["hypotheses"] and entry["relation"] in {"one_to_one","one_to_many","many_to_one","ligature"})
    missing_regions=sorted(set(regions)-covered_regions)
    if missing_regions:errors.append(f"unmatched DATA-004 regions require explicit alignment/exclusion: {', '.join(missing_regions)}")
    for aid,deps in dependencies.items():
        for dep in deps:
            if dep not in align_by_id:errors.append(f"{aid}: missing alignment dependency {dep}")
    visiting=set();visited=set()
    def visit(aid):
        if aid in visiting:errors.append(f"alignment dependency cycle includes {aid}");return
        if aid in visited:return
        visiting.add(aid)
        for dep in dependencies[aid]:
            if dep in dependencies:visit(dep)
        visiting.remove(aid);visited.add(aid)
    for aid in dependencies:visit(aid)
    return errors,eligible

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest="cmd",required=True)
    q=s.add_parser("validate");q.add_argument("manifest",type=Path);q.add_argument("--acquisition",type=Path,required=True);q.add_argument("--annotation",type=Path,required=True);q.add_argument("--output",type=Path)
    ref=s.add_parser("validate-reference",help="validate image-linked citation pointers with geometry only; never DATA-006 gold")
    ref.add_argument("manifest",type=Path,nargs="?",default=W9_RIME_REFERENCE_PACKET);ref.add_argument("--schema",type=Path,default=W9_RIME_REFERENCE_SCHEMA)
    w10=s.add_parser("validate-w10-pair",help="validate the W10 lawful image/edition locator candidate; never gold")
    w10.add_argument("manifest",type=Path,nargs="?",default=W10_LINE_PAIR_PACKET);w10.add_argument("--schema",type=Path,default=W10_LINE_PAIR_SCHEMA)
    a=p.parse_args(argv)
    try:
        if a.cmd=="validate-reference":
            packet=read(a.manifest);errors=validate_reference_geometry(packet,a.schema)
            if errors:raise AlignmentError("\n".join(errors))
            print(json.dumps({"reference_set_id":packet["reference_set_id"],"geometry_region_count":len(packet["geometry_regions"]),"line_level_alignment":False,"gold_scoreable_count":0,"training_admission":packet["rights_boundary"]["training_admission"]},sort_keys=True))
            return 0
        if a.cmd=="validate-w10-pair":
            packet=read(a.manifest);errors=validate_w10_line_pair(packet,a.schema)
            if errors:raise AlignmentError("\n".join(errors))
            pair=packet["line_pair_candidate"]
            print(json.dumps({"investigation_id":packet["investigation_id"],"source_sha256":packet["source"]["image"]["sha256"],"edition_line_locator":pair["edition_line_locator"],"geometry":pair["geometry"]["bounds"],"mapping_state":pair["mapping_state"],"review_state":pair["review_state"],"gold_scoreable":False,"training_admission":"blocked","result":"PASS: lawful source pointers and candidate geometry validated; no line match or gold asserted"},sort_keys=True,indent=2))
            return 0
        alignment=read(a.manifest);acq=read(a.acquisition);ann=read(a.annotation);registry=read(REGISTRY)
        errors,eligible=validate(alignment,acq,ann,registry)
        if errors:raise AlignmentError("\n".join(errors))
        result={"alignment_set_id":alignment["alignment_set_id"],"gold_scoring_eligibility":eligible,"eligible_count":sum(eligible.values()),"alignment_count":len(eligible),"generator":"hieratic-alignment/1.0.0"}
        encoded=json.dumps(result,sort_keys=True,indent=2)+"\n"
        if a.output:a.output.write_text(encoded,encoding="utf-8")
        print("PASS: alignment references and ordering valid; benchmark exclusion checked")
        print(encoded,end="");return 0
    except (AlignmentError,OSError,KeyError,TypeError,ValueError) as exc:print(f"REFUSED: {exc}",file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
