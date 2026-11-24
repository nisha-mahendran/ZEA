# ZEA: The Self-Verifying AI On-Call Engineer — Build Spec

Hackathon problem statement: **B3, The AI on-call engineer** (watch running systems, find root cause, propose or ship the fix, prove it worked, so keeping software alive needs far fewer people).

Status: derived from the JARVIS blueprint + interview on 2026-11-23. "JARVIS" is renamed **ZEA** everywhere (Marvel trademark concern). Solo build, 12 days.

---

## 1. Product definition

ZEA is an always-on, conversational AI engineer that understands a software system, investigates incidents with competing hypotheses, proposes a fix, and **proves recovery** before a human signs off.

- ZEA is **ZEA 2.0 on top of the 10-module on-call engineer**, not a separate product. The 10 modules remain the skeleton; the differentiators below are the depth layer.
- Autonomous within explicit permissions, never unrestricted. Humans stay accountable for production decisions.
- Optimization target: **hackathon judges first; portfolio quality second**. Where they conflict, the demo wins.

### Principles
Understand before acting. Investigate before concluding. Show evidence. Say when it doesn't know. Verify before claiming success. Ask approval before consequential actions. Resolution is the goal, whoever does the work.

### Differentiators (build priority order)
1. **Verified Recovery Engine** (must never be cut; the moment judges remember).
2. **Compound Incident Intelligence**: separate independent failures from symptoms.
3. **Evidence-backed investigation with adversarial mode**: experiments decide disputes.
4. **Engineering memory** (RAG) with visible wrong-match rejection.
5. **Context Completeness** (minimal) and **Benchmark Lab** (scripted scenarios, held-out set).

Claim only what is built. No uniqueness claims without a competitor study (existing: HolmesGPT, Aurora, Resolve AI, Rootly, Datadog Bits AI).

---

## 2. Scope

### In scope (12 days)
Monitoring intake, alert grouping, context gathering, codebase intelligence, multi-hypothesis investigation, conversational interface, patch generation, sandbox verification under traffic, GitHub PR creation, human approval gate, incident report, RAG memory for a second demo incident, timeline UI, benchmark of scripted scenarios.

### Explicitly OUT of scope (refuse to touch)
- Mobile companion
- Continuous self-improvement / auto-updating prompts or strategies
- Cost/resource optimisation features
- Resilience when the monitoring platform itself is down (roadmap slide only)

Also deferred: counterfactual rollback-vs-patch comparison (only if days remain), full Slack/Jira/Confluence ingestion depth (see §6), policy-based autonomous remediation.

---

## 3. Architecture

### 3.1 Layers
1. **Sample system**: fork of the OpenTelemetry Demo (see §4).
2. **Ingestion**: Prometheus Alertmanager webhooks, OTel traces/metrics/logs, GitHub, optional Slack/Jira/Confluence adapters.
3. **ZEA core** (Python + FastAPI): hand-rolled **explicit state machine** (no LangGraph), phases persisted to Postgres. Phases: `DETECT → GROUP → GATHER → HYPOTHESIZE → INVESTIGATE → EXPERIMENT → DIAGNOSE → REMEDIATE → VERIFY → AWAIT_APPROVAL → RESOLVE → REPORT`.
4. **Verification sandbox** (Docker Compose).
5. **UI** (Next.js + TypeScript + Tailwind): incident timeline is the hero.
6. **Data**: Postgres (+ pgvector, + FTS), Redis for jobs if needed.

Agents are mostly deterministic services/tools plus a small number of LLM calls under one orchestrator. No free-form agent swarm.

### 3.2 State model: event log + derived views
- Single **append-only `events` table** is the source of truth. Every observation, claim, hypothesis, evidence item, experiment, tool call, human message, approval and state transition is an event.
- Each event carries: `incident_id`, `ts`, `actor` (system | zea | human:<id>), `kind`, `payload`, `provenance` (source + query/link), and **`epistemic_status`**: `observed` (from telemetry/code), `verified` (confirmed by experiment), `human_claim`, `inferred` (model-derived), `rejected`.
- Derived projections (computed, never hand-edited): timeline, hypothesis board, facts list, dependency impact, incident report.
- Rule: a `human_claim` is never displayed or reasoned over as a fact until an experiment or observation upgrades it.
- Supports the question "Why did we abandon the first solution?" by querying the event history.

