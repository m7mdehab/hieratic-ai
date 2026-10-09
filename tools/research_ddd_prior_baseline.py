"""W24 verified publisher annotation-only empirical baseline and physical witness holdout.

DDD Zenodo 20553713 exact MD5/SHA256 source. Real 17,885 published
labels over 50 source document clusters. NONVISUAL LABEL-PRIOR NEGATIVE
CONTROL ONLY. Never input gold labels, images or metadata into visual
test-time model. Does not imply genuine palaeographic recognition.
"""
from __future__ import annotations
import argparse,collections,hashlib,json
from pathlib import Path
from tools.research_ddd_public_metadata import fetch_exact,PublicSourceError

SEED="R029-fixed-original-DDD-doc-groups-v1"
EXPECTED_PAPYRI=159
EXPECTED_SAMPLES=17885
EXPECTED_CLASSES=504
EXPECTED_GROUPS=50
def stable_rank(identifier:str)->str:
    return hashlib.sha256((SEED+":"+identifier).encode()).hexdigest()

def group_aware_baseline(papyri:dict,samples:dict,classes:dict)->dict:
    if (len(papyri)!=EXPECTED_PAPYRI or len(samples)!=EXPECTED_SAMPLES or
        len(classes)!=EXPECTED_CLASSES):
        raise PublicSourceError("DDD publisher source universe drift")
    image_cluster={}
    for image_id,item in papyri.items():
        if not isinstance(item,dict) or not isinstance(item.get("doc_cluster"),int):
            raise PublicSourceError("Source image cluster absent")
        image_cluster[str(image_id)]=str(item["doc_cluster"])
        if not isinstance(item.get("copyright"),str):
            raise PublicSourceError("Source-specific item copyright absent")
    groups=sorted(set(image_cluster.values()),key=stable_rank)
    if len(groups)!=EXPECTED_GROUPS:raise PublicSourceError("Not 50 source-independent originals")
    # Deterministic 35/7/8 physical-witness groups, not random source images.
    group_membership={g:("train" if i<35 else "dev" if i<42 else "test")
                      for i,g in enumerate(groups)}
    labels={"train":[],"dev":[],"test":[]}
    doc_samples={"train":collections.Counter(),"dev":collections.Counter(),"test":collections.Counter()}
    observed_image_ids=set()
    sample_normalized={}
    all_labels=set()
    for sample_id,row in samples.items():
        if not isinstance(row,dict):raise PublicSourceError("Source sample must be a record")
        img=str(row.get("document_number") or "")
        label=row.get("class_label")
        if img not in image_cluster or not isinstance(label,str) or not label.strip():
            raise PublicSourceError("Sample missing exact image/document identity or publisher label")
        if str(row.get("sample_number")) != str(sample_id):
            raise PublicSourceError("Source sample identity conflict")
        membership=group_membership[image_cluster[img]]
        labels[membership].append(label)
        doc_samples[membership][image_cluster[img]]+=1
        observed_image_ids.add(img)
        sample_normalized[str(sample_id)]=(membership,label,image_cluster[img])
        all_labels.add(label)
    if sum(len(v) for v in labels.values())!=EXPECTED_SAMPLES:
        raise PublicSourceError("Incomplete original annotation census")
    original_classes={v.get("class_label") for v in classes.values()
                      if isinstance(v,dict) and isinstance(v.get("class_label"),str)}
    out_of_taxonomy=all_labels-original_classes
    if out_of_taxonomy:
        raise PublicSourceError("Published sample labels absent in publisher class taxonomy")
    for part in ("train","dev","test"):
        if not labels[part] or not doc_samples[part]:raise PublicSourceError("Empty corpus partition")
    sets={part:set(c) for part,c in doc_samples.items()}
    if (sets["train"] & sets["dev"] or sets["train"] & sets["test"] or
        sets["dev"] & sets["test"]):
        raise PublicSourceError("Physical original leakage between train/dev/test")
    train_count=collections.Counter(labels["train"])
    prior_label,prior_count=sorted(train_count.items(),key=lambda q:(-q[1],q[0]))[0]
    real_test=labels["test"]
    observed_test=sum(train_count[x]>0 for x in real_test)
    correct=sum(x==prior_label for x in real_test)
    test_classes=set(real_test)
    unseen_class_set=test_classes-set(train_count)
    # Random sample-index control illustrates why document group discipline
    # matters. No images, embeddings, content or metric contamination.
    item_groups=collections.defaultdict(set)
    for sample_id,(_part,_label,group) in sample_normalized.items():
        rank=int(stable_rank("sample:"+sample_id)[:12],16)/(16**12)
        random_partition="train" if rank<0.70 else "dev" if rank<0.85 else "test"
        item_groups[group].add(random_partition)
    contaminated=sum(len(m)>1 for m in item_groups.values())
    cat1880_ids=[i for i,p in papyri.items() if "C1880" in str(p.get("name",""))]
    if len(cat1880_ids)<2 or len({image_cluster[str(i)] for i in cat1880_ids})!=1:
        raise PublicSourceError("Cat1880 original/rotation identity or source grouping drift")
    cluster=image_cluster[str(cat1880_ids[0])]
    rights=collections.Counter(papyri[i]["copyright"] for i in papyri)
    return {
        "protocol":"R029_source_original_17k_publisher_annotation_nonvisual_negative_control_v1",
        "source_record":"https://zenodo.org/records/20553713",
        "source_samples":len(samples),"source_papyri_images":len(papyri),
        "source_distinct_manuscripts":len(groups),
        "source_class_definitions":len(classes),
        "sample_observed_class_labels":len(all_labels),
        "source_images_with_annotation":len(observed_image_ids),
        "physical_witness_splits":{"train":35,"dev":7,"test":8},
        "sample_splits":{part:len(labels[part]) for part in ("train","dev","test")},
        "distinct_publisher_classes_by_partition":{p:len(set(labels[p])) for p in labels},
        "source_object_partition_intersection_count":0,
        "test_sample_count":len(real_test),"test_class_count":len(test_classes),
        "test_samples_with_train_attested_class":observed_test,
        "test_samples_with_train_attested_class_fraction":round(observed_test/len(real_test),8),
        "test_classes_unseen_in_train":len(unseen_class_set),
        "baseline_name":"train_label_majority_nonvisual_negative_control",
        "baseline_majority_class_training_frequency":prior_count,
        "baseline_original_document_holdout_correct":correct,
        "baseline_original_document_holdout_total":len(real_test),
        "baseline_original_document_holdout_accuracy":round(correct/len(real_test),8),
        "sample_random_control_document_clusters_contaminated":contaminated,
        "sample_random_control_total_clusters":len(item_groups),
        "cat1880_variant_ids":sorted(cat1880_ids),
        "cat1880_variant_source_cluster_count":1,
        "cat1880_group_partition":group_membership[cluster],
        "exact_source_item_copyright_strings":len(rights),
        "source_images_rights_explicitly_cleared_for_training":0,
        "publisher_licence":"CC_BY_NC_SA_4_0_RESEARCH_ONLY",
        "split_status":"NEW_FIXED_SEED_RESEARCH_DIAGNOSTIC_NOT_OFFICIAL_DDD_C-B",
        "heldout_images_retrieved":0,
        "image_model_trained":False,
        "empirical_hieratic_image_recognition_accuracy":None,
        "independent_blind_expert_gold":False,
        "benchmark_overlap":"UNKNOWN_QUARANTINED",
        "training_or_development_corpus_admitted":False,
        "weighted_capability_points_awarded":0,
        "source_originals_never_committed":True
    }

def run()->dict:
    originals={}
    manifest={}
    for name in ("papyri.json","samples.json","classes.json"):
        b,r=fetch_exact(name)
        originals[name]=json.loads(b)
        manifest[name]={"sha256":r["original_sha256"],"bytes":r["original_bytes"],
                         "md5":r["original_md5"]}
    report=group_aware_baseline(originals["papyri.json"],
                                originals["samples.json"],originals["classes.json"])
    report["source_sha256_proofs"]=manifest
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    r=run()
    s=json.dumps(r,indent=2,sort_keys=True,ensure_ascii=False)+"\n"
    if args.output:args.output.write_text(s,encoding="utf8")
    print(s)
if __name__=="__main__":main()
