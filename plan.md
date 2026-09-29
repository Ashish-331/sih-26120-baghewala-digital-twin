# Software Development Plan & Architecture
## SIH 26120: Digital Twin for Well-to-Surface Optimization of CSS and SRP Operations

### Phase 0: Requirements, Data Strategy & Contingencies
Before writing code, the team must resolve the unknowns bounding the problem statement.
* **Execution Procedure for Unknowns:**
  1. **Document Review:** Extract exact deliverables, evaluation rubrics, and technical constraints directly from the full SIH PS document.
  2. **Post-Qualification Strategy:** If the actual dataset is only released to qualified teams, the proposal phase will proceed using synthetic analogs derived from public Baghewala field literature. 
     - *Access Risk & Time-Box:* The team will prioritize open-access sources (DGH India archives, ONGC/OIL public reports, ResearchGate). This literature review is **time-boxed to a maximum of 4 hours**.
     - *Fallback for the Fallback:* If time expires with no relevant literature found, the team uses generic heavy-oil default parameters to test mathematical stability. **Demo Safety:** Any output generated from this path must be visibly watermarked/labeled "ILLUSTRATIVE - UNCALIBRATED" in the UI.
* **Physics & Scope Contingency Plan:**
  - Baghewala characteristics (heavy oil, CSS, SRP) are assumed provisional. 
  - *Branching Fallbacks:* If the PS specifies Steamflood instead of CSS, Boberg-Lantz is dropped. If PCPs/ESPs are specified instead of SRP, the Gibbs wave equation is discarded in favor of torque/affinity models.
  - *Fundamental Deviation Halt:* If the PS diverges entirely from thermal heavy-oil recovery, the current physics architecture is void. This check must occur by the **end of the Initial Requirements Session (typically Hours 1-3)** to allow time for reading attachments. If triggered, the team must halt and request an official PS switch from hackathon organizers.

### 1. Core Physics & Diagnostic Models
The twin couples the thermal recovery process with mechanical pump lifting.
* **Thermal Model (CSS Cycle):** Uses the Marx-Langenheim model to estimate heated zone growth (Injection phase) and the Boberg-Lantz model to estimate temperature/viscosity decline (Production phase).
* **Well-to-Surface Flow:** Uses the Ramey (1962) wellbore heat transmission model (or two-phase equivalents like Hasan-Kabir). *Domain Check:* The selection of Hasan-Kabir for two-phase flow must be verified by an SME or external mentor before implementation.
* **Mechanical Model (SRP):** Implements the 1D Damped Gibbs Wave Equation to compute downhole dynamometer cards.
* **Diagnostic ML (Feature-Based):** Dynamometer cards are processed as 1D vectors to extract engineered features (area, peak load, fill ratio). A lightweight classifier (e.g., Random Forest) is trained on these features.
  - *Fallback (Unsupervised):* If labeled failure data is missing, pivot to an Autoencoder for anomaly detection based on reconstruction error from historical baselines.

### 2. System Architecture & Demo Reliability
The tech stack is minimized for predictability and prediction-time availability.
* **Data Ingestion & Replay Engine:** A Python script simulates telemetry streaming via standard HTTP/REST. *Explicitly: No real PLC or register map has been seen; this is a placeholder.* 
  - **Demo Safeguard:** The simulator will feature a **Time-Compressed Replay Engine**. It will **precompute** the physical outputs of a full CSS cycle and play them back on a timer (compressing 3 weeks into a 3-minute animation). 
  - **Demo Ethics & Disclosure:** 
    - *If asked "Is this computing live?":* The team must honestly state: "The physics engine is fully functional, but this live-demo UI plays back a precomputed run to compress 3 weeks of operations into 3 minutes for stability."
    - *If asked "How do you know these numbers are accurate?":* If the uncalibrated Phase 0 fallback was triggered, the team must state: "These outputs use generic heavy-oil literature defaults to demonstrate the software pipeline's mathematical stability; they are explicitly illustrative and remain uncalibrated to Baghewala field data."
* **Backend Engine:** FastAPI (Python) handles data routing and serves the physics/ML models.
* **Database:** PostgreSQL handles all relational metadata and time-series telemetry.
* **Frontend:** A React/Next.js dashboard for visualizing cycles and dynamometer cards.

### 3. VFD Advisory System (Open-Loop) & Cycle Optimization
* **VFD Advisory:** Acts exclusively as a **Decision Support Tool**. As the thermal model estimates increasing viscosity, the twin recommends surface speed adjustments. No closed-loop actuation is designed.
* **SOR Cycle Transition:** Recommends transitioning from Production back to Injection based on a Steam-Oil Ratio (SOR) threshold. This threshold is a *configurable economic input* set by the operator.