### 3.3 Security boundaries (enforced in code)
- **Per-phase tool allowlist**: INVESTIGATE/EXPERIMENT phases have read-only tools plus sandbox execution only. Write tools (open PR, any deploy action) are physically unavailable until the human approval event exists.
- **Quarantined reader**: raw untrusted text (logs, Slack, Jira, Confluence, PR comments) is first processed by a separate no-tools LLM call that emits structured fields (summary, entities, timestamps, severity). The tool-using model sees the structured output, not raw text.
- Read-only default; sandboxed execution; resource limits and timeouts; auditable action history; rollback path.
- Planned **live demo beat**: a malicious log line is planted; ZEA flags it as an injection attempt and ignores it.
- Data hygiene: redaction of obvious secrets before indexing; retention noted in docs.

---

## 4. Sample application and fault scenarios

- **Base**: fork of OpenTelemetry Demo. Polyglot, so **restrict to 2–3 patchable services** (checkout, payment, and one more, e.g. cart or product-catalog). Others run unmodified. Ensure repo symbol indexing covers only those languages.
- **Telemetry**: Prometheus metrics, OTel traces (Jaeger or Tempo), logs. Alert rules defined in Prometheus; Alertmanager webhooks go to ZEA.
- **Fault injection, mixed per scenario**:
  - *Checkout bug*: a real bad commit (e.g. N+1 / missing index style query regression) deployed from git, so ZEA must find it through diff + code + traces.
  - *Payment dependency*: a **mock external payment gateway with controllable fault modes** (slow, erroring, flapping), driven by chaos tooling (toxiproxy or equivalent) where useful.
  - *Infra-style faults* (pool exhaustion, memory growth): chaos/config-level, for benchmark breadth.
- **Mitigation, not "fixing the vendor"**: for external faults ZEA proposes a resilience change (timeout, retry with backoff, circuit breaker) verified against the mock, and escalates/notifies the owner.

---

## 5. Core capabilities

### 5.1 Detection and grouping
- Detection path: Prometheus alert rules in. ZEA does **grouping, deduplication and correlation**, plus validation against recent baseline to suppress harmless variation (no independent anomaly-detector build).
- Output: one or more incidents, each with severity and the alerts folded into it ("50 alerts, 3 services → 1 investigation").

### 5.2 Compound incident separation
Three mechanisms combined:
1. **Topology**: cluster alerts by the service dependency graph (alerts not causally reachable from each other tend to be separate).
2. **Temporal + metric correlation**: onset time and signal-shape similarity.
3. **Hypothesis-driven residual**: test whether one root-cause hypothesis explains all symptoms; unexplained symptoms form a second incident.
LLM labels clusters and writes explanations, but partitioning is driven by 1–3. Output classes: primary root cause, secondary failure, contributing factor, downstream symptom, unrelated concurrent problem.

### 5.3 Context gathering
Automatic bundle per incident: start time, affected services, recent deployments, relevant diffs, related historical incidents, health snapshot, owning team (service catalogue file), plus a **Context Completeness** panel (see §5.8).

### 5.4 Codebase and system intelligence (hybrid)
- **Topology** from traces and compose/config files → dependency graph ("which services depend on this database?").
- **Code evidence** from tree-sitter symbol index plus grep/read tools used by the agent. No embedding index over code.
- Every code claim cites file, line and commit.
- Doc-vs-reality drift check (see §5.8).

### 5.5 Investigation engine
Workflow: symptoms → hypotheses → gather evidence for each → inspect code/logs/metrics/traces/deployments → compare to history → run discriminating experiments → eliminate unsupported → rank → report. Unfamiliar incidents get fresh hypotheses, safe experiments, stated uncertainty, escalation. Memory results are starting hypotheses only.

