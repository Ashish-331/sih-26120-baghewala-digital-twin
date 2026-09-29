# Edge ML Dynacard Diagnostic Evaluation Protocol

**Model:** Random Forest Classifier (`dynacard_rf_classifier.pkl`)  
**Architecture:** 120 Estimators, max_depth=10, 7 Handcrafted Kinematic Shape Features  
**Classes:** 5 (`normal`, `rod_floating`, `fluid_pound`, `gas_interference`, `traveling_valve_leak`)  
**Dataset Protocol:**
- **Training Set:** 2,000 synthetic dynamometer cards generated with randomized rod weights ($W_r \in [4.2k, 5.4k]$), fluid weights ($W_f \in [8.5k, 11.5k]$), Gaussian sensor jitter ($\sigma \in [60, 180]$), and 8% sensor spike noise.
- **Independent Test Set:** 750 samples drawn with independent seed (999) and wider parameter variations ($W_r \in [4.0k, 5.8k]$, $W_f \in [8.0k, 12.0k]$, $\sigma \in [80, 220]$, 12% corruptions). Zero overlap with training seeds.

---

## 📊 Classification Report (Independent Test Set)

```
                      precision    recall  f1-score   support

              normal     1.0000    0.9733    0.9865       150
        rod_floating     1.0000    1.0000    1.0000       150
         fluid_pound     0.9740    1.0000    0.9868       150
    gas_interference     1.0000    1.0000    1.0000       150
traveling_valve_leak     1.0000    1.0000    1.0000       150

            accuracy                         0.9947       750
           macro avg     0.9948    0.9947    0.9947       750
        weighted avg     0.9948    0.9947    0.9947       750

```

## 🎯 Confusion Matrix (Rows = Ground Truth, Columns = Predicted)

```
Classes: ['normal', 'rod_floating', 'fluid_pound', 'gas_interference', 'traveling_valve_leak']
[[150   0   0   0   0]
 [  0 150   0   0   0]
 [  4   0 146   0   0]
 [  0   0   0 150   0]
 [  0   0   0   0 150]]
```

---

## 🛡️ Reliability & Grey-Box Decision Logic

1. **Confidence Thresholding:** Telemetry with $\max P(\text{class}) < 0.70$ is tagged as `uncertain` to prevent false positive actuation.
2. **Grey-Box Consistency Verification:** The edge ML diagnosis is cross-checked against thermodynamic state variables (BHT, Andrade Viscosity, Fluid Pound Fillage). Any divergence flags an *"Unexplained Mechanical Discrepancy"*.
