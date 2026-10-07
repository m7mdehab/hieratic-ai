import {
  loadDashboardData,
  formatPoints,
  type DashboardData,
  type Task,
  type TaskStatus,
} from "@/lib/state";

const STATUS_LABEL: Record<TaskStatus, string> = {
  ready: "Ready",
  active: "Active",
  under_review: "Under review",
  revision_required: "Revision required",
  blocked: "Blocked",
  planned: "Planned",
  validated: "Validated",
  superseded: "Superseded",
};

/** Prominent groups; empty ones still render so absence of work is explicit. */
const PRIMARY_GROUPS: TaskStatus[] = ["ready", "active", "under_review"];
/** Collapsed archive groups; hidden when empty. */
const ARCHIVE_GROUPS: TaskStatus[] = ["revision_required", "blocked", "planned", "validated", "superseded"];

function humanizeId(id: string): string {
  const [head, ...rest] = id.split("_");
  const tail = rest.join(" ").toLowerCase();
  return tail ? `${head} · ${tail.charAt(0).toUpperCase()}${tail.slice(1)}` : head;
}

function pct(n: number, total: number): number {
  return total > 0 ? Math.max(0, Math.min(100, (n / total) * 100)) : 0;
}

function Meter({ value, total, label, thin = false }: { value: number; total: number; label: string; thin?: boolean }) {
  const width = pct(value, total);
  return (
    <div
      className={thin ? "thin-meter" : "meter"}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={total}
      aria-valuenow={value}
      aria-valuetext={`${formatPoints(value)} of ${formatPoints(total)}`}
    >
      {thin ? <span style={{ width: `${width}%` }} /> : <div className="meter-fill" style={{ width: `${width}%` }} />}
    </div>
  );
}

