"""Deterministic registered-data preprocessing plus one pinned private W8 image inspection path."""
from __future__ import annotations
import argparse, binascii, hashlib, json, math, os, re, stat, struct, sys, tempfile, zlib
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
import yaml
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]; SCHEMA=ROOT/"schemas/preprocessing_manifest.schema.json"; REGISTRY=ROOT/"data/sources/registry.yaml"
MET_PACKET_SCHEMA=ROOT/"data/acquisition/met/metadata_packet.schema.json"
MET_REFERENCE_LOCK=ROOT/"data/preprocessing/met_w6_source_lock.json"
MET_READINESS_SCHEMA=ROOT/"data/preprocessing/met_original_asset_readiness.schema.json"
MAX_INPUT_BYTES=64*1024*1024
MAX_IMAGE_PIXELS=1_000_000
# Resolve feature support before test monkeypatches replace os.link with a mock callable.
SECURE_DIRFD_PUBLISH_AVAILABLE=all(fn in os.supports_dir_fd for fn in (os.open,os.link,os.unlink))

class PreprocessingError(ValueError): pass

def _nfc(value:str)->str:
    import unicodedata
    return unicodedata.normalize("NFC",value)
PROFILES={"identity/1.0.0":lambda value:value,"unicode-nfc/1.0.0":_nfc}

def _read(path:Path)->Any:
    try:return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,yaml.YAMLError) as exc:raise PreprocessingError(f"{path}: {exc}") from exc
def _digest(data:bytes)->str:return hashlib.sha256(data).hexdigest()

def _jpeg_header(data:bytes,*,max_pixels:int=MAX_IMAGE_PIXELS)->tuple[int,int,int|None]:
    """Read bounded JPEG frame dimensions and EXIF orientation; never decodes pixels."""
    if not data.startswith(b"\xff\xd8"):raise PreprocessingError("JPEG magic is missing")
    pos=2;width=height=None;orientation=None;segments=0
    sof={0xC0,0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF}
    while pos<len(data) and segments<4096:
        if data[pos]!=0xff:raise PreprocessingError("invalid JPEG marker sequence")
        while pos<len(data) and data[pos]==0xff:pos+=1
        if pos>=len(data):break
        marker=data[pos];pos+=1;segments+=1
        if marker in {0xD8,0x01,*range(0xD0,0xD8)}:continue
        if marker==0xD9:break
        if marker==0xDA:break
        if pos+2>len(data):raise PreprocessingError("truncated JPEG segment length")
        length=int.from_bytes(data[pos:pos+2],"big")
        if length<2 or pos+length>len(data):raise PreprocessingError("truncated or invalid JPEG segment")
        segment=data[pos+2:pos+length];pos+=length
        if marker in sof:
            if len(segment)<6:raise PreprocessingError("truncated JPEG frame header")
            height=int.from_bytes(segment[1:3],"big");width=int.from_bytes(segment[3:5],"big")
        elif marker==0xE1 and segment.startswith(b"Exif\x00\x00"):
            orientation=_exif_orientation(segment[6:])
    if width is None or height is None or width<1 or height<1:raise PreprocessingError("JPEG frame dimensions are missing")
    if width*height>max_pixels:raise PreprocessingError("JPEG pixel dimensions exceed inspection safety limit")
    return width,height,orientation

def _exif_orientation(tiff:bytes)->int|None:
    if len(tiff)<8:return None
    endian=tiff[:2]
    if endian==b"II":order="little"
    elif endian==b"MM":order="big"
    else:return None
    if int.from_bytes(tiff[2:4],order)!=42:return None
    offset=int.from_bytes(tiff[4:8],order)
    if offset+2>len(tiff):return None
    count=int.from_bytes(tiff[offset:offset+2],order)
    if count>256 or offset+2+count*12>len(tiff):return None
    for index in range(count):
        entry=offset+2+index*12;tag=int.from_bytes(tiff[entry:entry+2],order);kind=int.from_bytes(tiff[entry+2:entry+4],order);items=int.from_bytes(tiff[entry+4:entry+8],order)
        if tag==0x0112:
            if kind!=3 or items!=1:return None
            value=int.from_bytes(tiff[entry+8:entry+10],order)
            return value if 1<=value<=8 else None
    return None

def inspect_original_image_bytes(data:bytes,*,expected_sha256:str|None=None,declared_mime:str|None=None)->dict[str,Any]:
    """Bounded source-byte identity/header inspection; deliberately does not assert pixel decoding or rights."""
    if len(data)>MAX_INPUT_BYTES:raise PreprocessingError("original image exceeds byte-size limit")
    if not data:raise PreprocessingError("original image is empty")
    digest=_digest(data)
    if expected_sha256 is not None and digest.lower()!=expected_sha256.lower():raise PreprocessingError("original image SHA-256 mismatch")
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        if len(data)<33 or int.from_bytes(data[8:12],"big")!=13 or data[12:16]!=b"IHDR":raise PreprocessingError("PNG header is truncated or malformed")
        width,height,depth,color,compression,filter_method,interlace=struct.unpack(">IIBBBBB",data[16:29])
        crc=int.from_bytes(data[29:33],"big")
        if (binascii.crc32(b"IHDR"+data[16:29])&0xffffffff)!=crc:raise PreprocessingError("PNG IHDR CRC mismatch")
        if not width or not height or depth!=8 or color not in {0,2,6} or compression or filter_method or interlace:raise PreprocessingError("unsupported PNG header")
        if width*height>MAX_IMAGE_PIXELS:raise PreprocessingError("PNG pixel dimensions exceed inspection safety limit")
        mime="image/png";orientation=None
    elif data.startswith(b"\xff\xd8"):
        width,height,orientation=_jpeg_header(data);mime="image/jpeg"
    else:raise PreprocessingError("original image magic is not supported PNG or JPEG")
    if declared_mime and declared_mime.split(";",1)[0].strip().lower()!=mime:raise PreprocessingError("declared MIME does not match image magic")
    return {"byte_sha256":digest,"byte_size":len(data),"mime_type_from_magic":mime,"pixel_dimensions":[width,height],"exif_orientation":orientation,"inspection_level":"bounded_container_header_only","pixel_decode_verified":False,"visual_content_reviewed":False,"source_side_or_exposure":"unresolved"}

def _load_met_packet(object_id:int)->tuple[dict[str,Any],dict[str,Any],str]:
    """Check the committed W6 packet against an independent fixed reference lock."""
    lock=json.loads(MET_REFERENCE_LOCK.read_text(encoding="utf-8"))
    entry=next((item for item in lock["objects"] if item["object_id"]==object_id),None)
    if entry is None:raise PreprocessingError(f"Met object {object_id} is not allowlisted")
    path=ROOT/"data/acquisition/met/objects"/f"{object_id}.json"
    if path.is_symlink() or not path.is_file():raise PreprocessingError("Met source packet is missing or is a symlink")
    resolved=path.resolve(strict=True)
    if not resolved.is_relative_to((ROOT/"data/acquisition/met/objects").resolve()):raise PreprocessingError("Met source packet escapes its evidence directory")
    raw=path.read_bytes()
    if len(raw)>MAX_INPUT_BYTES:raise PreprocessingError("Met source packet exceeds size limit")
    packet=json.loads(raw)
    packet_schema=json.loads(MET_PACKET_SCHEMA.read_text(encoding="utf-8"))
    errors=list(Draft202012Validator(packet_schema).iter_errors(packet))
    if errors:raise PreprocessingError(f"Met source packet schema failure: {errors[0].message}")
    observed=packet["observed"]
    if packet["verification_status"]!="verified_api_response_identity_and_schema":raise PreprocessingError("Met API response was not verified")
    if packet["requested_object_id"]!=entry["object_id"] or observed["objectID"]!=entry["object_id"]:raise PreprocessingError("Met API object ID mismatch")
    if observed["accessionNumber"]!=entry["accession"]:raise PreprocessingError("Met accession differs from fixed W6 source identity")
    if observed["objectURL"]!=entry["object_page"]:raise PreprocessingError("Met object page differs from fixed W6 source identity")
    if packet["response_body_sha256"]!=entry["api_response_sha256"]:raise PreprocessingError("Met API response body hash differs from fixed W6 evidence")
    if not observed["isPublicDomain"]:raise PreprocessingError("Met API public-domain flag is not true")
    expected_views=entry["original_image_urls"]
    actual_views=[observed["primaryImage"],*observed["additionalImages"]]
    if actual_views!=expected_views:raise PreprocessingError("Met original image URL metadata differs from fixed W6 source evidence")
    if packet["rights_assessment"]["original_image_bytes_obtained"] or packet["rights_assessment"]["original_image_sha256"] is not None:
        raise PreprocessingError("W6 metadata packet unexpectedly claims acquired image bytes")
    for url in actual_views:
        parts=urlsplit(url)
        if parts.scheme!="https" or parts.hostname!="images.metmuseum.org" or not parts.path.startswith("/CRDImages/eg/original/") or parts.username or parts.password or parts.query or parts.fragment:
            raise PreprocessingError("Met original-image reference outside exact HTTPS CDN policy")
    return entry,packet,_digest(raw)

