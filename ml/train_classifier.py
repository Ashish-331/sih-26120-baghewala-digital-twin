import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
import os

def generate_dynacard(condition, num_points=100):
    position = np.concatenate([np.linspace(0, 100, num_points//2), np.linspace(100, 0, num_points//2)])
    load = np.zeros(num_points)
    W_r = 4800
    W_f = 9800

    if condition == "normal":
        load[0:20] = np.linspace(W_r, W_r + W_f, 20)
        load[20:50] = W_r + W_f + np.random.normal(0, 150, 30)
        load[50:70] = np.linspace(W_r + W_f, W_r, 20)
        load[70:100] = W_r + np.random.normal(0, 150, 30)
    elif condition == "rod_floating":
        load[0:20] = np.linspace(W_r, W_r + W_f, 20)
        load[20:50] = W_r + W_f + np.random.normal(0, 150, 30)
        load[50:80] = np.linspace(W_r + W_f, W_r + (W_f * 0.6), 30)
        load[80:100] = W_r + (W_f * 0.6) + np.random.normal(0, 150, 20)
    elif condition == "fluid_pound":
        load[0:20] = np.linspace(W_r, W_r + W_f, 20)
        load[20:50] = W_r + W_f + np.random.normal(0, 150, 30)
        load[50:60] = np.linspace(W_r + W_f, W_r + W_f, 10)
        load[60:65] = np.linspace(W_r + W_f, W_r, 5)
        load[65:100] = W_r + np.random.normal(0, 150, 35)

    return position, load

def extract_features(position, load):
    half = len(load) // 2
    area = abs(np.trapezoid(load[:half], position[:half]) + np.trapezoid(load[half:], position[half:]))
    peak_load = np.max(load)
    min_load = np.min(load)
    load_range = peak_load - min_load
    fill_ratio = (np.mean(load) - min_load) / load_range if load_range > 0 else 0
    return [area, peak_load, min_load, load_range, fill_ratio]

def main():
    np.random.seed(42)
    conditions = ["normal", "rod_floating", "fluid_pound"]
    X, y = [], []
    
    for cond in conditions:
        for _ in range(300):
            pos, load = generate_dynacard(cond)
            features = extract_features(pos, load)
            X.append(features)
            y.append(cond)
            
    clf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
    clf.fit(X, y)
    
    model_path = "/home/ashish/Desktop/SIH/ml/dynacard_rf_classifier.pkl"
    joblib.dump(clf, model_path)
    print(f"Model trained on 900 samples, saved to {model_path}")
    
    # Quick validation
    from sklearn.model_selection import cross_val_score
    scores = cross_val_score(clf, X, y, cv=5)
    print(f"5-fold CV accuracy: {scores.mean():.3f} ± {scores.std():.3f}")

if __name__ == "__main__":
    main()
