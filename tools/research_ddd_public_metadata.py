"""W23 source-original verification of DDD 2026 *research-only* metadata.

No DDD raw photograph/large image archives, no training, no copied editorial
text, and no implicit attribution/rights conversion. Publisher data are original
CC BY-NC-SA; image copyright is per papyri.json item.
"""
from __future__ import annotations
import argparse,collections,hashlib,io,json,re,urllib.parse,urllib.request,zipfile
from pathlib import Path

RECORD="20553713"
BASE=f"https://zenodo.org/records/{RECORD}/files/"
FILES={
 "papyri.json":("4b9fa9f29cdbf080cacfecbf8e77a55f",130000),
 "classes.json":("14ebe82d6624cfb6def19880b3b82376",450000),
 "samples.json":("33c09acf76497a237394919cc55ee645",17000000),
 "DDD_annotations.zip":("c3405016b676cd1a09b9ce989a89ecbb",3500000),
 "Readme - Splits.txt":("2798ef1aa90b85d0fb874ecc0f9078df",24000),
}
USER_AGENT="HieraticAI-W23-original-DDD-license-metadata-verifier/1.0 (https://github.com/m7mdehab/hieratic-ai)"
EXTERNAL_RECORD="https://zenodo.org/records/20553713"
SPLITS=["C-A","C-B","C-C","C-D","D-B","O-A","O-B"]
class PublicSourceError(ValueError):pass

def safe_url(url:str)->bool:
 p=urllib.parse.urlsplit(url)
 return p.scheme=="https" and p.hostname=="zenodo.org" and p.port is None and p.username is None and p.password is None

def fetch_exact(name:str)->tuple[bytes,dict]:
 if name not in FILES:raise PublicSourceError("not allowlisted publisher metadata")
 expected_md5,max_length=FILES[name]
 link=BASE+urllib.parse.quote(name,safe="")+"?download=1"
 if not safe_url(link):raise PublicSourceError("invalid metadata link")
 req=urllib.request.Request(link,headers={"User-Agent":USER_AGENT,"Accept":"application/json,application/zip,text/plain,*/*"})
 with urllib.request.urlopen(req,timeout=65) as response:
  if response.status!=200 or not safe_url(response.geturl()):
   raise PublicSourceError("publisher redirect or HTTP status unexpected")
  data=response.read(max_length+1)
 if not 1<=len(data)<=max_length:raise PublicSourceError("publisher source metadata oversized or empty")
 if hashlib.md5(data).hexdigest()!=expected_md5:
  raise PublicSourceError(f"original publisher MD5 mismatch: {name}")
 return data,{"file":name,"publisher_record":EXTERNAL_RECORD,"original_md5":expected_md5,
     "original_sha256":hashlib.sha256(data).hexdigest(),"original_bytes":len(data)}

