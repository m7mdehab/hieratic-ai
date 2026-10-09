"""W20 original photo / historical edition, offline public-metadata audit only.
No sealed benchmark, no original image download, no modern TPOP transcript."""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[1]
MATRIX=ROOT/"docs/research/R025_CC0_PHOTO_EDITION_MATRIX.json"
PUBLIC=ROOT/"docs/research/R017_PUBLIC_BENCHMARK_SOURCE_METADATA.jsonl"
ALIASES=(r"(?<!\d)1880(?!\d)",r"(?<!\d)6759(?!\d)",r"(?<!\d)2169(?!\d)")
def audit(meta,public):
    if (meta["classification"]!="DOCUMENT_LEVEL_HISTORICAL_EDITION_CANDIDATE_NOT_REVIEWED_LINE_GOLD" or
        meta["original_photos_acquired"]!=0 or meta["exact_photo_to_written_line_pairs"]!=0 or
        meta["independent_expert_reviewed_pairs"]!=0 or meta["training_admission"] is not False or
        meta["benchmark_status"]!="UNRESOLVED_QUARANTINED"):
        raise ValueError("Unapproved material/gold/capability promotion")
    if len(public)!=266:raise ValueError("Public 266-row R017 source census revision drift")
    objs=meta["source_objects"]
    if len(objs)!=3 or len({o["support_id"] for o in objs})!=3:
        raise ValueError("Physical witness groups invalid")
    ed=meta["historical_edition"]
    if (ed["cat1880_printed_text_pages"]!=[50,65] or len(ed["cat1880_plates"])!=14 or
        ed["photo_to_specific_plate_region"]!="UNRESOLVED_NO_VISUAL_INSPECTION" or
        ed["original_pdf_bytes_acquired"] is not False):
        raise ValueError("Publication locator/side or exact-geometry assertion changed")
    hits=[];related=[]
    for rec in public:
        fields=" ".join(str(rec.get(k) or "") for k in ("object_name","source_url","source_file_url"))
        # Numeric token boundaries matter: AKU sign /67591 is NOT Suppl.6759.
        matched=[pat for pat in ALIASES if re.search(pat,fields)]
        if matched:hits.append({"id":rec["id"],"name":rec.get("object_name"),"aliases":matched})
        if re.search(r"Turin|Torino|Museo Egizio",fields,re.I):
            related.append({"id":rec["id"],"name":rec.get("object_name")})
    urls=[]
    for o in objs:
        for file in o["files"]:
            if (file["original_media_SHA256"] is not None or
                file["original_bytes_acquired"] is not False or
                not file["commons_file_page"].startswith("https://commons.wikimedia.org/wiki/File:")):
                raise ValueError("Public file metadata cannot be represented as acquired original pixels")
            urls.append({"physical_support":o["support_id"],"url":file["commons_file_page"],
                         "source_bytes":"NOT_ACQUIRED","face_alignment":"UNRESOLVED"})
    if len(urls)!=7:raise ValueError("Expected seven source photo file candidates, not seven documents")
    if any(o["type"].startswith("CRAFTSMEN") and o["exact_face_and_line_alignment"]!="NOT_APPLICABLE_STANDARD_HIERATIC_LINE" for o in objs):
        raise ValueError("Identity marks wrongly promoted to translatable lines")
    return {"status":"DOCUMENT_LEVEL_PHOTO_PUBLIC_DOMAIN_EDITION_ROUTE_VERIFIED_NO_LINE_GOLD",
        "public_benchmark_metadata_records_checked":len(public),
        "exact_public_accession_alias_matches":hits,"exact_match_count":len(hits),
        "Turin_institution_family_matches":related,"institution_family_count":len(related),
        "original_physical_supports":len(objs),"public_photo_pages_cited":len(urls),
        "historical_cat1880_text_pages":[50,65],"historical_cat1880_plate_count":14,
        "original_photo_bytes_acquired":0,"certified_physical_image_to_line_pairs":0,
        "benchmark_nonoverlap_certified":False,"production_admission":False,"media":urls}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--matrix",type=Path,default=MATRIX)
    p.add_argument("--benchmark",type=Path,default=PUBLIC)
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    meta=json.loads(args.matrix.read_text(encoding="utf-8"))
    rows=[json.loads(line) for line in args.benchmark.read_text(encoding="utf-8").splitlines() if line.strip()]
    report=audit(meta,rows)
    s=json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+"\n"
    if args.output:args.output.write_text(s,encoding="utf-8")
    print(s)
if __name__=="__main__":main()
