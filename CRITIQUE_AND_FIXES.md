# Critique & Remediation Plan — SIH-26120 Baghewala Digital Twin

**Basis:** Full line-by-line review of `backend/`, `ml/`, `frontend/`, `plan.md`, `README.md` + numerical verification of the physics models.
**Severity legend:** 🔴 **P0** = blocks execution/trust · 🟠 **P1** = credibility/validity gap (judge will catch it) · 🟡 **P2** = engineering/domain tuning · ⚪ **P3** = polish.
**Effort legend:** S < 1 h · M = 1–4 h · L > 4 h.

---

## 🔴 P0 — Blockers: the project does not run on any other machine

### 1. Hardcoded absolute developer paths
- **Evidence:** `backend/simulator.py` line 13: `sys.path.insert(0, '/home/ashish/Desktop/SIH/ml')` · line 24: `MODEL_PATH = "/home/ashish/Desktop/SIH/ml/dynacard_rf_classifier.pkl"` · `ml/train_classifier.py` line 53: same path.
- **Why it matters:** Clone repo → `./run.sh` → immediate `ModuleNotFoundError` / `FileNotFoundError`. A judge or teammate cannot start the system. This single bug converts an 8/10 first impression into a "doesn't even run" disqualifier moment.
- **Solution:** Resolve paths relative to the repo root.
- **Approach (S):**
  ```python
  from pathlib import Path
  ROOT = Path(__file__).resolve().parents[1]          # repo root
  sys.path.insert(0, str(ROOT / "ml"))
  MODEL_PATH = ROOT / "ml" / "dynacard_rf_classifier.pkl"
  ```
  Optionally allow an env override: `Path(os.getenv("TWIN_MODEL_PATH", ROOT / "ml" / "dynacard_rf_classifier.pkl"))`.

### 2. README Quick Start points to a non-existent repo
- **Evidence:** README: `git clone https://github.com/Ashish-331/sih-baghewala-digital-twin.git` and `cd sih-baghewala-digital-twin/backend` — the actual repo is `sih-26120-baghewala-digital-twin`.
- **Why it matters:** Copy-paste onboarding fails at step 0.
- **Solution (S):** Fix the URL and `cd` path; then actually **execute the Quick Start on a clean machine/VM once** — that one test catches problems #1, #2, #3, #15 in a single pass.

### 3. Backend address hardcoded in 5 frontend files
- **Evidence:** `frontend/src/app/page.tsx`, `surface/page.tsx`, `analytics/page.tsx`, `well/[id]/page.tsx`, `components/VFDAdvisory.tsx` — all use literal `http://127.0.0.1:8000` and `ws://127.0.0.1:8000`.
- **Why it matters:** Cannot demo on a projector/laptop pair, cannot deploy, cannot run backend in Docker. Every environment change = code edits in 5 places.
- **Solution (S):** Central config module.
- **Approach:**
  ```ts
  // frontend/src/lib/config.ts
  export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  export const WS_URL = API.replace(/^http/, "ws") + "/ws/telemetry";
  ```
  Replace all literals, document `NEXT_PUBLIC_API_URL` in the README.

---

## 🟠 P1 — Credibility & AI-validity gaps (a technical judge will catch these)

### 4. "60 Hz full-duplex telemetry" claim vs. actual 1 Hz replay
- **Evidence:** README tech-stack: *"60 Hz Full-Duplex WebSockets"* · `Sidebar.tsx`: "Telemetry 60 Hz" · `DynacardChart.tsx`: "SCADA SAM-RPC 60Hz" — but `simulator.py` does `time.sleep(1)` → **1 Hz**, and the WebSocket is server→client only (client never transmits).
- **Why it matters:** UI/Doc claims that contradict the code are credibility leaks. Judges at SIH specifically probe "is this live?"
- **Solution (S):** Don't fake the number — **pitch the replay as the feature**: "Time-compressed replay engine: 21 days of CSS physics → 3 minutes, 1 Hz tick, fully deterministic for demo stability." That framing is *stronger* than a fake 60 Hz (your own `plan.md` already proves this was intentional design). Change: README row, Sidebar label, DynacardChart caption, and answers to judges.

