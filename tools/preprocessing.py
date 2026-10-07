"""Deterministic, dependency-free preprocessing for provenance-cleared images."""
from __future__ import annotations
import argparse, binascii, hashlib, json, math, struct, sys, zlib
from pathlib import Path
from typing import Any
import yaml
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]; SCHEMA=ROOT/"schemas/preprocessing_manifest.schema.json"; REGISTRY=ROOT/"data/sources/registry.yaml"

class PreprocessingError(ValueError): pass

def _nfc(value:str)->str:
    import unicodedata
    return unicodedata.normalize("NFC",value)
PROFILES={"identity/1.0.0":lambda value:value,"unicode-nfc/1.0.0":_nfc}

def _read(path:Path)->Any:
    try:return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,yaml.YAMLError) as exc:raise PreprocessingError(f"{path}: {exc}") from exc
def _digest(data:bytes)->str:return hashlib.sha256(data).hexdigest()

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
    data=path.read_bytes();tokens=iter(_ppm_tokens(data));header=[]
    try:
        for _ in range(4):header.append(next(tokens))
    except StopIteration as exc:raise PreprocessingError("truncated PPM header") from exc
    if header[0][0] not in {b"P3",b"P6"}:raise PreprocessingError("only P3/P6 PPM input is supported by the standard-library decoder")
    try:w,h,mx=(int(header[i][0]) for i in range(1,4))
    except ValueError as exc:raise PreprocessingError("invalid PPM dimensions/max value") from exc
    if w<1 or h<1 or not 1<=mx<=65535:raise PreprocessingError("invalid PPM dimensions or max value")
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
        elif kind==b"IDAT":compressed.extend(chunk)
        elif kind==b"IEND":ended=True;break
    if not ended or width is None:raise PreprocessingError("PNG is missing IHDR or IEND")
    channels={0:1,2:3,6:4}[color];bpp=channels;stride=width*channels
    try:raw=zlib.decompress(bytes(compressed))
    except zlib.error as exc:raise PreprocessingError(f"invalid PNG deflate stream: {exc}") from exc
    if len(raw)!=(stride+1)*height:raise PreprocessingError("PNG decompressed size does not match dimensions")
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

def main(argv=None)->int:
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest="command",required=True);check=sub.add_parser("validate");check.add_argument("manifest",type=Path);check.add_argument("--acquisition",type=Path);execute=sub.add_parser("run");execute.add_argument("manifest",type=Path);execute.add_argument("--acquisition",type=Path);execute.add_argument("--output",type=Path,required=True);args=parser.parse_args(argv)
    try:
        if args.command=="validate":
            acquisition=_read(args.acquisition) if args.acquisition else None;errors=validate_request(_read(args.manifest),_read(REGISTRY),args.manifest.parent,acquisition)
            if errors:raise PreprocessingError("\n".join(errors))
            print("PASS: request valid; rights and overlap gates clear; no outputs written")
        else:
            acquisition=_read(args.acquisition) if args.acquisition else None;result=run(args.manifest,args.output,acquisition);print(f"PASS: {result['dataset_version_id']} ({len(result['items'])} items)")
        return 0
    except (PreprocessingError,OSError,KeyError,TypeError,ValueError) as exc:print(f"REFUSED: {exc}",file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
