/**
 * Offline, pinned ORIGINAL HieraticBench scoring of PUBLIC identify/signs items.
 *
 * Run with Node 22 + tsx installed in the pinned upstream checkout, e.g.
 * (cd /private/hieraticbench && node --import tsx /path/to/hieratic-ai/eval/baselines/official_replay.mjs ...)
 *
 * This does not make provider calls, load images or private sealed answers,
 * train models, or publish gold/predictions. Outputs aggregate statistics only.
 *
 * A valid JSON receipt is NOT an independently authenticated experiment.
 */
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

const project = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const PINNED = "d587dc990013f18007f1e7a8f56f96ff2f7127e2";
const RUNG_COUNTS = Object.freeze({identify: 116, signs: 150});
const requiredCapture = ["item_id","rung","sample_index","provider_model_id","prompt_sha256",
  "status","response_text","provider_response_id","timestamp"];
const requiredAttempts = ["item_id","rung","sample_index","model_key","prompt_path",
  "prompt_sha256","image_path","image_sha256"];
const sha = x => crypto.createHash("sha256").update(x).digest("hex");
const fail = msg => {throw new Error(msg)};
const asExact = (obj,fields,label) => {
  if (!obj || typeof obj!=="object" || Array.isArray(obj) ||
      Object.keys(obj).sort().join("|")!==[...fields].sort().join("|")) fail(`${label}: invalid or unexpected fields`);
};
const jsonFile = f => JSON.parse(fs.readFileSync(f,"utf8"));
const shaFile = f => sha(fs.readFileSync(f));
const iso = v => typeof v==="string" && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(v) && !Number.isNaN(Date.parse(v));
function secureFile(f,label) {
  const resolved=fs.realpathSync(f);
  if (resolved===project || resolved.startsWith(project+path.sep) || !fs.statSync(resolved).isFile())
    fail(`${label} must be a private external regular file`);
  return resolved;
}
function secureOutputDir(f) {
  const resolved=fs.realpathSync(f);
  if (resolved===project || resolved.startsWith(project+path.sep) || !fs.statSync(resolved).isDirectory())
    fail("Output directory must already exist outside the public repository");
  if (fs.lstatSync(f).isSymbolicLink()) fail("Output directory symlink prohibited");
  return resolved;
}
function readJsonl(f,label,required) {
  const data=fs.readFileSync(secureFile(f,label),"utf8");
  if(!data || !data.endsWith("\n")) fail(`${label} must be nonempty newline-terminated JSONL`);
  const lines=data.slice(0,-1).split("\n");
  if(lines.length>20000) fail(`${label}: record count cap exceeded`);
  return lines.map((line,index)=>{
    let obj;try{obj=JSON.parse(line)}catch{fail(`${label} line ${index+1}: invalid JSON`)}
    asExact(obj,required,`${label} line ${index+1}`);
    return obj;
  });
}
const flags=new Map();
for(let i=2;i<process.argv.length;i++){
  const arg=process.argv[i];
  if (!arg.startsWith("--") || flags.has(arg) || i+1>=process.argv.length) fail("Expected distinct --key value arguments");
  flags.set(arg,process.argv[++i]);
}
const get=k=>{if(!flags.has(k))fail(`Missing argument ${k}`);return flags.get(k)};
const allowed=new Set(["--checkout","--capture","--receipt","--freeze","--items",
  "--attempts","--output-dir","--self-test"]);
for(const k of flags.keys())if(!allowed.has(k))fail(`Unknown argument ${k}`);

const checkout=path.resolve(get("--checkout"));
const git=execFileSync("git",["-C",checkout,"rev-parse","HEAD"],{encoding:"utf8"}).trim();
if(git!==PINNED)fail("Upstream scorer checkout not at the EVAL-002 pinned SHA");
const scoreSrc=path.join(checkout,"bench/src/score.ts");
const promptsSrc=path.join(checkout,"bench/src/prompts.ts");
if(!fs.existsSync(scoreSrc)||!fs.existsSync(promptsSrc))fail("Missing pinned original official scorer/prompt source");
const {scoreResponse}=await import(pathToFileURL(scoreSrc).href);