### 5. "1D Damped Gibbs Wave Solver" is a static rod-stretch subtraction
- **Evidence:** `ml/thermal_models.py::compute_downhole_pump_card` — only computes stretch `= W_fluid / 30,000 lb·in⁻¹` and shifts positions. No wave propagation, no damping-term integration, no time stepping. Yet README (×2) and the well page tab call it a Gibbs wave solver.
- **Why it matters:** This is the most technically aggressive claim in the repo, and any petroleum/dynamics-literate judge can falsify it in 30 seconds. Two honest options:
- **Option A — Relabel (S, recommended for SIH):** Call it what it is: *"Kinematic pump-card transform: rod-stretch (Hooke) + valve load-transfer approximation (Gibbs-lite)"*. Your `plan.md` already pre-authorized this fallback — the docs just never got updated.
- **Option B — Implement a real solver (L, post-hackathon):**
  - Discretize the rod string into N≈100 elements; surface position/velocity from the measured card is the top boundary condition; pump boundary at the bottom via traveling/standing valve states.
  - Integrate `u_tt = a²u_xx − c·u_t` with central differences (a ≈ 16,000 ft/s in steel rod; respect CFL: `a·Δt/Δx ≤ 1`), damped term `c` from literature (~0.1–0.5 s⁻¹), run several pump cycles until periodic steady state.
  - Validate against the textbookEveritt–Jennings reference cards. ~60–100 lines of NumPy.

### 6. "Stokes fall velocity" advisory contains no Stokes mathematics
- **Evidence:** `VFDAdvisory.tsx`: `projectedRodStress = 14000 + targetSPM*1100 + viscosity*1.8` — arbitrary linear heuristic; README claims "Stokes Fall Velocity & Buckling Prevention".
- **Solution (M):** Implement the actual physics, it's short:
  ```python
  # Plunger/rod fall velocity (Stokes regime approximation)
  g, d, drho = 9.81, d_rod, rho_rod - rho_oil
  v_fall = g * d**2 * drho / (18 * mu)        # mu = dynamic viscosity Pa·s
  spm_max = v_fall / stroke_length * 60 / 2   # downstroke must not outrun the rod
  ```
  Advisory becomes: *"at μ = X cP, rod fall velocity = Y m/min → cap SPM at Z to avoid rod floating."* Same UI, now with real math behind the exact failure mode you already named. (For production use, replace Stokes with a viscous-drag correlation on the rod string — but Stokes is defensible for a demo.)

### 7. Two flagship physics models are implemented but never called
- **Evidence:** `simulator.py` imports `marx_langenheim_heated_area` and `ramey_wellbore_heat_loss` — **neither is ever invoked**. README presents Marx-Langenheim as Core Formulation #1. Dead imports.
- **Why it matters:** Claim-vs-code mismatch again; also a wasted asset — both functions are mathematically correct (verified: M–L gives ~15,130 m² heated area at 15 d for the documented test case, a sane number).
- **Solution (M):** Wire them in:
  - **Injection phase:** call `marx_langenheim_heated_area(steam_rate_bpd, enthalpy, ΔT, day_of_injection)` per step → add `heated_zone_area_m2` + `heated_radius_m` to the telemetry payload → render a "heated front" gauge on the well page. This makes the injection phase show *physics output* instead of static values.
  - **Injection-phase T(z):** replace the ad-hoc `frac**0.8` profile in `compute_depth_profile` with `ramey_wellbore_heat_loss(depth, injection_temp, time_days)`.
  - Add both outputs to `models.py` (Pydantic fields) → type safety end-to-end.

### 8. ML circular validation — train and inference data come from the same generator
- **Evidence:** `ml/train_classifier.py` builds 900 samples from `generate_dynacard()` (seed 42, σ=150); `backend/simulator.py` classifies live output of a near-identical `generate_dynacard()` (σ=80). Cross-validation accuracy (~1.0) proves nothing — the model is tested on its own homework.
- **Why it matters:** The first ML question from any judge ("what's your accuracy and how do you know?") currently has no honest answer.
- **Approach (M):**
  1. **Widen the training distribution:** randomize `W_r ∈ [4k, 6k]`, `W_f ∈ [8k, 12k]`, σ ∈ [50, 250], card length ∈ [40, 60], and inject 10% "corrupted" cards (gaps, spikes). Model must learn the *shape concept*, not the generator constants.
  2. **Independent test set:** generate test cards with a *different* seed and parameter draw; never touch during training.
  3. **Report honestly:** commit `ml/EVALUATION.md` with confusion matrix, per-class precision/recall/F1, and the exact data-generation protocol. Even a 0.94 F1 with a real protocol beats a meaningless 1.0.