def assess_met_original_asset_readiness(object_id:int=561392,view:str="primaryImage")->dict[str,Any]:
    """Offline exact-view selection and fail-closed intake readiness; never accesses the network."""
    lock=json.loads(MET_REFERENCE_LOCK.read_text(encoding="utf-8"));reconciliation=json.loads((ROOT/"data/acquisition/met/r017_reconciliation.json").read_text(encoding="utf-8"))
    all_candidates=[];selected=None
    for entry in lock["objects"]:
        _,packet,packet_sha=_load_met_packet(entry["object_id"])
        obs=packet["observed"]
        filename_accessions=[]
        filename=Path(obs["primaryImage"].split("?",1)[0]).name
        filename_accessions=re.findall(r"\d{2}[._]\d{3}[._]\d{3}",filename)
        filename_accessions=[re.sub(r"[._]",".",value) for value in filename_accessions]
        r017=next((candidate for candidate in reconciliation["candidates"] if candidate["candidate_id"]==f"MET-{entry['object_id']}"),None)
        direct_screen=("R-021 reports zero direct accession-string hits for this candidate; aliases, editions, facsimiles, image similarity and pretraining remain unresolved" if entry["object_id"] in {561345,561392} else "R-021 does not document an individual direct-hit result for this candidate")
        source_identity_warning=("image filename includes a second accession-like identifier" if len(set(filename_accessions))>1 else "physical support, view side and publication identity remain independently unverified")
        row={
            "object_id":entry["object_id"],"accession":entry["accession"],"api_response_sha256":entry["api_response_sha256"],
            "source_packet_sha256":packet_sha,"is_public_domain_api_flag":obs["isPublicDomain"],
            "official_object_page":entry["object_page"],"available_original_views":entry["original_image_urls"],
            "image_byte_sha256":None,"source_identity_status":"METADATA_VERIFIED_ONLY",
            "source_identity_warning":source_identity_warning,"r017_literal_match_ids":(r017 or {}).get("literal_accession_substring_matches_in_pinned_R017_public_metadata",[]),
            "r017_normalized_match_ids":(r017 or {}).get("normalized_accession_string_matches_in_pinned_R017_public_metadata",[]),
            "r021_direct_collision_screen":direct_screen,
            "benchmark_independence":"NOT_ESTABLISHED","rights_status":"CC0_POLICY_AND_API_FLAG_OBSERVED; EXACT_ASSET_RETRIEVAL_NOT_AUTHORIZED_OR_VERIFIED",
            "expert_gold":"MISSING","data008_status":"BLOCKED","go_no_go":"NO_GO",
        }
        all_candidates.append(row)
        if entry["object_id"]==object_id:
            if view=="primaryImage":view_index=0
            elif re.fullmatch(r"additionalImages:[0-9]+",view):view_index=int(view.split(":",1)[1])+1
            else:raise PreprocessingError("view must be primaryImage or additionalImages:<zero-based-index>")
            if not 0<=view_index<len(entry["original_image_urls"]):raise PreprocessingError("selected image view does not exist in the fixed source metadata")
            selected_url=entry["original_image_urls"][view_index]
            selected={**row,"selected_view":view,"exact_image_url":selected_url,
                "retrieval_authorization":{"status":"NOT_RECORDED","independent_authority_record_id":None,"approved_by":None,"approved_at":None,"approval_digest":None},
                "download_performed":False,"download_command_enabled":False,
                "blockers":["No independent owner-approved retrieval record for this exact object/view/purpose is present.","No DATA-001 Met source record or completed DATA-002 exact-image acquisition record exists.","No original image bytes, byte hash, MIME/magic result, file size, dimensions, decoder/EXIF result or side/exposure determination exists.","Physical support and publication/edition aliases are not independently reviewed; do not infer a separate manuscript from API views.","R-017/R-021 benchmark, facsimile, edition and perceptual overlap remains unresolved.","No independently authored and dual-reviewed scholarly line gold or associated rights evidence exists.","Production trust-root/admission remains disabled by DATA-008."],
                "source_identity_warning":source_identity_warning}
    if selected is None:raise PreprocessingError(f"Met object {object_id} is not in the fixed source lock")
    return {"schema_version":"1.0.0","assessment_id":"W7-DATA-003-MET-ORIGINAL-ASSET-READINESS-v1","generated_by":"hieratic-preprocessing/1.1.0","network_used":False,"image_bytes_read":False,"candidate_count":len(all_candidates),"all_candidates_no_go":all(row["go_no_go"]=="NO_GO" for row in all_candidates),"selected_candidate":selected,"candidate_matrix":all_candidates,"r021_global_collision_warning":"R-021 identifies direct benchmark source support collisions for Abbott and Hearst. Met candidate string-screen results do not establish benchmark independence; alias, edition, facsimile, pixel-level and pretraining review remain open.","evidence_boundary":"API metadata and image URL references are not image bytes, item-specific retrieval approval, independently determined rights, scholarly gold, benchmark clearance, or corpus admission.","retrieval_receipt_template":{"record_version":"1.0.0","status":"NOT_RECORDED","independent_authority_record_id":None,"authority_registry_ref":None,"object_id":object_id,"accession":selected["accession"],"exact_image_url":selected["exact_image_url"],"permitted_purpose":None,"approved_vault_id":None,"approved_by":None,"approved_at":None,"expiry_or_revocation_ref":None,"evidence_digest":None,"signature_verification":"must be independently checked outside this task-writable repository; a submitter-entered receipt is not authority"}}