### 4. Evaluation & Validation Strategy
* **Data Splitting:** Split provided historical data into training (70%) and hold-out testing (30%). 
  - *Volume Fallback:* If the dataset is small (< 5 wells), use *leave-one-well-out* or *k-fold cross-validation*.
* **Physical Metrics (RMSE/MAE):** Use RMSE or MAE in physical units (lbs for rod load, °C for temperature).
* **Diagnostic Metrics:** 
  - *Supervised:* Precision, Recall, and F1-score against the hold-out set.
  - *Unsupervised (Autoencoder):* Reconstruction error thresholds evaluated via manual SME review of flagged anomalies.
* **Financial Assumptions:** Any ROI outputs will explicitly list hardcoded assumptions and sources. 
  - *Oil Price:* Tied to the **PPAC Indian Crude Basket**.
  - *Steam Cost Methodology:* Pegged to **US EIA EOR cost reports**. *Methodological Simplification:* This is scaled purely by the ratio of the PPAC Indian natural gas benchmark against US Henry Hub prices, explicitly ignoring localized CapEx/O&M differences. The thermal conversion assumes ~10 MMBtu/ton of steam (based on standard SPE steamflood design literature, assuming 80% steam quality).
* **Hollow Twin Evaluation Pivot:** If the physics-free "Hollow Twin" fallback is triggered (see Section 5), physical metrics are discarded. Evaluation shifts entirely to software performance (e.g., API latency, data ingestion throughput, UI rendering FPS).

### 5. Prioritized Execution, Skills & Cut Order
* **Milestone 1 (Minimum Viable Demo - MVD):** Data ingestion pipeline, basic analytical thermal decline curve, and surface dynacard plotting. 
  - *Skills:* Python Data Engineer. *(Note: The Petroleum SME requirement is intentionally excluded here as Arps decline models rely on standard public math, deferring the domain bottleneck to M2).*
* **Milestone 2 (Core Twin):** Implementation of heat loss models, Gibbs wave solver, and the ML classifier. 
  - *Skills:* Physics/ML Engineer, **Petroleum SME**.
* **Milestone 3 (Optimization & Advisory):** Integration of economic SOR transition recommendations. 
  - *Skills:* Backend/UI Developer, **Petroleum SME (for logic/threshold validation)**.
* **Execution & Compounding Risks:** 
  - *SME Absence:* If the team lacks a Petroleum SME, they must replace the Gibbs equation with a basic 1D Spring-Mass kinematic model, and replace Marx-Langenheim with a generic Arps decline curve. *Note: Even these simplified models require literature-derived constants and a basic domain sanity check; they lower the SME burden but do not eliminate it.*
  - *Mid-Build Pivot Cutoff:* If Milestone 2 (Core Twin) is **< 50% complete by the end of Hackathon Day 1**, a pivot decision must be made. 
  - *Partial Twin (Middle Option):* Before abandoning physics, the team must evaluate shipping whichever subset is genuinely functional (e.g., Thermal-only or Mechanical-only). *Dependency Note:* A "Diagnostic-only" twin is only viable if real historical failure data is provided; if relying on synthetic data, the ML component cannot survive a physics engine failure. 
  - *Partial Twin Pitch Reframing:* If presenting a partial system, the team must explicitly reframe the pitch narrative. Instead of claiming a complete "Well-to-Surface" solution, pitch it as a "Modular, High-Fidelity Subsystem"—arguing that solving one specific domain with rigorous physics is more valuable than a shallow, physics-free dashboard spanning the whole system.
  - *Evaluation rules:* Section 4's metrics will restrict to whichever subset survives. If the surviving twin relies on generic Phase 0 fallback data, all outputs must still carry the 'ILLUSTRATIVE - UNCALIBRATED' watermark.
  - *Hollow Twin Pivot:* If no partial twin is viable, the team pivots to a "Hollow Twin"—a purely conceptual UI mockup and generic IoT data pipeline. 
  - *Rubric Warning:* Teams must acknowledge that if the PS strictly mandates physical modeling, a Hollow Twin risks severe penalization or disqualification. It is a desperation pivot, not a safe equivalent alternative.
* **Cut Order:** If time is short, frontend UI polish is downgraded to basic Matplotlib/Streamlit plots to ensure core physics and validation metrics are completed.