### 9. The ML loop is self-confirming — it adds zero information
- **Evidence:** `simulator.py`: viscosity thresholds **decide** the condition (`visc>2200 → rod_floating`) → card of that condition is generated → ML classifies it → UI shows "ML detected rod floating". Delete the RF model and nothing about the system's behavior changes.
- **Why it matters:** This is the deepest conceptual problem in the repo. A digital twin's ML should observe *emergent* behavior of the physics, not labels the physics was *told* to produce.
- **Approach (M–L):** Invert the dependency:
  1. Generate the card from **physics inputs only** — plunger fillage from inflow (PI·(p_res−p_bh)), rod drag from viscosity, valve states from fillage — with no `condition` argument at all.
  2. Let the RF classify the emergent shape independently.
  3. **Use disagreement as signal:** if physics-regime says "normal" but the classifier says "fluid pound" with high confidence → flag "anomalous pump behaviour not explained by thermal state" — that's a genuine digital-twin insight and a killer demo talking point.
  4. Short on time? Then document the current design openly: *"classifier validates a rule-based regime map (grey-box consistency check)"* — honest framing converts a weakness into a defensible design choice.

### 10. Only 3 fault classes
- **Evidence:** `normal`, `rod_floating`, `fluid_pound`. The classic SRP card library (gas interference, traveling-valve leak, standing-valve leak, worn plunger, tubing movement, full fillage) is absent.
- **Approach (M):** Add 2 more cheap, high-credibility classes — **gas interference** ( delayed load pickup + rounded upstroke corner) and **traveling-valve leak** (slope on upstroke load plateau). Both are simple shape perturbations of the existing generator and immediately widen the "Edge ML" story.

### 11. Trained `.pkl` committed to git; pickle serialization risk
- **Evidence:** `ml/dynacard_rf_classifier.pkl` (119 KB) in the repo; loaded via `joblib.load` at simulator start.
- **Why it matters:** (a) sklearn version mismatch → load crash; (b) pickle executes arbitrary code on load — anti-pattern for a repo others run; (c) binary artifacts in git.
- **Solution (S):** Remove the `.pkl` from git; make `run.sh` train-if-missing: `[ -f ml/model.joblib ] || python ml/train_classifier.py`. Pin `scikit-learn==X.Y.Z`. (Optional, cleaner: serialize with `skops.io`.)

### 12. No evaluation artifacts, no confidence thresholding
- **Evidence:** training script prints CV score to stdout only; runtime maps `argmax(proba)` straight to a displayed diagnosis with no floor.
- **Solution (S):** `predict_proba` max < 0.70 → label `uncertain` in UI (grey badge). This is one line and makes the ML look *more* trustworthy, not less.

---

## 🟡 P2 — Engineering & domain tuning

### 13. No persistence (plan promised PostgreSQL; shipped in-memory lists)
- **Evidence:** `main.py` module-level `telemetry_db`, `well_history`, `transition_db`; restart loses everything. `plan.md` §2 specified PostgreSQL.
- **Approach (M):** SQLite via **SQLModel** — same Pydantic-style models you already wrote, zero infra, file-backed persistence. Abstract the store behind 4 functions (`ingest`, `history`, `fleet_state`, `transitions`) so Postgres later is a connection-string change. Don't build real Postgres before SIH — demo value ≈ 0, risk > 0. Do document the swap path.

### 14. Security posture: wildcard CORS + credentials, zero auth
- **Evidence:** `main.py`: `allow_origins=["*"], allow_credentials=True` (an invalid combo per CORS spec); `/api/setpoint` — the one endpoint that "actuates" something — has no auth.
- **Solution (S):** `allow_origins=[FRONTEND_URL]`, `allow_credentials=False`; add a static bearer token header check on `/api/setpoint` only (read-only endpoints can stay open for the demo). One middleware, ~15 lines.

