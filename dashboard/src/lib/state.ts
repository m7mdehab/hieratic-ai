import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
import { parse } from "yaml";

/**
 * Canonical-state loader.
 *
 * Reads the repository's canonical files at build/server time and derives
 * everything the dashboard renders. Nothing here is authoritative: all values
 * originate in PROJECT_STATE.yaml / TASKS.yaml (and, for descriptive copy only,
 * ROADMAP.md / DECISIONS.md / RESEARCH.md / EXPERIMENTS.md).
 *
 * Required canonical fields are validated strictly: a missing/malformed
 * required field throws `CanonicalStateError` instead of inventing a default.
 * Optional fields (registry previews, phase names) degrade gracefully.
 *
 * The `StateSource` interface is the seam where CTRL-002's validator can later
 * be integrated without touching the page.
 */

export class CanonicalStateError extends Error {
  constructor(message: string) {
    super(`Canonical state error: ${message}`);
    this.name = "CanonicalStateError";
  }
}

export type TaskStatus =
  | "planned"
  | "ready"
  | "active"
  | "under_review"
  | "revision_required"
  | "validated"
  | "blocked"
  | "superseded";

export interface Task {
  id: string;
  phase: string;
  title: string;
  weight: number;
  status: TaskStatus;
  ownerRole: string;
  dependsOn: string[];
  acceptanceSummary?: string;
}

export type PhaseState = "complete" | "current" | "in_progress" | "ready" | "locked";

export interface Phase {
  id: string;
  /** e.g. "P5" — derived from the canonical phase id */
  code: string;
  /** Human name from ROADMAP.md headings when available, else derived from the id */
  name: string;
  weight: number;
  earned: number;
  validatedTasks: number;
  totalTasks: number;
  state: PhaseState;
}

export interface DecisionPreview {
  id: string;
  title: string;
  status?: string;
  date?: string;
}

export interface ResearchEntry {
  id: string;
  title: string;
  status?: string;
}

export interface DashboardData {
  project: { name: string; repository: string; repositoryUrl: string; ultimateGoal?: string };
  schemaVersion: string;
  updatedAt?: string;
  progress: { goalProgress: number; goalTotal: number; researchCoverage: number };
  state: {
    currentPhase: string;
    currentPhaseLabel: string;
    currentWave: string;
    controlPlaneGate?: string;
    validatedExperiments: number;
    trainedModels?: number;
    lastAcceptedTask?: { id: string; title?: string };
    nextOverseerAction?: string;
  };
  gates: { id: string; name: string; status: string; remaining: string[] }[];
  phases: Phase[];
  tasks: Task[];
  tasksByStatus: Record<TaskStatus, Task[]>;
  /** For blocked tasks: ids of dependencies that are not yet validated. */
  unmetDependencies: Record<string, string[]>;
  research: {
    decisionCount: number;
    latestDecisions: DecisionPreview[];
    registry: ResearchEntry[];
    experimentRecords: number;
  };
}

export interface StateSource {
  load(): DashboardData;
}

export const TASK_STATUSES: TaskStatus[] = [
  "ready",
  "active",
  "under_review",
  "revision_required",
  "blocked",
  "planned",
  "validated",
  "superseded",
];

const EPSILON = 1e-6;

type Obj = Record<string, unknown>;