function TaskList({ tasks, data, showDeps = false }: { tasks: Task[]; data: DashboardData; showDeps?: boolean }) {
  return (
    <ul className="queue">
      {tasks.map((t) => {
        const unmet = data.unmetDependencies[t.id];
        return (
          <li key={t.id}>
            <span className="task-id">{t.id}</span>
            <span className="task-title">{t.title}</span>
            <span className="task-sub">
              {t.phase.split("_")[0]} · {t.ownerRole.replace(/_/g, " ")} · {formatPoints(t.weight)} pts
              {showDeps && unmet ? ` · waiting on ${unmet.join(", ")}` : ""}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export default function Home() {
  const data = loadDashboardData();
  const { progress, state, project } = data;
  const remaining = progress.goalTotal - progress.goalProgress;
  const repo = project.repositoryUrl;
  const lastAccepted = state.lastAcceptedTask;

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <div className="page">
        <header className="masthead">
          <span className="wordmark">{project.name}</span>
          <nav aria-label="Sections">
            <ul>
              <li><a href="#state">State</a></li>
              <li><a href="#roadmap">Roadmap</a></li>
              <li><a href="#tasks">Tasks</a></li>
              <li><a href="#research">Research</a></li>
              <li><a href="#method">Method</a></li>
            </ul>
          </nav>
        </header>

        <main id="main">
          <section className="identity" aria-labelledby="identity-title">
            <p className="eyebrow">Open research program</p>
            <h1 id="identity-title">{project.name}</h1>
            <p className="lede">Teaching multimodal AI to read ancient Egyptian Hieratic.</p>
            <p className="links">
              <a href={repo}>{project.repository} on GitHub</a>
              <a href={`${repo}/blob/main/START_HERE.md`}>How the project is run</a>
            </p>
          </section>

          <section className="section" id="state" aria-labelledby="state-title">
            <div className="section-head">
              <p className="eyebrow">Primary state</p>
              <h2 id="state-title">Where the program stands</h2>
              <p>
                Read from <code>PROJECT_STATE.yaml</code> and <code>TASKS.yaml</code>
                {data.updatedAt ? `, state dated ${data.updatedAt}` : ""}.
              </p>
            </div>
            <div className="state">
              <div className="state-primary">
                <p className="eyebrow">Verified goal progress</p>
                <p className="numeral numeral-hero">
                  {formatPoints(progress.goalProgress)}
                  <small>%</small>
                </p>
                <Meter
                  value={progress.goalProgress}
                  total={progress.goalTotal}
                  label={`Verified goal progress: ${formatPoints(progress.goalProgress)} of ${formatPoints(progress.goalTotal)} points`}
                />
                <p className="caption">
                  {formatPoints(remaining)} of {formatPoints(progress.goalTotal)} capability points remain. Only
                  overseer-validated milestones are counted.
                </p>
              </div>
              <dl className="facts">
                <div>
                  <dt>Research coverage</dt>
                  <dd className="numeral numeral-md">
                    {formatPoints(progress.researchCoverage)}
                    <small>%</small>
                  </dd>
                </div>
                <div>
                  <dt>Capability phase</dt>
                  <dd>{state.currentPhaseLabel}</dd>
                </div>
                <div>
                  <dt>Control-plane wave</dt>
                  <dd>{humanizeId(state.currentWave)}</dd>
                </div>
                <div>
                  <dt>Validated experiments</dt>
                  <dd className="numeral numeral-md">{state.validatedExperiments}</dd>
                </div>
              </dl>
            </div>
            <p className="caption" style={{ marginTop: "var(--space-4)", color: "var(--ink-muted)", maxWidth: "62ch" }}>
              Research coverage is how much of the planned search space has been investigated. It can rise without any
              gain in goal progress.
            </p>
          </section>

          <section className="section" id="roadmap" aria-labelledby="roadmap-title">
            <div className="section-head">
              <p className="eyebrow">Capability roadmap</p>
              <h2 id="roadmap-title">
                {data.phases.length} phases, {formatPoints(progress.goalTotal)} points
              </h2>
              <p>Points are earned only by validated capability milestones. Later phases stay locked until their dependencies are met.</p>
            </div>
            <ol className="ledger">
              {data.phases.map((p) => (
                <li key={p.id} data-state={p.state} aria-current={p.state === "current" ? "step" : undefined}>
                  <span className="code">{p.code}</span>
                  <span className="row-body name">{p.name}</span>
                  <span className="row-meta">
                    <Meter
                      thin
                      value={p.earned}
                      total={p.weight}
                      label={`${p.code} ${p.name}: ${formatPoints(p.earned)} of ${formatPoints(p.weight)} points earned`}
                    />
                    <span className="points">
                      {formatPoints(p.earned)} / {formatPoints(p.weight)} pts
                    </span>
                  </span>
                  <span className="phase-state">
                    {p.state === "current"
                      ? "Current"
                      : p.state === "complete"
                      ? "Complete"
                      : p.state === "in_progress"
                      ? "In progress"
                      : p.state === "ready"
                      ? "Ready"
                      : "Locked"}
                  </span>
                </li>
              ))}
            </ol>
          </section>

          <section className="section" id="tasks" aria-labelledby="tasks-title">
            <div className="section-head">
              <p className="eyebrow">Task operations</p>
              <h2 id="tasks-title">What can move now</h2>
              <p>
                {data.tasks.length} tasks in the dependency graph. Grouped by lifecycle status from <code>TASKS.yaml</code>.
              </p>
            </div>
            <div className="task-groups">
              {PRIMARY_GROUPS.map((s) => {
                const list = data.tasksByStatus[s];
                return (
                  <div key={s}>
                    <div className="group-title">
                      <h3>{STATUS_LABEL[s]}</h3>
                      <span className="count">{list.length}</span>
                    </div>
                    {list.length > 0 ? <TaskList tasks={list} data={data} /> : <p className="empty">None right now.</p>}
                  </div>
                );
              })}
              <div className="archive">
                {ARCHIVE_GROUPS.filter((s) => data.tasksByStatus[s].length > 0).map((s) => (
                  <details key={s}>
                    <summary>
                      {STATUS_LABEL[s]} <span className="count">{data.tasksByStatus[s].length}</span>
                    </summary>
                    <TaskList tasks={data.tasksByStatus[s]} data={data} showDeps={s === "blocked"} />
                  </details>
                ))}
              </div>
            </div>
          </section>

          <section className="section" id="research" aria-labelledby="research-title">
            <div className="section-head">
              <p className="eyebrow">Research activity</p>
              <h2 id="research-title">Decisions, evidence, experiments</h2>
            </div>
            <div className="research">
              <div>
                <h3>Latest decisions</h3>
                {data.research.latestDecisions.length > 0 ? (
                  data.research.latestDecisions.map((d) => (
                    <div className="entry" key={d.id}>
                      <p className="meta">
                        {d.id}
                        {d.date ? ` · ${d.date}` : ""}
                        {d.status ? ` · ${d.status}` : ""}
                      </p>
                      <p>{d.title}</p>
                    </div>
                  ))
                ) : (
                  <p className="empty">No decisions recorded.</p>
                )}
                <p className="note">
                  <a href={`${repo}/blob/main/DECISIONS.md`}>Full decision log</a> ({data.research.decisionCount})
                </p>
              </div>
              <div>
                <h3>Research registry</h3>
                {data.research.registry.length > 0 ? (
                  data.research.registry.map((r) => (
                    <div className="entry" key={r.id}>
                      <p className="meta">
                        {r.id}
                        {r.status ? ` · ${r.status}` : ""}
                      </p>
                      <p>{r.title}</p>
                    </div>
                  ))
                ) : (
                  <p className="empty">No registry entries.</p>
                )}
                <p className="note">
                  <a href={`${repo}/blob/main/RESEARCH.md`}>Research registry</a>
                </p>
              </div>
              <div>
                <h3>Experiments</h3>
                <p className="big">{state.validatedExperiments}</p>
                <p className="note">
                  validated · {data.research.experimentRecords} recorded
                  {state.trainedModels !== undefined ? ` · ${state.trainedModels} trained models` : ""}
                </p>
                <p className="note">
                  <a href={`${repo}/blob/main/EXPERIMENTS.md`}>Experiment registry</a>
                </p>
              </div>
            </div>
            <div className="next-action">
              {lastAccepted && (
                <p>
                  <span className="eyebrow">Latest accepted task</span>
                  <br />
                  <strong>{lastAccepted.id}</strong>
                  {lastAccepted.title ? ` — ${lastAccepted.title}` : ""}
                </p>
              )}
              {state.nextOverseerAction && (
                <p style={{ marginTop: "var(--space-3)" }}>
                  <span className="eyebrow">Next overseer action</span>
                  <br />
                  {state.nextOverseerAction}
                </p>
              )}
            </div>
          </section>

          <section className="section" id="method" aria-labelledby="method-title">
            <div className="section-head">
              <p className="eyebrow">Methodology</p>
              <h2 id="method-title">How progress is counted</h2>
            </div>
            <div className="method">
              <p className="pull">Progress is earned by demonstrated capability, not by elapsed time or code written.</p>
              <ol>
                <li>
                  <strong>Capability, not time.</strong> The roadmap is a weighted graph of milestones. Calendar time,
                  token spend, and training runs earn nothing.
                </li>
                <li>
                  <strong>Bounded tasks.</strong> Execution agents implement explicit briefs with a fixed write scope and
                  acceptance criteria. They do not set goals, splits, or weights.
                </li>
                <li>
                  <strong>Validated evidence only.</strong> A task counts only after an overseer reviews its evidence
                  package and validates it. Negative results can raise research coverage without raising goal progress.
                </li>
              </ol>
            </div>
          </section>
        </main>

        <footer className="colophon">
          <p>
            Rendered from the public repository <a href={repo}>{project.repository}</a> at build time. This page holds no
            separate status data.
          </p>
          <p>Schema {data.schemaVersion}.</p>
        </footer>
      </div>
    </>
  );
}
