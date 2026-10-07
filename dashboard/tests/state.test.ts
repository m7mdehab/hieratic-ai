import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, copyFileSync, readFileSync, writeFileSync, rmSync, readdirSync, statSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { parse } from "yaml";
import {
  RepoFileStateSource,
  loadDashboardData,
  deriveDashboardData,
  parseRoadmapPhaseNames,
  parseDecisions,
  parseResearchRegistry,
  countExperimentRecords,
  CanonicalStateError,
  formatPoints,
} from "../src/lib/state";

const REPO_ROOT = path.resolve(__dirname, "..", "..");
const CANON = ["PROJECT_STATE.yaml", "TASKS.yaml", "ROADMAP.md", "DECISIONS.md", "RESEARCH.md", "EXPERIMENTS.md"];

describe("real canonical repository state", () => {
  const data = loadDashboardData(new RepoFileStateSource(REPO_ROOT));
  const ps = parse(readFileSync(path.join(REPO_ROOT, "PROJECT_STATE.yaml"), "utf8"));

  it("surfaces progress values exactly as stored in PROJECT_STATE.yaml", () => {
    expect(data.progress.goalProgress).toBe(ps.progress.goal_progress);
    expect(data.progress.researchCoverage).toBe(ps.progress.research_coverage);
    expect(data.state.validatedExperiments).toBe(ps.state.validated_experiments);
    expect(data.state.currentWave).toBe(ps.state.current_wave);
  });

  it("derives per-phase earned points from validated task weights and they sum to goal progress", () => {
    const earned = data.phases.reduce((s, p) => s + p.earned, 0);
    expect(earned).toBeCloseTo(data.progress.goalProgress, 6);
    const weights = data.phases.reduce((s, p) => s + p.weight, 0);
    expect(weights).toBeCloseTo(data.progress.goalTotal, 6);
  });

  it("lists P1..P8 with phases correctly partitioned across complete, current, in_progress, ready, and locked", () => {
    expect(data.phases.map((p) => p.code)).toEqual(["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]);
    const current = data.phases.filter((p) => p.state === "current");
    expect(current.map((p) => p.id)).toEqual([ps.state.current_phase]);
    expect(data.phases.every((p) => p.name.length > 0)).toBe(true);

    const p1 = data.phases.find((p) => p.code === "P1")!;
    expect(p1.state).toBe("complete");
    const p2 = data.phases.find((p) => p.code === "P2")!;
    expect(p2.state).toBe("current");
    const p3 = data.phases.find((p) => p.code === "P3")!;
    expect(p3.state).toBe("in_progress");
  });

  it("groups tasks by status and covers every task exactly once", () => {
    const total = Object.values(data.tasksByStatus).reduce((s, l) => s + l.length, 0);
    expect(total).toBe(data.tasks.length);
    const ready = data.tasksByStatus.ready.map((t) => t.id);
    for (const id of ps.state.ready_tasks as string[]) {
      // overseer-owned and execution tasks alike must agree with state.ready_tasks
      expect(ready).toContain(id);
    }
  });

  it("reports unmet dependencies only for non-validated tasks", () => {
    for (const [id, deps] of Object.entries(data.unmetDependencies)) {
      expect(data.tasks.find((t) => t.id === id)?.status).not.toBe("validated");
      expect(deps.length).toBeGreaterThan(0);
    }
  });
});

describe("canonical file changes propagate to derived data (fixture)", () => {
  let dir: string;
  beforeEach(() => {
    dir = mkdtempSync(path.join(tmpdir(), "dash-fixture-"));
    for (const f of CANON) copyFileSync(path.join(REPO_ROOT, f), path.join(dir, f));
  });
  afterEach(() => rmSync(dir, { recursive: true, force: true }));

  it("changing research coverage in PROJECT_STATE.yaml changes the rendered value", () => {
    const f = path.join(dir, "PROJECT_STATE.yaml");
    writeFileSync(f, readFileSync(f, "utf8").replace(/research_coverage:\s*[\d.]+/, "research_coverage: 37.5"));
    const d = new RepoFileStateSource(dir).load();
    expect(d.progress.researchCoverage).toBe(37.5);
  });

  it("validating a task in TASKS.yaml (with matching goal_progress) changes phase points and grouping", () => {
    const tf = path.join(dir, "TASKS.yaml");
    const sf = path.join(dir, "PROJECT_STATE.yaml");
    const before = new RepoFileStateSource(dir).load();
    const candidate = before.tasks.find((t) => t.status !== "validated" && t.weight > 0)!;
    expect(candidate).toBeDefined();

    const tasksDoc = parse(readFileSync(tf, "utf8"));
    const taskEntry = (tasksDoc.tasks as Array<{ id: string; status: string }>).find((t) => t.id === candidate.id)!;
    taskEntry.status = "validated";
    writeFileSync(tf, JSON.stringify(tasksDoc));

    const stateDoc = parse(readFileSync(sf, "utf8"));
    stateDoc.progress.goal_progress = Number((stateDoc.progress.goal_progress + candidate.weight).toFixed(2));
    writeFileSync(sf, JSON.stringify(stateDoc));

    const after = new RepoFileStateSource(dir).load();
    expect(after.progress.goalProgress).toBeCloseTo(before.progress.goalProgress + candidate.weight, 6);
    expect(after.tasksByStatus.validated.map((t) => t.id)).toContain(candidate.id);
    expect(after.tasksByStatus[candidate.status].map((t) => t.id)).not.toContain(candidate.id);
    const phaseBefore = before.phases.find((p) => p.id === candidate.phase)!;
    const phaseAfter = after.phases.find((p) => p.id === candidate.phase)!;
    expect(phaseAfter.earned).toBeCloseTo(phaseBefore.earned + candidate.weight, 6);
  });

  it("fails visibly when goal_progress disagrees with validated task weights", () => {
    const sf = path.join(dir, "PROJECT_STATE.yaml");
    writeFileSync(sf, readFileSync(sf, "utf8").replace(/goal_progress:\s*[\d.]+/, "goal_progress: 9"));
    expect(() => new RepoFileStateSource(dir).load()).toThrow(CanonicalStateError);
  });

  it("fails visibly when a required field is missing", () => {
    const sf = path.join(dir, "PROJECT_STATE.yaml");
    writeFileSync(sf, readFileSync(sf, "utf8").replace(/^[ \t]*current_wave:[^\r\n]*\r?\n/m, ""));
    expect(() => new RepoFileStateSource(dir).load()).toThrow(/current_wave/);
  });

  it("fails visibly when a canonical file is missing", () => {
    rmSync(path.join(dir, "TASKS.yaml"));
    expect(() => new RepoFileStateSource(dir).load()).toThrow(/TASKS.yaml not found/);
  });

  it("degrades gracefully when optional markdown/fields are absent", () => {
    for (const f of ["ROADMAP.md", "DECISIONS.md", "RESEARCH.md", "EXPERIMENTS.md"]) rmSync(path.join(dir, f));
    const sf = path.join(dir, "PROJECT_STATE.yaml");
    writeFileSync(
      sf,
      readFileSync(sf, "utf8").replace(/\r?\nnext_overseer_action:[\s\S]*$/, "\n").replace(/^[ \t]*last_accepted_task:[^\r\n]*\r?\n/m, ""),
    );
    const d = new RepoFileStateSource(dir).load();
    expect(d.research.latestDecisions).toEqual([]);
    expect(d.research.registry).toEqual([]);
    expect(d.state.nextOverseerAction).toBeUndefined();
    expect(d.state.lastAcceptedTask).toBeUndefined();
    expect(d.phases.every((p) => p.name.length > 0)).toBe(true);
  });
});

describe("pure derivation edge cases", () => {
  const baseState = {
    schema_version: "x",
    project: { name: "N", repository: "o/r" },
    progress: { goal_progress: 1, goal_total: 10, research_coverage: 5 },
    state: { current_phase: "P1_A", current_wave: "W0", validated_experiments: 0 },
  };
  const baseTasks = {
    phases: { P0_CTRL: { weight: 0 }, P1_A: { weight: 4 }, P2_B: { weight: 6 } },
    tasks: [
      { id: "A-1", phase: "P1_A", title: "a", weight: 1, status: "validated", depends_on: [] },
      { id: "B-1", phase: "P2_B", title: "b", weight: 6, status: "blocked", depends_on: ["A-1", "A-2"] },
      { id: "A-2", phase: "P1_A", title: "c", weight: 3, status: "ready", depends_on: ["A-1"] },
    ],
  };

  it("derives states, unmet dependencies and complete/locked phases", () => {
    const d = deriveDashboardData({ projectState: baseState, tasksDoc: baseTasks });
    expect(d.phases.map((p) => [p.code, p.earned, p.state])).toEqual([
      ["P1", 1, "current"],
      ["P2", 0, "locked"],
    ]);
    expect(d.unmetDependencies).toEqual({ "B-1": ["A-2"] });
  });

  it("rejects unknown dependency, unknown status and bad current phase", () => {
    const bad = (mut: (t: typeof baseTasks) => void, s = baseState) => {
      const t = structuredClone(baseTasks);
      mut(t);
      return () => deriveDashboardData({ projectState: s, tasksDoc: t });
    };
    expect(bad((t) => (t.tasks[0].depends_on = ["ZZZ"]))).toThrow(/unknown task/);
    expect(bad((t) => (t.tasks[0].status = "done"))).toThrow(/unsupported status|status_values/);
    expect(
      bad(() => undefined, { ...baseState, state: { ...baseState.state, current_phase: "P9_X" } }),
    ).toThrow(/current_phase/);
  });

  it("does not invent defaults for required numeric fields", () => {
    const s = structuredClone(baseState) as unknown as { progress: Record<string, unknown> };
    delete s.progress.research_coverage;
    expect(() => deriveDashboardData({ projectState: s, tasksDoc: baseTasks })).toThrow(/research_coverage/);
  });
});

describe("markdown preview parsers", () => {
  it("parses roadmap phase names from headings", () => {
    const names = parseRoadmapPhaseNames(
      "## Phase 0 - Project control plane - mandatory gate, 0 points\n## Phase 5 - Vision-language adaptation - 20 points\n",
    );
    expect(names.P5).toBe("Vision-language adaptation");
    expect(names.P0).toBe("Project control plane");
  });

  it("parses decisions, registry entries and experiment records", () => {
    const d = parseDecisions("## ADR-0001 — A\n\n**Status:** Accepted  \n**Date:** 2026-01-01\n\n## ADR-0002 — B\n");
    expect(d).toEqual([
      { id: "ADR-0001", title: "A", status: "Accepted", date: "2026-01-01" },
      { id: "ADR-0002", title: "B" },
    ]);
    expect(parseResearchRegistry("### R-001 — T\n\n**Status:** CANDIDATE / x.\n")).toEqual([
      { id: "R-001", title: "T", status: "CANDIDATE / x" },
    ]);
    expect(countExperimentRecords("## Template\nid: EXP-...\n## EXP-HTR-001\n### EXP-HTR-002 x\n")).toBe(2);
  });

  it("formats points without float noise", () => {
    expect(formatPoints(2.5)).toBe("2.5");
    expect(formatPoints(14)).toBe("14");
    expect(formatPoints(0.1 + 0.2)).toBe("0.3");
  });
});

describe("no duplicated canonical constants / no second state source", () => {
  const srcDir = path.resolve(__dirname, "..", "src");
  const walk = (d: string): string[] =>
    readdirSync(d).flatMap((n) => {
      if (n === "node_modules" || n === ".next" || n === "screenshots") return [];
      const p = path.join(d, n);
      return statSync(p).isDirectory() ? walk(p) : [p];
    });
  const files = walk(srcDir).filter((f) => /\.(ts|tsx)$/.test(f));
  const ps = parse(readFileSync(path.join(REPO_ROOT, "PROJECT_STATE.yaml"), "utf8"));

  it("source contains no numeric literal equal to current goal progress or research coverage", () => {
    const needles = [ps.progress.goal_progress, ps.progress.research_coverage].flatMap((n: number) => [
      String(n),
      n.toFixed(1),
    ]);
    const unique = [...new Set(needles)];
    const hits: string[] = [];
    for (const f of files) {
      const text = readFileSync(f, "utf8");
      for (const n of unique) {
        // standalone numeric token (not part of identifiers/other numbers such as 0.25 or 14ch)
        const re = new RegExp(`(?<![\\w.])${n.replace(".", "\\.")}(?![\\w.]|\\d)`, "g");
        if (re.test(text)) hits.push(`${path.relative(srcDir, f)}: ${n}`);
      }
    }
    expect(hits).toEqual([]);
  });

  it("source never hard-codes the canonical task ids or counts of current work", () => {
    const hits = files.filter((f) => /["'`](CTRL|FND|EVAL|DATA|SPEC|VLM|LING|GEN|REL)-\d{3}["'`]/.test(readFileSync(f, "utf8")));
    expect(hits).toEqual([]);
  });

  it("dashboard has no hand-maintained project JSON state file", () => {
    const dashRoot = path.resolve(__dirname, "..");
    expect(existsSync(path.join(dashRoot, "data", "project.json"))).toBe(false);
    const jsons = walk(dashRoot)
      .filter((f) => !f.includes("node_modules") && !f.includes(`${path.sep}.next${path.sep}`))
      .filter((f) => f.endsWith(".json"))
      .map((f) => path.basename(f));
    expect(jsons.sort()).toEqual(["package-lock.json", "package.json", "tsconfig.json"].sort());
  });
});