**Confidence = qualitative bands, rule-derived, never LLM self-reported percentages:**
- **High**: multiple independent supporting signals **and** a successful confirming experiment.
- **Medium**: consistent evidence, no experimental confirmation.
- **Low**: incomplete or conflicting evidence.
- UI always shows supporting **and** contradicting evidence; diagnosis is marked **unverified** when confirmation is missing.

### 5.6 Adversarial Investigation Mode
When the engineer disputes the diagnosis ("it's the connection pool"), ZEA treats it as a `human_claim` hypothesis, searches for supporting and contradicting evidence, and **designs and runs a discriminating experiment in the sandbox** to decide. Outcomes: engineer right, ZEA right, compound (primary + contributing), or insufficient evidence (stated plainly). It must be willing to disagree.

### 5.7 Remediation and Verified Recovery Engine
Remediation: locate code → candidate fixes with risk notes → patch → run unit/integration/regression tests → request approval → open GitHub PR.

Verification gate (the centrepiece):
1. **Red-then-green**: ZEA must first **reproduce the failure on the unpatched build** in the sandbox. If it cannot, the investigation is marked *unverified* and no "recovered" claim is made.
2. **Test environment**: Docker Compose clone of the system with the same images and seed data volume, fault re-injected, then:
   - **replayed traffic** captured from the incident window, plus
   - a **synthetic load ramp** (k6 or Locust) calibrated to the incident's traffic shape.
3. Checks on the patched build: original failure gone; sustained load OK; **survives process restart**; regression suite passes; data integrity preserved; other services not regressed; latency/error/memory vs baseline.
4. **"Resolved" = all automated checks pass + human sign-off.** A patch that looks right is never called a fix.
5. If verification fails: stop, report which check failed, propose an alternative. Never auto-retry into production.

**Approval gate UI**: engineer sees the diff plus the verification report (before/after, red-then-green evidence). Approval means "OK to merge via the normal GitHub flow"; ZEA does not itself deploy to production.

### 5.8 Context Completeness (minimal)
- Pre-investigation checklist: which sources are connected, stale, or missing; states how that limits the diagnosis ("no payment-provider logs; diagnosis incomplete").
- Doc-vs-reality: one **planted stale architecture doc** that ZEA catches by comparing it to the trace-derived dependency graph.

### 5.9 Engineering memory (RAG)
- Store: **Postgres + pgvector + FTS** (hybrid retrieval). Incident memory, system memory, engineering memory as typed records with timestamps and provenance.
- Corpus: **mix of public postmortems and authored incidents**; authored set includes true matches *and* near-miss decoys.
- Demo beat: retrieval returns a **superficially similar but wrong** past incident; ZEA rejects it with evidence and continues. Memory is a hypothesis source, never truth.
- Freshness: source timestamps, versioned retrieval, contradictory-source flagging.

### 5.10 Conversational interface and reporting
- Persistent per-incident conversation context; questions answered from the event log with evidence cards inline.
- Postmortem auto-generated from the event log (what, when, services, cause, evidence, actions, code changes, tests, recovery, prevention) and written back to incident memory.

---

## 6. Integrations: "real where free tiers allow, mock the rest"
- **GitHub**: real (PRs, diffs, history).
- **Slack / Jira / Confluence / PagerDuty**: real where a free tier can be set up quickly; otherwise seeded fixtures behind the same adapter interface. Decide per integration by end of Day 2; do not sink time here.
- Context Completeness panel must truthfully show which are live vs fixture.

---

## 7. UI/UX

- **Hero screen: Incident Timeline.** Vertical timeline of detection, grouping, hypotheses, experiments, rejections, human interventions, verification, with evidence links and epistemic-status badges. This is the screen judges watch at the moment of diagnosis.
- Supporting panels (secondary, keep minimal): chat side panel, hypothesis cards with ± evidence and confidence band, approval view (diff + verification report), dependency graph with incidents colour-separated, completeness checklist.
- No separate mobile UI.

---

