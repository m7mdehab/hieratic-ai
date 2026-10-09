"""W24: original DDD publication's real annotations, grouped-only metadata baseline.

Public publisher metadata are CC BY-NC-SA; never emit label-bearing rows,
licensed image bytes, or test answers. No image models and no accuracy claim.
"""
from __future__ import annotations
import argparse,collections,hashlib,json
from pathlib import Path
from tools.research_ddd_public_metadata import fetch_exact,PublicSourceError

def structural_probe(papyri,samples,classes):
    if len(papyri)!=159 or len(samples)!=17885 or len(classes)!=504:
        raise PublicSourceError("DDD publisher universe drift")
    keys=sorted(samples,key=str)
    first=samples[keys[0]]
    cls=next(iter(classes.values()))
    img=next(iter(papyri.values()))
    def shape(value):
        if not isinstance(value,dict):return {"type":type(value).__name__}
        return {"type":"dict","fields":sorted(value),
          "field_values_probe":{k:(str(v)[:75] if not isinstance(v,(dict,list)) else
              (f"{type(v).__name__}(keys={sorted(v)[:10]})" if isinstance(v,dict)
               else f"list(len={len(v)})"))
           for k,v in value.items()}}
    return {"schema":"w24-ddd-annotation-structure-probe/1.0",
     "samples_count":len(samples),"classes_count":len(classes),
     "images_count":len(papyri),
     "sample_structure":shape(first),
     "class_structure":shape(cls),
     "papyrus_structure_fields":sorted(img),
     "research_only":True,"no_training":True,
     "source_rights":"CC_BY_NC_SA_4_0_AND_PER_IMAGE"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path)
    args=ap.parse_args()
    original={}
    for name in ("papyri.json","samples.json","classes.json"):
        raw,manifest=fetch_exact(name)
        original[name]=(json.loads(raw),manifest)
    p=original["papyri.json"][0]
    s=original["samples.json"][0]
    c=original["classes.json"][0]
    report=structural_probe(p,s,c)
    report["source_sha256"]={name:value[1]["original_sha256"] for name,value in original.items()}
    result=json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n"
    if args.output:args.output.write_text(result,encoding="utf8")
    print(result)
if __name__=="__main__":main()