if(flags.has("--self-test")){
  const v1=scoreResponse({id:"synthetic",split:"public",rungs:["identify"],script:"hieratic"}, "identify","SCRIPT: hieratic",undefined);
  const v2=scoreResponse({id:"synthetic",split:"public",rungs:["signs"],gardiner:["G17"]}, "signs","SIGNS: G17",undefined);
  const v3=scoreResponse({id:"synthetic",split:"public",rungs:["signs"],gardiner:["G17"]}, "signs","SIGNS: Q1",undefined);
  if(v1?.score!==1||v2?.score!==1||v3?.score!==0)fail("Official original scorer synthetic parity failed");
  console.log("PASS: original upstream scorer imported directly and synthetic identify/sign scores verified");
  process.exit(0);
}
const archive=secureFile(get("--capture"),"Raw provider response archive");
const receipt=jsonFile(secureFile(get("--receipt"),"Capture receipt"));
const freeze=jsonFile(secureFile(get("--freeze"),"Frozen run preregistration"));
const itemRows=readJsonl(get("--items"),"Public item/rung manifest",["item_id","rung","split"]);
const attemptRows=readJsonl(get("--attempts"),"Frozen rendered attempt manifest",requiredAttempts);
const responseRows=readJsonl(archive,"Raw provider response archive",requiredCapture);
const outputDir=secureOutputDir(get("--output-dir"));

if(freeze.state!=="locked"||freeze.official_benchmark_commit!==PINNED ||
  freeze.scorer_source_sha256!==shaFile(scoreSrc)||
  freeze.official_prompt_source_sha256!==shaFile(promptsSrc)||
  freeze.public_item_manifest_sha256!==shaFile(get("--items"))||
  freeze.prompt_attempts_manifest_sha256!==shaFile(get("--attempts")))
  fail("Not a matching locked scorer/prompt/public-manifest/run freeze");
if(receipt.schema_version!=="1.0.0"||receipt.state!=="captured"||
  receipt.run_id!==freeze.run_id||receipt.provider_model_id!==freeze.provider_model_id||
  receipt.model_key!==freeze.model_key||receipt.capture_sha256!==shaFile(archive)||
  receipt.rendered_attempts_sha256!==shaFile(get("--attempts")))
  fail("Private capture receipt/hash/identity mismatch");
if(receipt.records_expected!==freeze.attempts_planned||responseRows.length!==receipt.records_expected)
  fail("Incomplete capture receipt or missing raw attempt records");
const itemsDir=path.join(checkout,"data/items");
const items=new Map();
for(const file of fs.readdirSync(itemsDir).filter(x=>x.endsWith(".json"))){
  const item=jsonFile(path.join(itemsDir,file));
  if(item.id!==file.slice(0,-5)||items.has(item.id))fail("Bad upstream item identities");
  items.set(item.id,item);
}
if(items.size!==268)fail("Pinned upstream inventory count changed");
const expected=new Map();
const seenRung=new Set();
const rungItems={identify:new Set(),signs:new Set()};
for(const r of itemRows){
  if(r.split!=="public"||!Object.hasOwn(RUNG_COUNTS,r.rung)||typeof r.item_id!=="string")
    fail("A sealed/nonpublic/unsupported item entered the manifest");
  const item=items.get(r.item_id);
  if(!item||item.split!=="public"||!item.rungs.includes(r.rung)||
    (r.rung==="signs"&&!Array.isArray(item.gardiner))) fail("Unapproved upstream item/rung or missing public gold");
  const token=`${r.item_id}|${r.rung}`;
  if(seenRung.has(token))fail("Duplicate frozen public item/rung");
  seenRung.add(token);rungItems[r.rung].add(r.item_id);
}
for(const [r,n] of Object.entries(RUNG_COUNTS))if(rungItems[r].size!==n)fail(`Unexpected ${r} population`);
if(itemRows.length!==266)fail("Not the complete predeclared public item/rung set");
for(const r of attemptRows){
  if(typeof r.sample_index!=="number"||!Number.isInteger(r.sample_index)||
    r.sample_index<0||r.sample_index>=freeze.samples_per_item||
    r.model_key!==freeze.model_key||!seenRung.has(`${r.item_id}|${r.rung}`))
    fail("Unplanned/invalid frozen prompt attempt");
  const key=`${r.item_id}|${r.rung}|${r.sample_index}`;
  if(expected.has(key))fail("Duplicate frozen prompt attempt");
  expected.set(key,r.prompt_sha256);
}
if(expected.size!==266*freeze.samples_per_item||freeze.attempts_planned!==expected.size)
  fail("Frozen run is not a complete 266-item/rung attempt schedule");