## 8. LLM strategy
- Model/tier **not fixed**: "whatever credits allow". Recommendation in spec: route by phase (cheap model for triage/summarisation and the quarantined reader, strongest available for diagnosis and patch generation), behind a single provider interface so the model can be swapped.
- Log every prompt/response/tool call into the event log. Cache and record tool-call traces to enable replay.
- **Pre-recorded full backup run is mandatory** for the demo (live + recorded insurance). Failure handling is shown via the recording or slides, not relied on live.
- Open item: pick provider and confirm credit limits by Day 1.

---

## 9. Benchmark Lab (honest minimal version)
- Replayable scripted fault scenarios, each with ground-truth root cause, expected evidence, and a verified fix.
- **A held-out subset is required**: scenarios not used while tuning prompts/retrieval, to avoid overfitting claims.
- Score **ZEA only** (no human baseline in this build; do not claim senior-engineer comparison). Final scenario count set on Day 5; target 5–8 with at least one compound and one held-out unfamiliar fault.
- Report honestly, including failures.

Metrics: root-cause accuracy, hypothesis-rejection accuracy, fix success rate, regression rate, red-then-green reproduction rate, time to detect/diagnose/resolve, false-positive rate, escalation accuracy, cost per investigation.

---

## 10. Demo (5 minutes) and fallback
1. Healthy system.
2. Inject two simultaneous faults (checkout code bug + payment gateway degradation).
3. ZEA detects, separates into **two independent incidents**, shows completeness panel (one gap, one stale doc).
4. Timeline fills with competing hypotheses and evidence; engineer disputes one → ZEA runs a discriminating experiment.
5. Injection beat: planted malicious log line flagged and ignored.
6. ZEA reproduces fault (red), generates patches, runs verification under replayed + ramped traffic (green), restart test.
7. Engineer reviews diff + verification report, approves; PR shown.
8. Question: "How do you know your fixes didn't break anything?" → before/after results.
9. Auto-generated incident report.
10. Second, different incident: memory retrieval returns a wrong match, ZEA rejects it, investigates, resolves.
Backup: full pre-recorded run of the same flow.

---

## 11. 12-day plan (vertical slice first)

| Days | Goal |
|---|---|
| 1–2 | Fork OTel Demo, restrict patchable services, wire alert rules → ZEA webhook, events table, state machine skeleton, choose LLM/provider, decide real-vs-fixture integrations |
| 3–4 | **Crude end-to-end slice**: one fault → detect → context → hypotheses → patch → sandbox red/green → PR. Ugly UI acceptable |
| 5–6 | Verified Recovery depth (replayed traffic, ramp, restart, data integrity), scenario scripting, define benchmark set + held-out |
| 7–8 | Compound separation (topology + correlation + residual), mock gateway fault modes, timeline UI as hero |
| 9 | Memory/RAG, authored + public corpus, wrong-match demo; adversarial mode with experiments |
| 10 | Injection guards (allowlists + quarantined reader) with live beat; completeness panel + planted stale doc; postmortem generation |
| 11 | Benchmark run and metrics; bug fixing; record backup demo; README/architecture docs |
| 12 | Demo rehearsal, polish, submission. **No new features** |

Rule: do not add features until the core flow works end to end; protect Verified Recovery above everything.

---

## 12. Risks and mitigations
- **Solo, 12 days**: strict out-of-scope list; vertical slice by Day 4.
- **LLM variance or API stall during demo**: recorded backup, cached traces, scripted deterministic faults.
- **Polyglot fork**: patchable services limited to 2–3; others untouched.
- **Vacuous verification**: red-then-green gate; unverified label otherwise.
- **Overfitting to the demo**: held-out scenarios, second unseen incident, honest metrics.
- **Prompt injection**: code-level allowlists + quarantined reader; demoed.
- **Integration time sink**: time-boxed decisions; fixtures behind adapters.
- **Over-claiming**: no uniqueness claims; label fixtures and mocks.

---

## 13. Open questions
1. LLM provider/tier and credit budget (Day 1).
2. Which of Slack/Jira/Confluence/PagerDuty get live accounts.
3. Exact third patchable service.
4. Final benchmark scenario count and which are held out.
5. Whether counterfactual rollback testing fits after Day 9 (default: cut).
6. Replay mechanism for captured traffic (proxy capture vs. trace-derived request regeneration).