function isObj(v: unknown): v is Obj {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function reqObj(parent: Obj, key: string, where: string): Obj {
  const v = parent[key];
  if (!isObj(v)) throw new CanonicalStateError(`${where}.${key} must be a mapping`);
  return v;
}

function reqStr(parent: Obj, key: string, where: string): string {
  const v = parent[key];
  if (typeof v !== "string" || v.trim() === "") {
    throw new CanonicalStateError(`${where}.${key} must be a non-empty string`);
  }
  return v;
}

function reqNum(parent: Obj, key: string, where: string): number {
  const v = parent[key];
  if (typeof v !== "number" || !Number.isFinite(v)) {
    throw new CanonicalStateError(`${where}.${key} must be a finite number`);
  }
  return v;
}

function optStr(parent: Obj, key: string): string | undefined {
  const v = parent[key];
  return typeof v === "string" && v.trim() !== "" ? v.trim() : undefined;
}

function optNum(parent: Obj, key: string): number | undefined {
  const v = parent[key];
  return typeof v === "number" && Number.isFinite(v) ? v : undefined;
}

function optStrList(parent: Obj, key: string): string[] {
  const v = parent[key];
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
}

function readText(file: string): string | undefined {
  return existsSync(file) ? readFileSync(file, "utf8") : undefined;
}

function readYaml(file: string, label: string): Obj {
  const text = readText(file);
  if (text === undefined) throw new CanonicalStateError(`${label} not found at ${file}`);
  let doc: unknown;
  try {
    doc = parse(text);
  } catch (e) {
    throw new CanonicalStateError(`${label} is not valid YAML (${(e as Error).message})`);
  }
  if (!isObj(doc)) throw new CanonicalStateError(`${label} must be a YAML mapping`);
  return doc;
}

/** "P5_VLM" -> "P5"; throws on ids that do not follow the Pn_ convention. */
export function phaseCode(phaseId: string): string {
  const m = /^P(\d+)(?:_|$)/.exec(phaseId);
  if (!m) throw new CanonicalStateError(`phase id "${phaseId}" does not match P<n>_<NAME>`);
  return `P${m[1]}`;
}

function humanizePhaseId(phaseId: string): string {
  const rest = phaseId.replace(/^P\d+_?/, "");
  if (!rest) return phaseId;
  const words = rest.split("_").map((w) => (w.length <= 3 ? w : w.charAt(0) + w.slice(1).toLowerCase()));
  const s = words.join(" ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Parse "## Phase 5 - Vision-language ... - 20 points" headings (descriptive copy only). */
export function parseRoadmapPhaseNames(md: string | undefined): Record<string, string> {
  const out: Record<string, string> = {};
  if (!md) return out;
  for (const line of md.split(/\r?\n/)) {
    const m = /^##\s+Phase\s+(\d+)\s+[-–—]\s+(.+?)\s*(?:[-–—]\s*[^-–—]*points?)\s*$/i.exec(line);
    if (m) out[`P${m[1]}`] = m[2].trim();
  }
  return out;
}

export function parseDecisions(md: string | undefined): DecisionPreview[] {
  if (!md) return [];
  const lines = md.split(/\r?\n/);
  const out: DecisionPreview[] = [];
  for (let i = 0; i < lines.length; i++) {
    const m = /^##\s+(ADR-\d+)\s+[-–—]\s+(.+?)\s*$/.exec(lines[i]);
    if (!m) continue;
    const entry: DecisionPreview = { id: m[1], title: m[2] };
    for (let j = i + 1; j < lines.length && !/^##\s/.test(lines[j]); j++) {
      const s = /^\*\*Status:\*\*\s*(.+?)\s*$/.exec(lines[j]);
      const d = /^\*\*Date:\*\*\s*(.+?)\s*$/.exec(lines[j]);
      if (s) entry.status = s[1];
      if (d) entry.date = d[1];
    }
    out.push(entry);
  }
  return out;
}

export function parseResearchRegistry(md: string | undefined): ResearchEntry[] {
  if (!md) return [];
  const lines = md.split(/\r?\n/);
  const out: ResearchEntry[] = [];
  for (let i = 0; i < lines.length; i++) {
    const m = /^###\s+(R-\d+)\s+[-–—]\s+(.+?)\s*$/.exec(lines[i]);
    if (!m) continue;
    const entry: ResearchEntry = { id: m[1], title: m[2] };
    for (let j = i + 1; j < lines.length && !/^#{1,3}\s/.test(lines[j]); j++) {
      const s = /^\*\*Status:\*\*\s*(.+?)\s*$/.exec(lines[j]);
      if (s) {
        entry.status = s[1].replace(/\.$/, "");
        break;
      }
    }
    out.push(entry);
  }
  return out;
}

/** Counts real experiment records (headings like "## EXP-HTR-001"), not the template. */
export function countExperimentRecords(md: string | undefined): number {
  if (!md) return 0;
  return md.split(/\r?\n/).filter((l) => /^#{2,4}\s+EXP-[A-Z0-9]+(?:-[A-Z0-9]+)*\b/.test(l)).length;
}

function parseTasks(doc: Obj): { tasks: Task[]; phaseWeights: Record<string, number>; statusValues: string[] } {
  const phasesRaw = reqObj(doc, "phases", "TASKS.yaml");
  const phaseWeights: Record<string, number> = {};
  for (const [id, v] of Object.entries(phasesRaw)) {
    if (!isObj(v)) throw new CanonicalStateError(`TASKS.yaml.phases.${id} must be a mapping`);
    phaseWeights[id] = reqNum(v, "weight", `TASKS.yaml.phases.${id}`);
  }
  const statusValues = optStrList(doc, "status_values");
  const rawTasks = doc["tasks"];
  if (!Array.isArray(rawTasks) || rawTasks.length === 0) {
    throw new CanonicalStateError("TASKS.yaml.tasks must be a non-empty list");
  }
  const seen = new Set<string>();
  const tasks = rawTasks.map((raw, i): Task => {
    const where = `TASKS.yaml.tasks[${i}]`;
    if (!isObj(raw)) throw new CanonicalStateError(`${where} must be a mapping`);
    const id = reqStr(raw, "id", where);
    if (seen.has(id)) throw new CanonicalStateError(`duplicate task id ${id}`);
    seen.add(id);
    const phase = reqStr(raw, "phase", `${where}(${id})`);
    if (!(phase in phaseWeights)) throw new CanonicalStateError(`${id} references unknown phase ${phase}`);
    const status = reqStr(raw, "status", `${where}(${id})`);
    if (statusValues.length > 0 && !statusValues.includes(status)) {
      throw new CanonicalStateError(`${id} has status "${status}" not in status_values`);
    }
    if (!TASK_STATUSES.includes(status as TaskStatus)) {
      throw new CanonicalStateError(`${id} has unsupported status "${status}"`);
    }
    return {
      id,
      phase,
      title: reqStr(raw, "title", `${where}(${id})`),
      weight: reqNum(raw, "weight", `${where}(${id})`),
      status: status as TaskStatus,
      ownerRole: optStr(raw, "owner_role") ?? "unassigned",
      dependsOn: optStrList(raw, "depends_on"),
      acceptanceSummary: optStr(raw, "acceptance_summary"),
    };
  });
  for (const t of tasks) {
    for (const d of t.dependsOn) {
      if (!seen.has(d)) throw new CanonicalStateError(`${t.id} depends on unknown task ${d}`);
    }
  }
  return { tasks, phaseWeights, statusValues };
}

/** Pure derivation step: separated from file IO so it is directly unit-testable. */
export function deriveDashboardData(input: {
  projectState: Obj;
  tasksDoc: Obj;
  roadmapMd?: string;
  decisionsMd?: string;
  researchMd?: string;
  experimentsMd?: string;
}): DashboardData {
  const ps = input.projectState;
  const project = reqObj(ps, "project", "PROJECT_STATE.yaml");
  const progress = reqObj(ps, "progress", "PROJECT_STATE.yaml");
  const state = reqObj(ps, "state", "PROJECT_STATE.yaml");

  const goalProgress = reqNum(progress, "goal_progress", "progress");
  const goalTotal = reqNum(progress, "goal_total", "progress");
  const researchCoverage = reqNum(progress, "research_coverage", "progress");
  if (goalTotal <= 0) throw new CanonicalStateError("progress.goal_total must be > 0");
  if (goalProgress < 0 || goalProgress > goalTotal) {
    throw new CanonicalStateError("progress.goal_progress must be within 0..goal_total");
  }
  if (researchCoverage < 0 || researchCoverage > 100) {
    throw new CanonicalStateError("progress.research_coverage must be within 0..100");
  }

  const { tasks, phaseWeights } = parseTasks(input.tasksDoc);

  const currentPhase = reqStr(state, "current_phase", "state");
  if (!(currentPhase in phaseWeights)) {
    throw new CanonicalStateError(`state.current_phase "${currentPhase}" is not a phase in TASKS.yaml`);
  }
  const currentWave = reqStr(state, "current_wave", "state");
  const validatedExperiments = reqNum(state, "validated_experiments", "state");

  const names = parseRoadmapPhaseNames(input.roadmapMd);
  const phases: Phase[] = Object.entries(phaseWeights)
    .filter(([, weight]) => weight > 0)
    .map(([id, weight]): Phase => {
      const code = phaseCode(id);
      const inPhase = tasks.filter((t) => t.phase === id);
      const validated = inPhase.filter((t) => t.status === "validated");
      const earned = validated.reduce((s, t) => s + t.weight, 0);
      let pState: PhaseState;
      if (weight - earned < EPSILON) {
        pState = "complete";
      } else if (id === currentPhase) {
        pState = "current";
      } else if (earned > 0 || inPhase.some((t) => t.status === "active" || t.status === "under_review")) {
        pState = "in_progress";
      } else if (inPhase.some((t) => t.status === "ready")) {
        pState = "ready";
      } else {
        pState = "locked";
      }
      return {
        id,
        code,
        name: names[code] ?? humanizePhaseId(id),
        weight,
        earned,
        validatedTasks: validated.length,
        totalTasks: inPhase.length,
        state: pState,
      };
    })
    .sort((a, b) => Number(a.code.slice(1)) - Number(b.code.slice(1)));

  const totalWeights = phases.reduce((s, p) => s + p.weight, 0);
  if (Math.abs(totalWeights - goalTotal) > EPSILON) {
    throw new CanonicalStateError(`phase weights sum to ${totalWeights}, expected goal_total ${goalTotal}`);
  }
  const earnedTotal = phases.reduce((s, p) => s + p.earned, 0);
  if (Math.abs(earnedTotal - goalProgress) > EPSILON) {
    throw new CanonicalStateError(
      `progress.goal_progress (${goalProgress}) disagrees with validated task weights in TASKS.yaml (${earnedTotal})`,
    );
  }

  const tasksByStatus = Object.fromEntries(TASK_STATUSES.map((s) => [s, [] as Task[]])) as Record<TaskStatus, Task[]>;
  for (const t of tasks) tasksByStatus[t.status].push(t);

  const byId = new Map(tasks.map((t) => [t.id, t]));
  const unmetDependencies: Record<string, string[]> = {};
  for (const t of tasks) {
    if (t.status === "validated") continue;
    const unmet = t.dependsOn.filter((d) => byId.get(d)?.status !== "validated");
    if (unmet.length > 0) unmetDependencies[t.id] = unmet;
  }

  const repository = reqStr(project, "repository", "project");
  const lastAcceptedId = optStr(state, "last_accepted_task");
  const decisions = parseDecisions(input.decisionsMd);

  return {
    project: {
      name: reqStr(project, "name", "project"),
      repository,
      repositoryUrl: `https://github.com/${repository}`,
      ultimateGoal: optStr(project, "ultimate_goal"),
    },
    schemaVersion: reqStr(ps, "schema_version", "PROJECT_STATE.yaml"),
    updatedAt: optStr(ps, "updated_at"),
    progress: { goalProgress, goalTotal, researchCoverage },
    state: {
      currentPhase,
      currentPhaseLabel: phases.find((p) => p.id === currentPhase)?.name ?? humanizePhaseId(currentPhase),
      currentWave,
      controlPlaneGate: optStr(state, "control_plane_gate"),
      validatedExperiments,
      trainedModels: optNum(state, "trained_models"),
      lastAcceptedTask: lastAcceptedId
        ? { id: lastAcceptedId, title: byId.get(lastAcceptedId)?.title }
        : undefined,
      nextOverseerAction: optStr(ps, "next_overseer_action")?.replace(/\s+/g, " "),
    },
    gates: (Array.isArray(ps["critical_gates"]) ? (ps["critical_gates"] as unknown[]) : [])
      .filter(isObj)
      .map((g) => ({
        id: optStr(g, "id") ?? "",
        name: optStr(g, "name") ?? "",
        status: optStr(g, "status") ?? "unknown",
        remaining: optStrList(g, "remaining"),
      }))
      .filter((g) => g.id !== ""),
    phases,
    tasks,
    tasksByStatus,
    unmetDependencies,
    research: {
      decisionCount: decisions.length,
      latestDecisions: decisions.slice(-3).reverse(),
      registry: parseResearchRegistry(input.researchMd),
      experimentRecords: countExperimentRecords(input.experimentsMd),
    },
  };
}

/** Resolve the repository root: DASHBOARD_REPO_ROOT, else the parent of `dashboard/`. */
export function resolveRepoRoot(cwd: string = process.cwd()): string {
  const fromEnv = process.env.DASHBOARD_REPO_ROOT;
  if (fromEnv) return path.resolve(fromEnv);
  return path.resolve(cwd, "..");
}

export class RepoFileStateSource implements StateSource {
  constructor(private readonly root: string = resolveRepoRoot()) {}

  load(): DashboardData {
    const r = (f: string) => path.join(this.root, f);
    return deriveDashboardData({
      projectState: readYaml(r("PROJECT_STATE.yaml"), "PROJECT_STATE.yaml"),
      tasksDoc: readYaml(r("TASKS.yaml"), "TASKS.yaml"),
      roadmapMd: readText(r("ROADMAP.md")),
      decisionsMd: readText(r("DECISIONS.md")),
      researchMd: readText(r("RESEARCH.md")),
      experimentsMd: readText(r("EXPERIMENTS.md")),
    });
  }
}

/** Single entry point for pages. Swap the source here to add CTRL-002 validation later. */
export function loadDashboardData(source: StateSource = new RepoFileStateSource()): DashboardData {
  return source.load();
}

export function formatPoints(n: number): string {
  return Number.isInteger(n) ? String(n) : String(Number(n.toFixed(2)));
}
