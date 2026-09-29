import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL_PATH = Path(os.getenv("TWIN_MODEL_PATH", ROOT / "dynacard_rf_classifier.pkl"))

def generate_dynacard(condition, num_points=100, W_r=None, W_f=None, noise_scale=None, corrupt_prob=0.0):
    """
    Kinematic pump model with domain shape perturbations for 5 standard fault classes.
    Supports parameterized randomization for robust generalization across pump depths.
    """
    if W_r is None:
        W_r = np.random.uniform(4200, 5400)
    if W_f is None:
        W_f = np.random.uniform(8500, 11500)
    if noise_scale is None:
        noise_scale = np.random.uniform(60, 180)

    position = np.concatenate([np.linspace(0, 100, num_points // 2), np.linspace(100, 0, num_points // 2)])
    load = np.zeros(num_points)

    if condition == "normal":
        # Upstroke: elastic elongation pickup (0-20), steady fluid lift (20-50)
        load[0:20] = np.linspace(W_r, W_r + W_f, 20)
        load[20:50] = W_r + W_f + np.random.normal(0, noise_scale, 30)
        # Downstroke: valve transfer (50-70), rod fall (70-100)
        load[50:70] = np.linspace(W_r + W_f, W_r, 20)
        load[70:100] = W_r + np.random.normal(0, noise_scale, 30)

    elif condition == "rod_floating":
        # Heavy oil Stokes viscous drag retarding rod descent
        load[0:20] = np.linspace(W_r, W_r + W_f, 20)
        load[20:50] = W_r + W_f + np.random.normal(0, noise_scale, 30)
        load[50:80] = np.linspace(W_r + W_f, W_r + (W_f * 0.58), 30)
        load[80:100] = W_r + (W_f * 0.58) + np.random.normal(0, noise_scale, 20)

    elif condition == "fluid_pound":
        # Incomplete pump fillage / fluid level starvation
        load[0:20] = np.linspace(W_r, W_r + W_f, 20)
        load[20:50] = W_r + W_f + np.random.normal(0, noise_scale, 30)
        load[50:62] = np.linspace(W_r + W_f, W_r + W_f * 0.92, 12)
        load[62:68] = np.linspace(W_r + W_f * 0.92, W_r * 0.65, 6) # sudden pound impact
        load[68:100] = W_r + np.random.normal(0, noise_scale * 1.3, 32)

    elif condition == "gas_interference":
        # Gas cushion in pump barrel causes delayed load pickup & rounded corners
        load[0:30] = np.linspace(W_r, W_r + W_f, 30) ** 0.95 * (W_r + W_f) ** 0.05
        load[30:50] = W_r + W_f + np.random.normal(0, noise_scale, 20)
        load[50:75] = (W_r + W_f) - ((np.linspace(0, 1, 25) ** 1.8) * W_f) # gradual gas expansion
        load[75:100] = W_r + np.random.normal(0, noise_scale, 25)

    elif condition == "traveling_valve_leak":
        # Fluid slipping past worn traveling valve ball & seat during upstroke
        load[0:20] = np.linspace(W_r, W_r + W_f, 20)
        # Drooping upstroke load line as column weight bleeds back into barrel
        load[20:50] = np.linspace(W_r + W_f, W_r + W_f * 0.72, 30) + np.random.normal(0, noise_scale, 30)
        load[50:70] = np.linspace(W_r + W_f * 0.72, W_r, 20)
        load[70:100] = W_r + np.random.normal(0, noise_scale, 30)

    # Inject sensor corrupted spikes/gaps if flagged
    if corrupt_prob > 0.0 and np.random.rand() < corrupt_prob:
        spike_idx = np.random.randint(0, num_points, 3)
        load[spike_idx] += np.random.choice([-1, 1], size=3) * np.random.uniform(500, 1500)

    return position, load

def extract_features(position, load):
    half = len(load) // 2
    # Net polygon area (in*lb)
    area = abs(np.trapezoid(load[:half], position[:half]) + np.trapezoid(load[half:], position[half:]))
    peak_load = np.max(load)
    min_load = np.min(load)
    load_range = max(1.0, peak_load - min_load)
    fill_ratio = (np.mean(load) - min_load) / load_range
    # Skewness & slope indicators to differentiate gas interference & valve leaks
    upstroke_slope = (load[half - 1] - load[20]) / max(1, half - 21)
    downstroke_midpoint_load = load[half + 15] / peak_load
    return [area, peak_load, min_load, load_range, fill_ratio, upstroke_slope, downstroke_midpoint_load]

def main():
    np.random.seed(42)
    conditions = ["normal", "rod_floating", "fluid_pound", "gas_interference", "traveling_valve_leak"]
    
    # 1. Training Set (Varied operational parameters & 8% corrupted sensor noise)
    X_train, y_train = [], []
    for cond in conditions:
        for _ in range(400):
            pos, load = generate_dynacard(cond, W_r=None, W_f=None, noise_scale=None, corrupt_prob=0.08)
            feats = extract_features(pos, load)
            X_train.append(feats)
            y_train.append(cond)
            
    clf = RandomForestClassifier(n_estimators=120, max_depth=10, random_state=42, class_weight="balanced")
    clf.fit(X_train, y_train)
    
    # 2. Independent Test Set (Different seed 999, independent distribution shifts)
    np.random.seed(999)
    X_test, y_test = [], []
    for cond in conditions:
        for _ in range(150):
            pos, load = generate_dynacard(cond, W_r=np.random.uniform(4000, 5800), W_f=np.random.uniform(8000, 12000), noise_scale=np.random.uniform(80, 220), corrupt_prob=0.12)
            feats = extract_features(pos, load)
            X_test.append(feats)
            y_test.append(cond)
            
    y_pred = clf.predict(X_test)
    report = classification_report(y_test, y_pred, target_names=conditions, digits=4)
    cm = confusion_matrix(y_test, y_pred, labels=conditions)
    
    # Save model
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")
    
    # Generate Evaluation Report (Fixes #8, #10, #12)
    eval_md = f"""# Edge ML Dynacard Diagnostic Evaluation Protocol

**Model:** Random Forest Classifier (`dynacard_rf_classifier.pkl`)  
**Architecture:** 120 Estimators, max_depth=10, 7 Handcrafted Kinematic Shape Features  
**Classes:** 5 (`normal`, `rod_floating`, `fluid_pound`, `gas_interference`, `traveling_valve_leak`)  
**Dataset Protocol:**
- **Training Set:** 2,000 synthetic dynamometer cards generated with randomized rod weights ($W_r \\in [4.2k, 5.4k]$), fluid weights ($W_f \\in [8.5k, 11.5k]$), Gaussian sensor jitter ($\\sigma \\in [60, 180]$), and 8% sensor spike noise.
- **Independent Test Set:** 750 samples drawn with independent seed (999) and wider parameter variations ($W_r \\in [4.0k, 5.8k]$, $W_f \\in [8.0k, 12.0k]$, $\\sigma \\in [80, 220]$, 12% corruptions). Zero overlap with training seeds.

---

## 📊 Classification Report (Independent Test Set)

```
{report}
```

## 🎯 Confusion Matrix (Rows = Ground Truth, Columns = Predicted)

```
Classes: {conditions}
{cm}
```

---

## 🛡️ Reliability & Grey-Box Decision Logic

1. **Confidence Thresholding:** Telemetry with $\\max P(\\text{{class}}) < 0.70$ is tagged as `uncertain` to prevent false positive actuation.
2. **Grey-Box Consistency Verification:** The edge ML diagnosis is cross-checked against thermodynamic state variables (BHT, Andrade Viscosity, Fluid Pound Fillage). Any divergence flags an *"Unexplained Mechanical Discrepancy"*.
"""
    with open(ROOT / "EVALUATION.md", "w") as f:
        f.write(eval_md)
    print(f"Evaluation report written to {ROOT / 'EVALUATION.md'}")
    print("\n" + report)

if __name__ == "__main__":
    main()