### 15. Unpinned dependencies
- **Evidence:** `requirements.txt` uses `>=` everywhere. Code uses `np.trapezoid` → silently requires NumPy ≥ 2.0; sklearn pickle (see #11) silently requires the trainer's sklearn version.
- **Solution (S):** `pip freeze > requirements-lock.txt`, use it in the README; or adopt `uv`/`poetry` lock. Cheap insurance judged reproducibility.

### 16. Alert dedup checks only the single last transition
- **Evidence:** `main.py`: `if not transition_db or transition_db[-1].well_id != data.well_id or ...` — if two wells alternate SOR breaches, every tick appends a new alert → spam.
- **Solution (S):** keep per-well last-recommendation state:
  ```python
  last_alert_rec: Dict[str, str] = {}
  if last_alert_rec.get(well_id) != recommendation:
      transition_db.append(alert); last_alert_rec[well_id] = recommendation
  ```

### 17. Process management fragility (`run.sh` + `--reload`)
- **Evidence:** `main.py` runs `uvicorn.run(..., reload=True)`; `run.sh` backgrounds both and traps signals — uvicorn's reloader forks a child that the trap won't kill → orphaned port-8000 processes on the demo laptop.
- **Solution (S):** `reload=False` for the demo; kill by process group. **Better (M):** one `docker-compose.yml` (backend+simulator as one Python container with two processes via `supervisord` or a tiny entrypoint; frontend as a second service) → judge runs `docker compose up`. This single file fixes #1, #2, #3, #15, #17 as a bundle.

### 18. "Full-duplex" WebSocket is receive-only
- **Evidence:** server does `await websocket.receive_text()` purely to detect disconnects; the browser never sends commands over WS (setpoint goes via REST).
- **Solution (S):** either route the VFD setpoint dispatch over the WS (real duplex, tiny change), or drop the word "full-duplex" from the docs.

### 19. Zero automated tests
- **Evidence:** no `tests/`, no CI.
- **Solution (M, high ROI):** ~12 pytest cases — you already know the right expected values:
  - `calculate_viscosity(40) ≈ 14 900 ± 5 %`, `(100) ≈ 810`, `(250) ≈ 10` (verified against the code).
  - Boberg–Lantz: `t=0 → T_init`; `t→∞ → T_res`; strictly decreasing.
  - Marx–Langenheim: `area(0)=0`; strictly increasing in t.
  - Feature extractor: constant card → `load_range = 0 → fill_ratio = 0`, no exception.
  - API smoke: `TestClient` POST a minimal telemetry payload → 201; `GET /api/status` → "online".
  - CI: GitHub Action running pytest + `npm run build`. This converts "trust me" into a green badge on the README — the single cheapest credibility purchase available.

### 20. Economic tuning collapses: production phase floored at −$464/day most of the cycle
- **Evidence (computed, not vibes):** with the shipped formulas, cycle-2 well oil rate goes 44 bpd (fresh heat) → 8.5 bpd within ~2 days (viscosity ratio `9/47 cP` crushes `visc_inflow_factor`) → floor 5 bpd ⇒ SOR pinned at 7.0, margin pinned at −$464/day for most of the 12-day production phase. Meanwhile the frontend's offline fallback shows SOR 1.2 / margin +$4,800 — **the live engine and the demo fallback tell contradictory stories.**
- **Approach (M):**
  1. Soften the inflow model: `visc_inflow_factor = min(1, (μ_steam/μ(T))**0.5)` (square-root response — heavy-oil PI responds sub-linearly to viscosity) or hold PI recovery for the soak-heated period.
  2. Use **cumulative cycle SOR** (steam injected this cycle ÷ cumulative oil this cycle) for the economic decision — that is how CSS is actually evaluated; keep instantaneous SOR as a secondary gauge.
  3. Regenerate all frontend fallback constants **by running the engine once and copying its mid-cycle outputs** — live and offline modes then agree by construction.

### 21. `days_to_sor_cutoff` uses a hardcoded slope
- **Evidence:** `simulator.py`: `rate_of_sor_rise = 0.15` — a magic constant unrelated to the actual SOR trajectory; every well gets the same countdown dynamics.
- **Solution (S):** estimate the slope from live data: linear fit over the last k SOR points `slope = polyfit(t, sor[-k:], 1)[0]`, then `days = (cutoff − sor)/slope` (guard `slope ≤ ε → "stable"`). Fifteen lines, real output.

### 22. Headline analytics feature never triggers with default parameters
- **Evidence (the math is exact):** `analytics/page.tsx` uses `q₀=140 bpd, Dᵢ=0.08/d, steam=35 t/d` ⇒ `SOR(t) = 35(1+0.08t)/140 = 0.25(1+0.08t)`. Solving `SOR(t) = 3.16` gives **t ≈ 145 days** — the chart only draws days 1–14, so `sorCrossoverDay` is always `undefined`: the "automatic breakeven inflection" never appears on screen. (Also, instantaneous SOR of 0.25–0.53 is unrealistically rosy — real CSS operates at SOR 3–5.)
- **Solution (S–M):** pick parameters from your own engine: peak oil ≈ 20–25 bpd, Dᵢ ≈ 0.10–0.15 ⇒ crossover lands at ~day 8–12, **inside** the chart; or extend the horizon to 21 days and mark the crossing point with a `ReferenceDot`. Bonus: label the axis "instantaneous SOR" and add the cumulative-SOR line (#20) — the difference between the two is itself an expert-level talking point.

### 23. Simulator discards its own simulated clock
- **Evidence:** `precompute_well` builds `sim_time` (+2.8 h/step, offset per well) — then `run_simulation` overwrites `payload["timestamp"] = datetime.now()`. Result: the analytics historian plots data claiming 2.8 h spacing on a 1-second wall-clock axis; decline curves look time-wrong, and offset wells appear simultaneous.
- **Solution (S):** send both — `timestamp` (wall clock, for liveness) and `sim_time` (process clock, for physics plots); x-axis of all trend charts = `sim_time`.

### 24. Water cut displayed as 100 % during Injection/Soak
- **Evidence:** `simulator.py` sets `water_cut = 100.0` in non-production phases; fleet table renders "WC: 100%".
- **Solution (S):** emit `null`/last-producing value outside Production; render "—". Tiny fix, removes a "huh?" moment in front of judges.

---

## ⚪ P3 — Polish

| # | Item | Fix (effort) |
|---|------|--------------|
| 25 | Offline fallback data contradicts live engine (margins/SOR) (#20 covers cause) | Regenerate fallback constants from one engine run (S) |
| 26 | No LICENSE; history squashed to 1 commit | Add MIT/Apache-2.0 (S); keep incremental commits going forward |
| 27 | `/analytics` shows only the banner watermark, other pages also show the diagonal one | Standardize on the banner everywhere **or** both everywhere (S) |
| 28 | `frontend/README.md` is create-next-app boilerplate | Replace with 10-line route map + env vars (S) |

---

## Recommended fix order (≈ 1 focused day)

| Order | Items | Why first | Effort |
|---|---|---|---|
| 1 | #1, #2, #3, #15 | Nothing else matters if it won't run elsewhere | ~1 h |
| 2 | #4, #5-A, #6, #7, #18, #24 | Kill every doc-vs-code mismatch (cheap, judge-visible) | ~2 h |
| 3 | #20, #21, #22, #23 | Make the live engine and UI tell one consistent story | ~2–3 h |
| 4 | #8, #11, #12 (+#10 if time) | ML credibility package + EVALUATION.md | ~2 h |
| 5 | #19, #16, #14, #17 | Tests, alerts, auth, compose | ~2–3 h |
| 6 | #9, #13 | Deeper ML redesign, persistence — only if spare time remains | L |

**Explicitly do NOT attempt before the hackathon:** the full Gibbs finite-difference solver (#5-B), real PostgreSQL, auth beyond the setpoint token, Kubernetes/cloud deployment. High risk, near-zero judging value versus relabeling honestly.

## Pre-approved answers if a judge probes (extend your plan.md ethics script)

- *"Is this computing live?"* → "The physics engine is fully functional and live; the UI plays a time-compressed deterministic replay — 21 days in 3 minutes — so you can watch an entire CSS cycle, including degradation across cycles 1, 2 and 4."
- *"Where's the field data?"* → "Baghewala sensor data is OIL-restricted; every constant is anchored to published literature (viscosity fit verified at 3 temperatures), and the UI carries the UNCALIBRATED watermark by design."
- *"What's your ML accuracy?"* → (after fix #8) "0.9x F1 on an independent synthetic test set drawn from a different noise distribution than training — protocol and confusion matrix are in `ml/EVALUATION.md`. The classifier cross-checks a rule-based thermal regime map; disagreement itself is surfaced as an advisory."
- *"Is that really the Gibbs equation?"* → (after fix #5-A) "It's the kinematic subset — Hookean rod stretch plus valve load transfer; the full damped-wave solver is on the roadmap and the interface already carries the fields it would output."