def inspect_metadata(source:dict[str,bytes], public_rows:list[dict])->dict:
 papyri=json.loads(source["papyri.json"])
 classes=json.loads(source["classes.json"])
 samples=json.loads(source["samples.json"])
 if not isinstance(papyri,dict) or len(papyri)!=159:
  raise PublicSourceError("publisher papyrus-image universe differs from documented 159")
 if not isinstance(classes,(dict,list)) or not isinstance(samples,(dict,list)):
  raise PublicSourceError("invalid publisher classes/samples source structure")
 ids=set(papyri)
 missing=[k for k,z in papyri.items() if not isinstance(z,dict) or not isinstance(z.get("doc_cluster"),int) or not isinstance(z.get("copyright"),str)]
 if missing:raise PublicSourceError("all original publisher papyri must have document cluster and item-level copyright")
 cluster_counts=collections.Counter(z["doc_cluster"] for z in papyri.values())
 copyrights=collections.Counter(z["copyright"] for z in papyri.values())
 cat1880=[{"id":key,"source_name":row["name"],"document_cluster":row["doc_cluster"],
           "copyright":row["copyright"],"source_document":row.get("TPOP_ref",{}).get("document")}
          for key,row in papyri.items() if re.search(r"C1880",row.get("name",""),re.I)]
 cat1880_groups=sorted(set(x["document_cluster"] for x in cat1880))
 if len(cat1880)<2 or len(cat1880_groups)!=1:
  raise PublicSourceError("Original Cat1880 rotated/view cluster overlap must be retained")
 if len(public_rows)!=266:raise PublicSourceError("approved 266-record public source benchmark snapshot drift")
 public_cat1880=[z.get("id") for z in public_rows
                 if re.search(r"(?<![0-9])1880(?![0-9])",str(z.get("object_name",""))+" "+str(z.get("source_url","")))]
 with zipfile.ZipFile(io.BytesIO(source["DDD_annotations.zip"])) as z:
  infos=z.infolist()
  if len(infos)>900 or sum(x.file_size for x in infos)>120*1024*1024:raise PublicSourceError("unsafe annotation zip archive limit")
  if any(x.filename.startswith("/") or ".." in Path(x.filename).parts for x in infos):
   raise PublicSourceError("invalid zip path")
  labels=[x for x in infos if x.filename.lower().endswith(".json")]
  masks=[x for x in infos if x.filename.lower().endswith((".png",".jpg",".jpeg"))]
  zip_summary={"file_count":len(infos),"json_labelme_file_count":len(labels),
     "masked_or_image_file_count":len(masks),"total_declared_uncompressed_bytes":sum(x.file_size for x in infos)}
 return {
  "source_dataset":"DDD - Diagnostic Deir el-Medina Dataset",
  "doi":"10.5281/zenodo.20553713","publisher_date":"2026-06-26",
  "publisher_images":len(papyri),"publisher_claim_distinct_documents":50,
  "actual_cluster_count":len(cluster_counts),"largest_document_cluster_images":max(cluster_counts.values()),
  "source_classes_length":len(classes),"source_samples_length":len(samples),
  "source_classes_top_level_type":type(classes).__name__,
  "source_samples_top_level_type":type(samples).__name__,
  "publisher_claim_class_categories":504,
  "item_level_copyright_distinct_labels":len(copyrights),
  "item_level_copyright_claims":[{"copyright":k,"images":v} for k,v in sorted(copyrights.items())],
  "cat1880_original_document_images":cat1880,
  "cat1880_same_physical_cluster":cat1880_groups,
  "R017_public_benchmark_metadata_count":len(public_rows),
  "R017_public_literal_cat1880_matches":public_cat1880,
  "annotations_zip_structure":zip_summary,
  "original_image_files_retrieved":0,
  "other_split_zip_files_retrieved":0,
  "source_image_bytes_committed":0,
  "source_original_papyri_metadata_sha256":hashlib.sha256(source["papyri.json"]).hexdigest(),
  "licence_for_dataset_annotations":"CC-BY-NC-SA-4.0_PUBLISHER_CLAIM_NONCOMMERCIAL",
  "image_rights":"SEPARATE_PER_PAPYRUS_COPYRIGHT_ITEM_RIGHTS_REVIEW_REQUIRED",
  "research_track":"SEPARATE_NONCOMMERCIAL_INTERNAL_RESEARCH_ONLY",
  "data008_production_corpus_admission":False,
  "sealed_benchmark_unblinded":False,
  "benchmark_overlap":"UNKNOWN_QUARANTINED",
  "official_published_split_names":SPLITS,
  "publisher_document_disjoint_split_protocols":["C-A","C-B","D-B","O-A","O-B"],
  "publisher_random_sample_splits_not_valid_as_document_holdout":["C-C","C-D"],
  "recommended_first_research_only_closed_set_holdout_split":"C-B",
  "recommended_first_research_only_open_set_holdout_split":"O-B",
  "publisher_split_authority":"https://zenodo.org/records/20553713/files/Readme%20-%20Splits.txt?download=1",
  "expert_gold_status":"PUBLISHER_ANNOTATIONS_NOT_PROJECT_INDEPENDENT_BLIND_ADJUDICATION",
  "hieratic_model_accuracy_claim":False,
  "scientific_capability_points_awarded":0,
 }

def audit(public_file:Path)->dict:
 rows=[json.loads(x) for x in public_file.read_text("utf-8").splitlines() if x.strip()]
 received={};orig=[]
 for name in FILES:
  contents,metadata=fetch_exact(name)
  received[name]=contents
  orig.append(metadata)
 report=inspect_metadata(received,rows)
 report["verified_publisher_files"]=orig
 report["original_publisher_source_count"]=len(orig)
 report["dataset_licensing_source"]=EXTERNAL_RECORD
 return report

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--public",type=Path,default=Path(__file__).resolve().parents[1]/"docs/research/R017_PUBLIC_BENCHMARK_SOURCE_METADATA.jsonl")
 p.add_argument("--output",type=Path)
 args=p.parse_args()
 result=audit(args.public)
 rendered=json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False)+"\n"
 if args.output:args.output.write_text(rendered,encoding="utf-8")
 print(rendered)
if __name__=="__main__":main()