def _publish_readiness_output(path:Path,payload:dict[str,Any])->None:
    """Commit immutable metadata using pinned POSIX dirfds; never follow a swapped parent."""
    import secrets, stat
    root=(ROOT/"data/preprocessing").resolve(strict=True)
    absolute=path.absolute()
    try:relative=absolute.relative_to(root)
    except ValueError as exc:raise PreprocessingError("readiness output must remain under data/preprocessing") from exc
    if not relative.parts or any(part in {".","..",""} for part in relative.parts):
        raise PreprocessingError("readiness output contains an invalid or escaping component")
    if os.name!="posix" or not all(hasattr(os,flag) for flag in ("O_DIRECTORY","O_NOFOLLOW")) or not SECURE_DIRFD_PUBLISH_AVAILABLE:
        raise PreprocessingError("secure readiness publication requires POSIX no-follow directory handles")
    flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
    directory_fd=None
    temporary=None
    published=False
    name=relative.parts[-1]
    try:
        directory_fd=os.open(root,flags)
        for component in relative.parts[:-1]:
            next_fd=os.open(component,flags,dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd=next_fd
        # Path inspection alone never authorizes publication: compare it to the held handle.
        def parent_is_still_pinned()->bool:
            current=os.stat(absolute.parent,follow_symlinks=False)
            pinned=os.fstat(directory_fd)
            return stat.S_ISDIR(current.st_mode) and (current.st_dev,current.st_ino)==(pinned.st_dev,pinned.st_ino)
        if not parent_is_still_pinned():
            raise PreprocessingError("readiness output parent was replaced")
        temporary=f".readiness-{secrets.token_hex(12)}.tmp"
        staged_fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory_fd)
        with os.fdopen(staged_fd,"w",encoding="utf-8",newline="\n") as stream:
            json.dump(payload,stream,ensure_ascii=False,sort_keys=True,indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # Both source and destination resolve relative to the *same pinned directory*.
        # The link is atomic/no-clobber even for pre-existing empty files or symlinks.
        os.link(temporary,name,src_dir_fd=directory_fd,dst_dir_fd=directory_fd,follow_symlinks=False)
        published=True
        os.fsync(directory_fd)
        if not parent_is_still_pinned():
            raise PreprocessingError("readiness output parent moved during commit")
    except (OSError,PreprocessingError) as exc:
        if published and directory_fd is not None:
            try:os.unlink(name,dir_fd=directory_fd)
            except OSError:pass
        if isinstance(exc,PreprocessingError):raise
        raise PreprocessingError("readiness output could not be atomically published (no-clobber or unsafe symlink/parent traversal)") from exc
    finally:
        if temporary and directory_fd is not None:
            try:os.unlink(temporary,dir_fd=directory_fd)
            except FileNotFoundError:pass
        if directory_fd is not None:os.close(directory_fd)

def validate_request(payload:Any,registry:dict[str,Any],base:Path,acquisition:dict[str,Any]|None=None)->list[str]:
    errors=[e.message for e in Draft202012Validator(_read(SCHEMA)).iter_errors(payload)]
    if errors:return errors
    sources={s["source_id"]:s for s in registry["sources"]};seen=set()
    for item in payload["items"]:
        iid=item["item_id"]
        if iid in seen:errors.append(f"duplicate item_id: {iid}")
        seen.add(iid);source=sources.get(item["source_id"])
        synthetic=item["acquisition_record_id"].startswith("synthetic:") and item["source_id"]=="SRC-REPO-SYNTHETIC"
        if synthetic:
            if payload["acquisition_manifest_id"]!=item["acquisition_record_id"]:errors.append(f"{iid}: synthetic acquisition manifest ID mismatch")
        elif acquisition is None:errors.append(f"{iid}: real assets require the referenced DATA-002 acquisition manifest")
        else:
            if acquisition.get("manifest_id")!=payload["acquisition_manifest_id"]:errors.append(f"{iid}: DATA-002 manifest ID mismatch")
            matches=[a for a in acquisition.get("items",[]) if a.get("source_id")==item["source_id"] and a.get("source_object_id")==item["source_object_id"]]
            if len(matches)!=1:errors.append(f"{iid}: expected exactly one DATA-002 item for source/object identity; found {len(matches)}")
            else:
                acquired=matches[0]
                if acquired.get("intended_use")!=item["intended_use"]:errors.append(f"{iid}: intended use differs from DATA-002 record")
                if acquired.get("acquisition_status")!="complete":errors.append(f"{iid}: DATA-002 acquisition is not complete")
                if acquired.get("actual_sha256","").lower()!=item["input_sha256"].lower():errors.append(f"{iid}: input hash differs from acquired DATA-002 bytes")
                if acquired.get("benchmark_quarantine") is not False or acquired.get("benchmark_overlap_review",{}).get("status")!="clear":errors.append(f"{iid}: DATA-002 benchmark quarantine/overlap review is not clear")
                if acquired.get("source_rights_snapshot",{}).get("rights_class")!=item["rights_class"]:errors.append(f"{iid}: rights class differs from DATA-002 snapshot")
                if source and acquired.get("source_rights_snapshot",{}).get("use_decision")!="allowed":errors.append(f"{iid}: DATA-002 use decision is not allowed")
                if source and source.get(f"{item['intended_use']}_use")!="allowed":errors.append(f"{iid}: DATA-001 {item['intended_use']} decision is not allowed")
                from tools.acquisition import logical_fingerprint
                if item["acquisition_record_id"]!=logical_fingerprint(acquired):errors.append(f"{iid}: acquisition_record_id does not match DATA-002 logical fingerprint")
                from tools.acquisition import validate_data as validate_acquisition
                acquisition_schema=json.loads((ROOT/"schemas/acquisition_manifest.schema.json").read_text(encoding="utf-8"))
                acquisition_errors,_=validate_acquisition(acquisition,registry,acquisition_schema)
                if acquisition_errors:errors.extend(f"{iid}: DATA-002 policy validation: {message}" for message in acquisition_errors)
        if source is None and not synthetic:errors.append(f"{iid}: unidentified source_id")
        elif source is not None:
            if source.get("training_use")!="allowed":errors.append(f"{iid}: source training use is not allowed")
            if source.get("rights_class") in {"UNKNOWN","EVALUATION-ONLY","RESTRICTED"}:errors.append(f"{iid}: source rights class is not eligible")
            if source.get("benchmark_quarantine") is True:errors.append(f"{iid}: benchmark-quarantined source")
        if item["benchmark_quarantine"]:errors.append(f"{iid}: benchmark-quarantined item")
        if item["benchmark_overlap_review"]!="clear":errors.append(f"{iid}: benchmark overlap is not cleared")
        if not item["source_object_id"].strip():errors.append(f"{iid}: missing source object identity")
        path=(base/item["asset_path"]).resolve()
        if not path.is_relative_to(base.resolve()) or Path(item["asset_path"]).is_absolute():
            errors.append(f"{iid}: asset_path escapes the manifest directory")
        elif not path.is_file():errors.append(f"{iid}: input asset is missing: {item['asset_path']}")
        elif _digest(path.read_bytes())!=item["input_sha256"]:errors.append(f"{iid}: input SHA-256 mismatch")
        for op in item["operations"]:
            if op["kind"]=="crop" and (op["box"][2]<=op["box"][0] or op["box"][3]<=op["box"][1]):errors.append(f"{iid}: crop bounds must have positive area")
            if op["kind"]=="text_normalize" and f"{op['text_profile']}/{op['text_profile_version']}" not in PROFILES:errors.append(f"{iid}: undeclared text profile/version")
    return errors

class Raster:
    def __init__(self,width:int,height:int,mode:str,pixels:list[tuple[int,...]]):self.width,self.height,self.mode,self.pixels=width,height,mode,pixels
    def at(self,x:int,y:int)->tuple[int,...]:return self.pixels[y*self.width+x]

def _ppm_tokens(data:bytes):
    i=0;n=len(data)
    while i<n:
        while i<n and data[i] in b" \t\r\n\v\f":i+=1
        if i<n and data[i]==35:
            while i<n and data[i] not in b"\r\n":i+=1
            continue
        if i>=n:break
        start=i
        while i<n and data[i] not in b" \t\r\n\v\f#":i+=1
        if i==start:break
        token=data[start:i]
        delim=data[i:i+1]
        yield token,i+len(delim),delim

def decode_ppm(path:Path)->Raster:
    if path.stat().st_size>MAX_INPUT_BYTES:raise PreprocessingError("image input exceeds byte-size limit")
    data=path.read_bytes();tokens=iter(_ppm_tokens(data));header=[]
    try:
        for _ in range(4):header.append(next(tokens))
    except StopIteration as exc:raise PreprocessingError("truncated PPM header") from exc
    if header[0][0] not in {b"P3",b"P6"}:raise PreprocessingError("only P3/P6 PPM input is supported by the standard-library decoder")
    try:w,h,mx=(int(header[i][0]) for i in range(1,4))
    except ValueError as exc:raise PreprocessingError("invalid PPM dimensions/max value") from exc
    if w<1 or h<1 or w*h>MAX_IMAGE_PIXELS or not 1<=mx<=65535:raise PreprocessingError("invalid PPM dimensions, pixel budget, or max value")
    count=w*h*3
    if header[0][0]==b"P3":
        values_tokens=list(tokens)
        if len(values_tokens)<count:raise PreprocessingError("truncated P3 sample data")
        values=[]
        for token,_,_ in values_tokens[:count]:
            try:v=int(token)
            except ValueError as exc:raise PreprocessingError("invalid P3 sample value") from exc
            if not 0<=v<=mx:raise PreprocessingError("P3 sample outside declared max value")
            values.append((v*255+mx//2)//mx)
    else:
        pos=header[3][1]
        # P6 sample data begins immediately after the single header separator (CRLF counts as one line ending).
        if header[3][2]==b"\r" and data[pos:pos+1]==b"\n":pos+=1
        bps=1 if mx<256 else 2;needed=count*bps;raw=data[pos:pos+needed]
        if len(raw)!=needed:raise PreprocessingError("truncated P6 sample data")
        if bps==1:rawvals=list(raw)
        else:rawvals=[raw[i]*256+raw[i+1] for i in range(0,len(raw),2)]
        if any(v>mx for v in rawvals):raise PreprocessingError("P6 sample outside declared max value")
        values=[(v*255+mx//2)//mx for v in rawvals]
    return Raster(w,h,"RGB",[tuple(values[i:i+3]) for i in range(0,count,3)])

def decode_png(path:Path)->Raster:
    if path.stat().st_size>MAX_INPUT_BYTES:raise PreprocessingError("image input exceeds byte-size limit")
    data=path.read_bytes();signature=b"\x89PNG\r\n\x1a\n"
    if not data.startswith(signature):raise PreprocessingError("invalid PNG signature")
    pos=len(signature);width=height=depth=color=None;compressed=bytearray();ended=False
    while pos+12<=len(data):
        length=struct.unpack(">I",data[pos:pos+4])[0];kind=data[pos+4:pos+8];chunk=data[pos+8:pos+8+length];crc=struct.unpack(">I",data[pos+8+length:pos+12+length])[0]
        if len(chunk)!=length or (binascii.crc32(kind+chunk)&0xffffffff)!=crc:raise PreprocessingError("PNG chunk truncated or CRC mismatch")
        pos+=12+length
        if kind==b"IHDR":
            if length!=13:raise PreprocessingError("invalid PNG IHDR")
            width,height,depth,color,compression,filter_method,interlace=struct.unpack(">IIBBBBB",chunk)
            if not width or not height or depth!=8 or color not in {0,2,6} or compression or filter_method or interlace:raise PreprocessingError("PNG requires 8-bit grayscale/RGB/RGBA, standard compression/filter, non-interlaced layout")
            if width*height>MAX_IMAGE_PIXELS:raise PreprocessingError("PNG pixel dimensions exceed decoder safety limit")
        elif kind==b"IDAT":
            compressed.extend(chunk)
            if len(compressed)>MAX_INPUT_BYTES:raise PreprocessingError("PNG compressed stream exceeds byte-size limit")
        elif kind==b"IEND":ended=True;break
    if not ended or width is None:raise PreprocessingError("PNG is missing IHDR or IEND")
    channels={0:1,2:3,6:4}[color];bpp=channels;stride=width*channels
    expected_raw_size=(stride+1)*height
    if expected_raw_size>MAX_IMAGE_PIXELS*5:raise PreprocessingError("PNG decompressed pixel data exceeds decoder safety limit")
    try:
        decoder=zlib.decompressobj()
        raw=decoder.decompress(bytes(compressed),expected_raw_size+1)
        if decoder.unconsumed_tail or not decoder.eof or decoder.unused_data:raise PreprocessingError("PNG decompressed stream exceeds bounds or has trailing data")
    except zlib.error as exc:raise PreprocessingError(f"invalid PNG deflate stream: {exc}") from exc
    if len(raw)!=expected_raw_size:raise PreprocessingError("PNG decompressed size does not match dimensions")
    rows=[];prior=bytearray(stride);offset=0
    for _ in range(height):
        filter_type=raw[offset];offset+=1;encoded=raw[offset:offset+stride];offset+=stride;row=bytearray(stride)
        for i,val in enumerate(encoded):
            left=row[i-bpp] if i>=bpp else 0;up=prior[i];upper_left=prior[i-bpp] if i>=bpp else 0
            if filter_type==0:predictor=0
            elif filter_type==1:predictor=left
            elif filter_type==2:predictor=up
            elif filter_type==3:predictor=(left+up)//2
            elif filter_type==4:
                p=left+up-upper_left;pa=abs(p-left);pb=abs(p-up);pc=abs(p-upper_left);predictor=left if pa<=pb and pa<=pc else up if pb<=pc else upper_left
            else:raise PreprocessingError(f"unsupported PNG row filter {filter_type}")
            row[i]=(val+predictor)&255
        rows.append(row);prior=row
    mode={1:"L",3:"RGB",4:"RGBA"}[channels];pixels=[]
    for row in rows:
        if channels==1:pixels.extend((v,) for v in row)
        else:pixels.extend(tuple(row[i:i+channels]) for i in range(0,len(row),channels))
    return Raster(width,height,mode,pixels)

def decode_image(path:Path)->Raster:
    if path.stat().st_size>MAX_INPUT_BYTES:raise PreprocessingError("image input exceeds byte-size limit")
    with path.open("rb") as stream:signature=stream.read(8)
    return decode_png(path) if signature==b"\x89PNG\r\n\x1a\n" else decode_ppm(path)

def _matrix_multiply(a,b):return [[sum(a[r][k]*b[k][c] for k in range(3)) for c in range(3)] for r in range(3)]
def _identity():return [[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0]]

def _orient(im:Raster,orientation:str)->tuple[Raster,list[list[float]]]:
    w,h=im.width,im.height
    if orientation=="identity":return im,_identity()
    if orientation=="rotate_90_clockwise":
        out=Raster(h,w,im.mode,[im.at(y,h-1-x) for y in range(w) for x in range(h)]);m=[[0,-1,h],[1,0,0],[0,0,1]]
    elif orientation=="rotate_180":out=Raster(w,h,im.mode,[im.at(w-1-x,h-1-y) for y in range(h) for x in range(w)]);m=[[-1,0,w],[0,-1,h],[0,0,1]]
    elif orientation=="rotate_270_clockwise":out=Raster(h,w,im.mode,[im.at(w-1-y,x) for y in range(w) for x in range(h)]);m=[[0,1,0],[-1,0,w],[0,0,1]]
    else:raise PreprocessingError(f"unsupported orientation {orientation}")
    return out,m

def _convert(im:Raster,mode:str)->Raster:
    pixels=[]
    for p in im.pixels:
        if mode=="RGB":q=p[:3] if len(p)>=3 else (p[0],)*3
        elif mode=="L":q=((299*p[0]+587*p[1]+114*p[2]+500)//1000,) if len(p)>=3 else (p[0],)
        elif mode=="RGBA":q=(p[0],p[1],p[2],p[3] if len(p)>3 else 255) if len(p)>=3 else (p[0],p[0],p[0],255)
        else:raise PreprocessingError(f"unsupported image mode {mode}")
        pixels.append(q)
    return Raster(im.width,im.height,mode,pixels)

def _resize(im:Raster,w:int,h:int,method:str)->Raster:
    if method not in {"nearest","bilinear"}:raise PreprocessingError("standard-library resampler supports nearest and bilinear only")
    result=[]
    for y in range(h):
        sy=(y+.5)*im.height/h-.5
        for x in range(w):
            sx=(x+.5)*im.width/w-.5
            if method=="nearest":result.append(im.at(min(im.width-1,max(0,int(math.floor(sx+.5)))),min(im.height-1,max(0,int(math.floor(sy+.5))))));continue
            x0=max(0,min(im.width-1,math.floor(sx)));y0=max(0,min(im.height-1,math.floor(sy)));x1=min(im.width-1,x0+1);y1=min(im.height-1,y0+1);dx=max(0,min(1,sx-x0));dy=max(0,min(1,sy-y0))
            vals=[]
            for c in range(len(im.pixels[0])):
                value=(im.at(x0,y0)[c]*(1-dx)*(1-dy)+im.at(x1,y0)[c]*dx*(1-dy)+im.at(x0,y1)[c]*(1-dx)*dy+im.at(x1,y1)[c]*dx*dy)
                vals.append(max(0,min(255,math.floor(value+.5))))
            result.append(tuple(vals))
    return Raster(w,h,im.mode,result)

def _resize_operation(im:Raster,op:dict[str,Any])->tuple[Raster,list[list[float]]]:
    w,h=op["width"],op["height"];fit=op["fit"]
    if fit=="exact":rw,rh=w,h;left=top=0
    elif fit=="contain":
        if im.width*h>=im.height*w:rw=w;rh=max(1,(im.height*w+im.width//2)//im.width)
        else:rh=h;rw=max(1,(im.width*h+im.height//2)//im.height)
        left=(w-rw)//2;top=(h-rh)//2
    else:
        if im.width*h>=im.height*w:rh=h;rw=max(w,(im.width*h+im.height-1)//im.height)
        else:rw=w;rh=max(h,(im.height*w+im.width-1)//im.width)
        left=(rw-w)//2;top=(rh-h)//2
    resized=_resize(im,rw,rh,op["resampling"])
    scale=[[rw/im.width,0,0],[0,rh/im.height,0],[0,0,1]]
    if fit=="contain":
        bg=(0,)*len(im.pixels[0]);pixels=[bg]*(w*h)
        for y in range(rh):
            for x in range(rw):pixels[(y+top)*w+x+left]=resized.at(x,y)
        return Raster(w,h,im.mode,pixels),[[rw/im.width,0,left],[0,rh/im.height,top],[0,0,1]]
    if fit=="cover":
        pixels=[resized.at(x+left,y+top) for y in range(h) for x in range(w)]
        return Raster(w,h,im.mode,pixels),[[rw/im.width,0,-left],[0,rh/im.height,-top],[0,0,1]]
    return resized,scale

def _png_chunk(kind:bytes,data:bytes)->bytes:
    body=kind+data;return struct.pack(">I",len(data))+body+struct.pack(">I",binascii.crc32(body)&0xffffffff)
def encode_png(im:Raster)->bytes:
    color={"L":0,"RGB":2,"RGBA":6}.get(im.mode)
    if color is None:raise PreprocessingError(f"cannot encode image mode {im.mode}")
    bpp=len(im.pixels[0]);raw=b"".join(b"\x00"+bytes(c for p in im.pixels[y*im.width:(y+1)*im.width] for c in p) for y in range(im.height))
    # Deterministic zlib stream using uncompressed DEFLATE blocks, independent of zlib compressor versions.
    blocks=[];offset=0
    while offset<len(raw):
        chunk=raw[offset:offset+65535];offset+=len(chunk);final=offset==len(raw);n=len(chunk)
        blocks.append(bytes([1 if final else 0])+struct.pack("<HH",n,n^0xffff)+chunk)
    compressed=b"\x78\x01"+b"".join(blocks)+struct.pack(">I",zlib.adler32(raw)&0xffffffff)
    header=struct.pack(">IIBBBBB",im.width,im.height,8,color,0,0,0)
    return b"\x89PNG\r\n\x1a\n"+_png_chunk(b"IHDR",header)+_png_chunk(b"IDAT",compressed)+_png_chunk(b"IEND",b"")

def transform_image(source:Path,operations:list[dict[str,Any]])->tuple[bytes,list[dict[str,Any]]]:
    image=decode_image(source);matrix=_identity();lineage=[{"kind":"decode","format":"PNG 8-bit non-interlaced or PPM P3/P6","input_mode":image.mode,"input_size":[image.width,image.height],"orientation":"metadata orientation is not inferred; identity until explicitly declared"}]
    for op in operations:
        before=[image.width,image.height];local=_identity()
        if op["kind"]=="orient":image,local=_orient(image,op["orientation"])
        elif op["kind"]=="convert_mode":image=_convert(image,op["mode"])
        elif op["kind"]=="resize":image,local=_resize_operation(image,op)
        elif op["kind"]=="crop":
            x0,y0,x1,y1=op["box"]
            if x1>image.width or y1>image.height:raise PreprocessingError(f"crop box {op['box']} exceeds current image bounds {[image.width,image.height]}")
            image=Raster(x1-x0,y1-y0,image.mode,[image.at(x,y) for y in range(y0,y1) for x in range(x0,x1)]);local=[[1,0,-x0],[0,1,-y0],[0,0,1]]
        elif op["kind"]!="text_normalize":raise PreprocessingError(f"unsupported image operation {op['kind']}")
        matrix=_matrix_multiply(local,matrix)
        if op["kind"]!="text_normalize":lineage.append({"operation":op,"input_size":before,"output_size":[image.width,image.height],"coordinate_system":"pixel_origin_top_left; crop right/bottom exclusive","cumulative_input_to_output_matrix":matrix})
    return encode_png(image),lineage

def run(manifest_path:Path,out_dir:Path,acquisition:dict[str,Any]|None=None)->dict[str,Any]:
    payload=_read(manifest_path);registry=_read(REGISTRY);errors=validate_request(payload,registry,manifest_path.parent,acquisition)
    if errors:raise PreprocessingError("\n".join(errors))
    records=[]
    for item in sorted(payload["items"],key=lambda i:i["item_id"]):
        blob,lineage=transform_image(manifest_path.parent/item["asset_path"],[op for op in item["operations"] if op["kind"]!="text_normalize"])
        output_hash=_digest(blob);target=out_dir/f"{item['item_id']}.png";target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob)
        original_text=item.get("text_input");normalized=original_text;text_lineage=[]
        for op in item["operations"]:
            if op["kind"]=="text_normalize":
                if normalized is None:raise PreprocessingError(f"{item['item_id']}: text profile declared without text_input")
                before_text=normalized;normalized=PROFILES[f"{op['text_profile']}/{op['text_profile_version']}"](normalized);text_lineage.append({"profile":op["text_profile"],"version":op["text_profile_version"],"input_sha256":_digest(before_text.encode("utf-8")),"output_sha256":_digest(normalized.encode("utf-8"))})
        records.append({"item_id":item["item_id"],"acquisition_record_id":item["acquisition_record_id"],"source_id":item["source_id"],"source_object_id":item["source_object_id"],"input_sha256":item["input_sha256"],"output_sha256":output_hash,"output_path":target.name,"text_input":original_text,"normalized_text":normalized,"text_transformations":text_lineage,"transformations":lineage})
    identity={"schema_version":payload["schema_version"],"profile_id":payload["profile_id"],"acquisition_manifest_id":payload["acquisition_manifest_id"],"items":records};version="ds-"+hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(",",":")).encode()).hexdigest();result={**identity,"dataset_version_id":version,"generator":"hieratic-preprocessing/1.0.0"}
    (out_dir/"dataset-manifest.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8");return result

W8_PROFILE=ROOT/"data/preprocessing/w8_cat2044_inspection.json"
W8_EXPECTED_SHA256="569e8e5bb446588481481bfea823fc95383bb7076270363c666f868b7fa5b912"
W8_PROFILE_SHA256="86e65185d0852a4229443651294e9ecbd0b0eb1f91d00e273e2bdd1e9857ac50"
W8_VAULT_SUFFIX=Path("HieraticAI/private-artifacts/W8")
W8_MAX_BYTES=8*1024*1024
W8_MAX_PIXELS=35_000_000
W8_MAX_EVIDENCE_BYTES=256*1024

def _w8_private_root()->Path:
    local=os.environ.get("LOCALAPPDATA")
    if not local:raise PreprocessingError("W8 local inspection requires LOCALAPPDATA private vault")
    root=(Path(local)/W8_VAULT_SUFFIX).absolute()
    if root.resolve(strict=True)==ROOT.resolve() or ROOT.resolve() in root.resolve(strict=True).parents:raise PreprocessingError("W8 private vault must be outside repository")
    if _has_symlink_or_junction(root):raise PreprocessingError("W8 private vault contains a symlink or junction")
    return root.resolve(strict=True)

def _has_symlink_or_junction(path:Path)->bool:
    current=Path(path.anchor)
    for part in path.parts[1:]:
        current=current/part
        if current.is_symlink() or (hasattr(current,"is_junction") and current.is_junction()):return True
    return False

def _w8_read_private_file(path:Path,limit:int,label:str)->bytes:
    flags=os.O_RDONLY|getattr(os,"O_BINARY",0)|getattr(os,"O_NOFOLLOW",0)
    try:descriptor=os.open(path,flags)
    except OSError as exc:raise PreprocessingError(f"W8 {label} cannot be opened without following links") from exc
    try:
        metadata=os.fstat(descriptor);reparse_flag=getattr(stat,"FILE_ATTRIBUTE_REPARSE_POINT",0x400)
        if not stat.S_ISREG(metadata.st_mode) or getattr(metadata,"st_file_attributes",0)&reparse_flag:raise PreprocessingError(f"W8 {label} is not a regular non-reparse file")
        if metadata.st_size>limit:raise PreprocessingError(f"W8 {label} exceeds configured byte bound")
        with os.fdopen(descriptor,"rb",closefd=False) as stream:data=stream.read(limit+1)
        if len(data)>limit:raise PreprocessingError(f"W8 {label} exceeds configured byte bound")
        current=path.stat()
        if (metadata.st_dev,metadata.st_ino)!=(current.st_dev,current.st_ino):raise PreprocessingError(f"W8 {label} path changed while reading")
        return data
    finally:os.close(descriptor)

def _w8_load_profile(path:Path=W8_PROFILE)->dict[str,Any]:
    try:raw=path.read_bytes();payload=json.loads(raw.decode("utf-8"))
    except (OSError,UnicodeError,json.JSONDecodeError) as exc:raise PreprocessingError("W8 inspection profile is missing or malformed") from exc
    # Git stores this repository text file with LF. Normalize checkout line endings
    # before checking the immutable content lock so Windows CRLF checkouts match CI.
    if _digest(raw.replace(b"\r\n",b"\n"))!=W8_PROFILE_SHA256:raise PreprocessingError("W8 inspection profile hash differs from immutable profile lock")
    if payload.get("profile_id")!="w8-cat2044-unlabelled-image-inspection" or payload.get("profile_version")!="1.0.0" or payload.get("engine_version")!="W8-CAT2044-INSPECTION-1.0.0":raise PreprocessingError("unsupported W8 inspection profile")
    source=payload.get("source_lock",{})
    required={"candidate_id":"CAT2044","institution":"Museo Egizio, Turin","source_object_id":"Cat.2044/013","physical_support_group":"Cat.2044/013","exact_file_page":"https://commons.wikimedia.org/wiki/File:Journal_of_year_1_of_Ramesses_VI_on_recto_and_verso_-_Museo_Egizio_Turin_C_2044_p01.jpg","exact_file_revision":"https://commons.wikimedia.org/w/index.php?title=File:Journal_of_year_1_of_Ramesses_VI_on_recto_and_verso_-_Museo_Egizio_Turin_C_2044_p01.jpg&oldid=900807568","exact_original_path":"/wikipedia/commons/e/e5/Journal_of_year_1_of_Ramesses_VI_on_recto_and_verso_-_Museo_Egizio_Turin_C_2044_p01.jpg","commons_pageid":145137491,"commons_api_response_sha256":"c530f106a4661d9a0ce7bfdefe51642e435bee868a077223b438c278466f1030","file_sha256":W8_EXPECTED_SHA256,"file_sha1":"752747405048f358147a7b1f0f697720c338394b","byte_size":2649239,"mime_type":"image/jpeg","dimensions":[7063,3947],"exif_orientation":1,"license":"CC0","license_url":"http://creativecommons.org/publicdomain/zero/1.0/deed.en","official_museum_policy_url":"https://collezioni.museoegizio.it/en-GB/","papyrus_database_image_policy_url":"https://collezionepapiri.museoegizio.it/en-GB/section/Papyrus-Database/Policy-on-access-and-publication-of-papyri/"}
    if any(source.get(key)!=value for key,value in required.items()):raise PreprocessingError("W8 source lock changed from the one authorized image")
    if payload.get("outputs",{}).get("training_admission")!="BLOCKED" or payload.get("outputs",{}).get("development_admission")!="BLOCKED" or payload.get("outputs",{}).get("evaluation_admission")!="NOT_AUTHORIZED" or payload.get("outputs",{}).get("benchmark_overlap")!="UNRESOLVED_QUARANTINED" or payload.get("outputs",{}).get("annotation_or_gold")!="NONE":raise PreprocessingError("W8 processing admission boundary changed")
    return payload

def _w8_verify_inputs(image_path:Path,evidence_path:Path,profile:dict[str,Any])->tuple[bytes,dict[str,Any],dict[str,Any],str]:
    vault=_w8_private_root()
    image_path=image_path.absolute();evidence_path=evidence_path.absolute()
    for path,label in ((image_path,"image"),(evidence_path,"evidence")):
        absolute=path.absolute()
        if _has_symlink_or_junction(absolute):raise PreprocessingError(f"W8 {label} path contains a symlink or junction")
        try:resolved=absolute.resolve(strict=True);resolved.relative_to(vault)
        except (OSError,ValueError) as exc:raise PreprocessingError(f"W8 {label} must be inside the protected private vault") from exc
    if image_path.name!="CAT2044-013-commons-original.jpg":raise PreprocessingError("W8 image filename does not match locked source")
    if evidence_path.name!="CAT2044.json":raise PreprocessingError("W8 evidence filename does not match locked source")
    if image_path.is_symlink() or evidence_path.is_symlink():raise PreprocessingError("W8 input must not be a symlink")
    if len(image_path.resolve(strict=True).relative_to(vault).parts)!=1 or len(evidence_path.resolve(strict=True).relative_to(vault).parts)!=1:raise PreprocessingError("W8 source and evidence files must be direct private-vault children")
    try:data=_w8_read_private_file(image_path,W8_MAX_BYTES,"source image");evidence_raw=_w8_read_private_file(evidence_path,W8_MAX_EVIDENCE_BYTES,"acquisition evidence");evidence=json.loads(evidence_raw.decode("utf-8"))
    except (OSError,UnicodeError,json.JSONDecodeError) as exc:raise PreprocessingError("W8 private evidence or image is unreadable") from exc
    source=profile["source_lock"]
    if len(data)!=source["byte_size"] or _digest(data)!=source["file_sha256"] or hashlib.sha1(data).hexdigest()!=source["file_sha1"]:raise PreprocessingError("W8 source byte hash/size differs from immutable lock")
    url_parts=urlsplit(evidence.get("exact_original_file_url", ""))
    if evidence.get("candidate_id")!="CAT2044" or evidence.get("source_object_id")!=source["source_object_id"] or evidence.get("physical_support_group")!=source["physical_support_group"] or evidence.get("commons_pageid")!=source["commons_pageid"] or evidence.get("commons_api_response_sha256")!=source["commons_api_response_sha256"] or evidence.get("source_sha256")!=source["file_sha256"] or evidence.get("source_byte_size")!=source["byte_size"] or evidence.get("commons_file_sha1")!=source["file_sha1"] or evidence.get("declared_dimensions")!=source["dimensions"] or evidence.get("mime_type")!=source["mime_type"] or url_parts.scheme!="https" or url_parts.hostname!="upload.wikimedia.org" or url_parts.path!=source["exact_original_path"] or url_parts.username or url_parts.password or url_parts.fragment:raise PreprocessingError("W8 acquisition evidence does not match exact source lock")
    if evidence.get("commons_file_page_url")!=source["exact_file_page"] or evidence.get("commons_file_revision_url")!=source["exact_file_revision"]:raise PreprocessingError("W8 evidence cites a different Commons page or revision")
    license_info=evidence.get("license",{});boundary=evidence.get("use_boundary",{})
    if license_info.get("identifier")!="CC0" or license_info.get("url")!=source["license_url"] or license_info.get("official_museum_policy_url")!=source["official_museum_policy_url"] or license_info.get("papyrus_database_image_policy_url")!=source["papyrus_database_image_policy_url"] or "Museo Egizio" not in license_info.get("file_credit_observation",""):raise PreprocessingError("W8 exact-file license evidence is not CC0 or its rights sources changed")
    if boundary.get("source_registry_status")!="NOT_REGISTERED" or boundary.get("benchmark_overlap_status")!="UNRESOLVED_QUARANTINED" or boundary.get("training_admission")!="BLOCKED" or boundary.get("development_admission")!="BLOCKED" or boundary.get("evaluation_admission")!="NOT_AUTHORIZED" or boundary.get("gold_or_transcription")!="NONE":raise PreprocessingError("W8 source evidence was promoted beyond inspection-only status")
    return data,evidence,source,_digest(evidence_raw)

def _w8_decode(data:bytes,source:dict[str,Any]):
    """Decode only the one pinned JPEG with Pillow decompression guards."""
    if len(data)>W8_MAX_BYTES:raise PreprocessingError("W8 source exceeds byte bound")
    width,height,orientation=_jpeg_header(data,max_pixels=W8_MAX_PIXELS)
    if width*height>W8_MAX_PIXELS:raise PreprocessingError("W8 decoded pixel count exceeds safety bound")
    import io, warnings
    try:
        from PIL import Image,ImageOps,UnidentifiedImageError
    except ImportError as exc:raise PreprocessingError("W8 JPEG pixel processing requires Pillow; install the documented optional image runtime") from exc
    effective_orientation=orientation if orientation is not None else 1
    if [width,height]!=source["dimensions"] or effective_orientation!=source["exif_orientation"]:raise PreprocessingError("W8 JPEG dimensions or EXIF orientation differ from source lock")
    previous_limit=Image.MAX_IMAGE_PIXELS;Image.MAX_IMAGE_PIXELS=W8_MAX_PIXELS
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error",Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as check:
                if check.format!="JPEG" or check.size!=(width,height):raise PreprocessingError("W8 decoder format or dimension mismatch")
                check.verify()
            image=Image.open(io.BytesIO(data));image.load()
            corrected=ImageOps.exif_transpose(image).convert("RGB")
    except (OSError,ValueError,Image.DecompressionBombError,Image.DecompressionBombWarning,UnidentifiedImageError) as exc:raise PreprocessingError(f"W8 JPEG pixel decode failed: {type(exc).__name__}") from exc
    finally:Image.MAX_IMAGE_PIXELS=previous_limit
    if corrected.size!=(width,height):raise PreprocessingError("W8 EXIF transform unexpectedly changed locked source dimensions")
    return corrected

def _w8_pixel_analysis(image,profile:dict[str,Any])->dict[str,Any]:
    """Return low-resolution material/ink proposals and diagnostics; never labels text."""
    from PIL import Image
    factor=profile["limits"]["analysis_downsample_factor"];width,height=image.size
    small=image.resize((max(1,(width+factor-1)//factor),max(1,(height+factor-1)//factor)),Image.Resampling.NEAREST)
    sw,sh=small.size;scale_x=width/sw;scale_y=height/sh;raw_rgb=small.convert("RGB").tobytes();pixels=list(zip(raw_rgb[0::3],raw_rgb[1::3],raw_rgb[2::3]));paper=bytearray(sw*sh);dark=bytearray(sw*sh);red=bytearray(sw*sh)
    hist=[0]*256;paper_count=dark_count=red_count=0
    margin_x=max(2,sw//100);margin_y=max(2,sh//100)
    for i,(r,g,b) in enumerate(pixels):
        lum=(299*r+587*g+114*b)//1000;hist[lum]+=1
        x=i%sw;y=i//sw
        # Exclude the photographed frame and edge shadow; classify brown paper
        # or very dark pixels only within the inner page area.
        is_paper=margin_x<=x<sw-margin_x and margin_y<=y<sh-margin_y and ((r>g+8 and g>b+3 and r<247) or lum<80)
        if is_paper:
            paper[i]=1;paper_count+=1
            if lum<80:dark[i]=1;dark_count+=1
            if r-g>26 and r>b*1.18 and lum<190:red[i]=1;red_count+=1
    min_area=profile["limits"]["candidate_region_min_area_pixels"];seen=bytearray(sw*sh);regions=[]
    for start,value in enumerate(paper):
        if not value or seen[start]:continue
        seen[start]=1;stack=[start];left=right=start%sw;top=bottom=start//sw;area=0
        while stack:
            pos=stack.pop();x=pos%sw;y=pos//sw;area+=1;left=min(left,x);right=max(right,x);top=min(top,y);bottom=max(bottom,y)
            for neighbor in (pos-1 if x else -1,pos+1 if x+1<sw else -1,pos-sw if y else -1,pos+sw if y+1<sh else -1):
                if neighbor>=0 and paper[neighbor] and not seen[neighbor]:seen[neighbor]=1;stack.append(neighbor)
        if area>=min_area and not ((right-left+1)/sw>0.95 and (bottom-top+1)/sh>0.90):
            regions.append({"analysis_box":[left,top,right+1,bottom+1],"source_box":[round(left*scale_x),round(top*scale_y),min(width,round((right+1)*scale_x)),min(height,round((bottom+1)*scale_y))],"sampled_pixels":area,"status":"unlabelled_material_or_text_region_candidate","interpretation_status":"UNKNOWN_UNREVIEWED_NOT_GOLD"})
    row_counts=[sum(dark[y*sw:(y+1)*sw]) for y in range(sh)];threshold=profile["limits"]["line_row_ink_minimum"]
    active=[count>=threshold for count in row_counts];merge=profile["limits"]["line_row_gap_merge"]
    bands=[];y=0
    while y<sh:
        if not active[y]:y+=1;continue
        top=y;end=y;gap=0;y+=1
        while y<sh:
            if active[y]:end=y;gap=0
            else:
                gap+=1
                if gap>merge:break
            y+=1
        if end+1-top>10:
            for split_top in range(top,end+1,8):bands.append((split_top,min(end+1,split_top+8)))
        else:bands.append((top,end+1))
    lines=[]
    for top,bottom in bands:
        counts=[sum(dark[row*sw+x] for row in range(top,bottom)) for x in range(sw)];columns=[count>=max(1,(bottom-top)//3) for count in counts];spans=[];x=0
        while x<sw:
            if not columns[x]:x+=1;continue
            x0=x;last=x;gap=0;x+=1
            while x<sw:
                if columns[x]:last=x;gap=0
                else:
                    gap+=1
                    if gap>4:break
                x+=1
            if last-x0>=3:spans.append((x0,last+1))
        for left,right in spans:
            box=[round(left*scale_x),round(top*scale_y),min(width,round(right*scale_x)),min(height,round(bottom*scale_y))]
            if box[2]-box[0]<40 or box[3]-box[1]<12:continue
            points=[(x,y) for y in range(top,bottom) for x in range(left,right) if dark[y*sw+x]]
            correction=0.0
            if len(points)>=8:
                mx=sum(x for x,_ in points)/len(points);my=sum(y for _,y in points)/len(points);variance=sum((x-mx)**2 for x,_ in points)
                if variance>0:
                    slope=sum((x-mx)*(y-my) for x,y in points)/variance;estimate=math.degrees(math.atan(slope))
                    if 0.25<=abs(estimate)<=5.0:correction=round(estimate,3)
            lines.append({"source_box":box,"analysis_box":[left,top,right,bottom],"reading_order":"right_to_left_candidate_order_only","first_candidate_edge":"right","status":"unlabelled_line_region_proposal_not_transcription_gold","reading_status":"UNKNOWN_UNREVIEWED","estimated_baseline_angle_degrees":round(estimate,3) if len(points)>=8 and variance>0 else None,"deskew_correction_degrees":correction,"deskew_status":"heuristic correction applied to crop" if correction else "not applied; estimated angle below threshold or insufficient evidence"})
    lines=sorted(lines,key=lambda item:(item["source_box"][1],-item["source_box"][0]))[:profile["limits"]["maximum_crop_proposals"]]
    total=len(pixels);mean=sum((i*n) for i,n in enumerate(hist))/max(total,1);variance=sum(((i-mean)**2)*n for i,n in enumerate(hist))/max(total,1)
    return {"analysis_dimensions":[sw,sh],"downsample_factor":factor,"material_candidate_pixel_fraction":paper_count/max(total,1),"dark_candidate_pixel_fraction":dark_count/max(paper_count,1),"red_tone_or_brown_pigment_candidate_pixel_fraction":red_count/max(paper_count,1),"sampled_luminance_mean":round(mean,4),"sampled_luminance_stddev":round(math.sqrt(variance),4),"candidate_material_regions":sorted(regions,key=lambda item:(item["source_box"][1],item["source_box"][0]))[:128],"candidate_line_regions":lines,"coordinate_transform_source_to_analysis":[[sw/width,0,0],[0,sh/height,0],[0,0,1]],"diagnostic_warning":"Color and darkness heuristics propose image regions only; they do not identify ink, script, reading, line truth, or gold. Red/brown hues can be papyrus, stain, or ink and are not distinguished as a scholarly reading."}

def inspect_w8_real_image(manifest_path:Path,image_path:Path,evidence_path:Path,out_dir:Path)->dict[str,Any]:
    """Private, fixed-source image-processing demonstration; never a corpus admission path."""
    profile=_w8_load_profile(manifest_path);data,evidence,source,evidence_digest=_w8_verify_inputs(image_path,evidence_path,profile);image=_w8_decode(data,source);analysis=_w8_pixel_analysis(image,profile)
    vault=_w8_private_root();absolute=out_dir.absolute()
    if _has_symlink_or_junction(absolute):raise PreprocessingError("W8 output path contains a symlink or junction")
    try:resolved_parent=absolute.parent.resolve(strict=True)
    except OSError as exc:raise PreprocessingError("W8 output parent must exist inside the private vault") from exc
    if resolved_parent!=vault:raise PreprocessingError("W8 output directory must be a direct child of the private local vault")
    if absolute.exists() or absolute.is_symlink():raise PreprocessingError("W8 output directory already exists; refusing overwrite")
    absolute.mkdir()
    created=[]
    try:
        from PIL import Image,ImageDraw,ImageOps
        factor=analysis["downsample_factor"];sw,sh=analysis["analysis_dimensions"]
        overlay=image.copy();draw=ImageDraw.Draw(overlay)
        for region in analysis["candidate_material_regions"]:
            x0,y0,x1,y1=region["source_box"];draw.rectangle((x0,y0,x1-1,y1-1),outline=(255,170,0),width=max(2,factor//2))
        for index,line in enumerate(analysis["candidate_line_regions"],1):
            x0,y0,x1,y1=line["source_box"];draw.rectangle((x0,y0,x1-1,y1-1),outline=(0,210,255),width=max(2,factor//2));draw.text((x0,y0),f"L{index} ?",fill=(0,30,100),stroke_width=1,stroke_fill=(255,255,255))
        preview=overlay.copy();preview.thumbnail((1800,1800),Image.Resampling.LANCZOS)
        artifacts=[]
        def save_image(name,image_obj):
            path=absolute/name;created.append(path);image_obj.save(path,format="PNG",optimize=False,compress_level=9);blob=path.read_bytes();artifacts.append({"path":name,"sha256":_digest(blob),"byte_size":len(blob),"dimensions":list(image_obj.size)});return path
        save_image("candidate-regions-overlay.png",preview)
        mask=Image.new("L",(sw,sh));mask_rgb=image.resize((sw,sh),Image.Resampling.NEAREST).convert("RGB").tobytes();margin_x=max(2,sw//100);margin_y=max(2,sh//100);mask.putdata([255 if margin_x<=i%sw<sw-margin_x and margin_y<=i//sw<sh-margin_y and ((r>g+8 and g>b+3 and r<247) or ((299*r+587*g+114*b)//1000)<80) else 0 for i,(r,g,b) in enumerate(zip(mask_rgb[0::3],mask_rgb[1::3],mask_rgb[2::3]))]);save_image("material-candidate-mask.png",mask)
        crop_records=[]
        total_crop_pixels=0
        for index,line in enumerate(analysis["candidate_line_regions"],1):
            box=line["source_box"];pad_x=24;pad_y=64;crop_box=[max(0,box[0]-pad_x),max(0,box[1]-pad_y),min(image.width,box[2]+pad_x),min(image.height,box[3]+pad_y)];crop=image.crop(tuple(crop_box));angle=line["deskew_correction_degrees"];crop_width,crop_height=crop.size
            source_crop_pixels=crop_width*crop_height;crop_limit=profile["limits"]["maximum_crop_area_pixels"];aggregate_limit=profile["limits"]["maximum_total_crop_pixels"]
            if source_crop_pixels>crop_limit or total_crop_pixels+source_crop_pixels>aggregate_limit:
                crop_records.append({**line,"crop_artifact":None,"crop_source_bounds":crop_box,"crop_status":"omitted_private_output_size_limit","source_crop_pixels":source_crop_pixels});continue
            total_crop_pixels+=source_crop_pixels
            if angle:
                crop=crop.rotate(angle,resample=Image.Resampling.BILINEAR,expand=True,fillcolor=(255,255,255))
                theta=math.radians(angle);cosine=math.cos(theta);sine=math.sin(theta);out_cx,out_cy=crop.width/2,crop.height/2;in_cx,in_cy=crop_width/2,crop_height/2
                rotate=[[cosine,sine,out_cx-cosine*in_cx-sine*in_cy],[-sine,cosine,out_cy+sine*in_cx-cosine*in_cy],[0,0,1]]
                source_to_crop=_matrix_multiply(rotate,[[1,0,-crop_box[0]],[0,1,-crop_box[1]],[0,0,1]])
            else:source_to_crop=[[1,0,-crop_box[0]],[0,1,-crop_box[1]],[0,0,1]]
            name=f"line-candidate-{index:03d}.png";save_image(name,crop)
            crop_records.append({**line,"crop_artifact":name,"crop_status":"written_unlabelled_candidate","source_crop_pixels":source_crop_pixels,"crop_source_bounds":crop_box,"crop_context_padding_pixels":[pad_x,pad_y],"source_to_crop_transform":source_to_crop,"crop_bounds":"left/top inclusive; right/bottom exclusive"})
        input_sha=_digest(data);evidence_sha=evidence_digest
        identity={"profile_id":profile["profile_id"],"profile_version":profile["profile_version"],"engine_version":profile["engine_version"],"profile_sha256":W8_PROFILE_SHA256,"source_sha256":input_sha,"source_dimensions":source["dimensions"],"source_object_id":source["source_object_id"],"physical_support_group":source["physical_support_group"],"asset_view":"Commons p01; side/exposure is not independently mapped to recto or verso","historical_label_status":"unresolved: Commons filename says Ramesses VI while TPOP record says Ramesses V","evidence_sha256":evidence_sha,"analysis":analysis,"artifacts":artifacts,"crop_records":crop_records,"decoder":{"name":"Pillow","version":__import__("PIL").__version__},"exif_orientation":source["exif_orientation"],"orientation_operation":"EXIF transpose; identity for locked source orientation 1","rights_and_science_boundary":profile["outputs"],"gold_or_reading_created":False,"scientific_status":"UNLABELLED_HEURISTIC_OUTPUT; REVIEW_AND_READINGS_UNKNOWN"}
        identity["processing_id"]="w8-"+_digest(json.dumps(identity,sort_keys=True,separators=(",",":")).encode("utf-8"))
        complete=absolute/"inspection-manifest.json";temporary=absolute/".inspection-manifest.tmp";created.append(temporary)
        with temporary.open("w",encoding="utf-8",newline="\n") as stream:stream.write(json.dumps(identity,ensure_ascii=False,sort_keys=True,indent=2)+"\n");stream.flush();os.fsync(stream.fileno())
        os.rename(temporary,complete);created.remove(temporary);created.append(complete)
        return identity
    except Exception:
        for path in reversed(created):
            try:path.unlink(missing_ok=True)
            except OSError:pass
        try:absolute.rmdir()
        except OSError:pass
        raise

def main(argv=None)->int:
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest="command",required=True)
    check=sub.add_parser("validate");check.add_argument("manifest",type=Path);check.add_argument("--acquisition",type=Path)
    execute=sub.add_parser("run");execute.add_argument("manifest",type=Path);execute.add_argument("--acquisition",type=Path);execute.add_argument("--output",type=Path,required=True)
    readiness=sub.add_parser("met-readiness",help="offline, no-go preflight for an exact W6 Met image view")
    readiness.add_argument("--object-id",type=int,default=561392);readiness.add_argument("--view",default="primaryImage",help="primaryImage or additionalImages:<zero-based-index>");readiness.add_argument("--output",type=Path)
    inspect=sub.add_parser("inspect-image",help="private, pinned W8 unlabelled Cat.2044 image-processing demonstration")
    inspect.add_argument("manifest",type=Path,nargs="?",default=W8_PROFILE);inspect.add_argument("--image",type=Path,required=True,help="exact acquired JPEG inside the private W8 vault")
    inspect.add_argument("--evidence",type=Path,required=True,help="redacted Cat.2044 acquisition record inside the private W8 vault")
    inspect.add_argument("--output",type=Path,required=True,help="new, unused output directory inside the private W8 vault")
    args=parser.parse_args(argv)
    try:
        if args.command=="met-readiness":
            result=assess_met_original_asset_readiness(args.object_id,args.view)
            schema=json.loads(MET_READINESS_SCHEMA.read_text(encoding="utf-8"));errors=list(Draft202012Validator(schema).iter_errors(result))
            if errors:raise PreprocessingError(f"readiness output schema failure: {errors[0].message}")
            if args.output:_publish_readiness_output(args.output,result)
            print(json.dumps({"assessment_id":result["assessment_id"],"selected_object":args.object_id,"accession":result["selected_candidate"]["accession"],"view":args.view,"image_url":result["selected_candidate"]["exact_image_url"],"go_no_go":result["selected_candidate"]["go_no_go"],"download_performed":False,"blocker_count":len(result["selected_candidate"]["blockers"]),"output":str(args.output) if args.output else None},ensure_ascii=False,sort_keys=True))
            return 0
        if args.command=="inspect-image":
            result=inspect_w8_real_image(args.manifest,args.image,args.evidence,args.output)
            print(json.dumps({"processing_id":result["processing_id"],"source_sha256":result["source_sha256"],"source_dimensions":result["source_dimensions"],"decoder":result["decoder"],"candidate_material_regions":len(result["analysis"]["candidate_material_regions"]),"candidate_line_regions":len(result["analysis"]["candidate_line_regions"]),"artifact_count":len(result["artifacts"]),"output":str(args.output),"training_admission":"BLOCKED","benchmark_overlap":"UNRESOLVED_QUARANTINED","gold_created":False},sort_keys=True))
            return 0
        if args.command=="validate":
            acquisition=_read(args.acquisition) if args.acquisition else None;errors=validate_request(_read(args.manifest),_read(REGISTRY),args.manifest.parent,acquisition)
            if errors:raise PreprocessingError("\n".join(errors))
            print("PASS: request valid; rights and overlap gates clear; no outputs written")
        else:
            acquisition=_read(args.acquisition) if args.acquisition else None;result=run(args.manifest,args.output,acquisition);print(f"PASS: {result['dataset_version_id']} ({len(result['items'])} items)")
        return 0
    except (PreprocessingError,OSError,KeyError,TypeError,ValueError) as exc:print(f"REFUSED: {exc}",file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