const seen=new Set();
const perItem=new Map();
const categories={identify:{ok:0,failed:0,abstained:0,timeout:0,refused:0},
  signs:{ok:0,failed:0,abstained:0,timeout:0,refused:0}};
for(const r of responseRows){
  const key=`${r.item_id}|${r.rung}|${r.sample_index}`;
  if(!expected.has(key)||seen.has(key))fail("Duplicate/unplanned provider response attempt");
  seen.add(key);
  if(r.provider_model_id!==freeze.provider_model_id||r.prompt_sha256!==expected.get(key))
    fail("Response provider/prompt differs from exact locked attempt");
  if(!Object.hasOwn(categories[r.rung],r.status)||typeof r.response_text!=="string"||
    (r.status==="ok"&&(!r.response_text||!r.provider_response_id))||!iso(r.timestamp))
    fail("Response status, timestamp, receipt or raw text invalid");
  const scored = r.status==="ok" ?
    scoreResponse(items.get(r.item_id),r.rung,r.response_text,undefined) : null;
  if(r.status==="ok"&&(!scored||!Number.isFinite(scored.score)||scored.score<0||scored.score>1))
    fail("Upstream original score unexpectedly missing/invalid for a public response");
  const group=`${r.item_id}|${r.rung}`;
  const row=perItem.get(group)||{item_id:r.item_id,rung:r.rung,official:[],intent:[]};
  if(scored)row.official.push(scored.score);
  row.intent.push(scored ? scored.score : 0);
  perItem.set(group,row);
  categories[r.rung][r.status]++;
}
if(seen.size!==expected.size)fail("Incomplete response attempts cannot disappear from denominator");
const mean=v=>v.reduce((a,b)=>a+b,0)/v.length;
const summaries={};
for(const [rung,population] of Object.entries(RUNG_COUNTS)){
  const groups=[...perItem.values()].filter(x=>x.rung===rung);
  if(groups.length!==population)fail("Missing planned item group");
  const scored=groups.filter(x=>x.official.length);
  const c=categories[rung];
  summaries[rung]={
    official_upstream_scored_sample_item_macro:scored.length?mean(scored.map(g=>mean(g.official))):null,
    official_scored_items:scored.length,
    official_scored_samples:scored.reduce((a,g)=>a+g.official.length,0),
    official_item_coverage:scored.length/population,
    scheduled_items:population,
    scheduled_attempts:population*freeze.samples_per_item,
    statuses:c,
    intention_to_test_zero_for_failed_macro:mean(groups.map(g=>mean(g.intent))),
  };
}
const report={
  schema_version:"1.0.0",report_type:"private_inputs_to_public_aggregate_no_authentication",
  evaluation_id:freeze.run_id,upstream_commit:PINNED,official_scorer_sha256:shaFile(scoreSrc),
  public_item_manifest_sha256:shaFile(get("--items")),raw_capture_sha256:shaFile(archive),
  model_key:freeze.model_key,provider_model_id:freeze.provider_model_id,
  rung_aggregates:summaries,
  note:"Replays pinned original scorer in memory. Scores are not independently validated provider experiments. No gold, per-item scores, parsed answers, response text, or images exported.",
  original_provider_calls_authenticated:false,
  independently_accepted_result:false,
};
const file=path.join(outputDir,`original-scores-${freeze.run_id}.json`);
const fd=fs.openSync(file,"wx",0o600);
try{fs.writeFileSync(fd,JSON.stringify(report,null,2)+"\n")}finally{fs.closeSync(fd)}
console.log(JSON.stringify({status:"pass",report_path:file,provider_calls_authenticated:false,
  metrics:"original scorer per-rung aggregates only; no answer/gold export"}));
