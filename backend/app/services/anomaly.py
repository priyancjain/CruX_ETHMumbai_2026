"""
Anomaly Detection Service — Pre-trained IsolationForest Model.

Uses a model trained on 21,000+ Virtuals agents to detect anomalous
wallet behaviour. The model + scaler are loaded once at import time.

Model:   IsolationForest (contamination=0.03, n_estimators=100)
Scaler:  StandardScaler (z-score normalisation)
Features: 13 signals (must match training order exactly)
"""

import os
import logging
import numpy as np
from joblib import load

logger = logging.getLogger("agentscore.services.anomaly")

# ── 13 features used during training — ORDER MUST MATCH EXACTLY ──────────────
ANOMALY_FEATURES = [
    "wallet_age_days",
    "tx_count_total",
    "tx_count_90d",
    "last_seen_at_days",
    "defi_protocol_count",
    "balance_eth",
    "erc20_token_count",
    "nft_count",
    "cross_chain_count",
    "virtuals_mcap_usd",
    "virtuals_holder_count",
    "virtuals_level",
    "is_active",
]

# ── Load pre-trained model + scaler at import time (once) ────────────────────
_MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
_MODEL_PATH = os.path.join(_MODEL_DIR, "anomaly_model.pkl")
_SCALER_PATH = os.path.join(_MODEL_DIR, "anomaly_scaler.pkl")

_model = None
_scaler = None

try:
    _model = load(_MODEL_PATH)
    _scaler = load(_SCALER_PATH)
    logger.info(
        f"[Anomaly] Pre-trained model loaded: "
        f"IsolationForest(contamination={_model.contamination}, "
        f"n_estimators={_model.n_estimators}) + StandardScaler({_scaler.n_features_in_} features)"
    )
except Exception as e:
    logger.error(f"[Anomaly] Failed to load pre-trained model: {e}")


def run_anomaly_detection(features: dict, historical_features: list[dict] = None) -> dict:
    """
    Run pre-trained IsolationForest anomaly detection on agent features.

    Flow:
      1. Extract 13 feature values from the agent's feature dict
      2. Scale using the pre-trained StandardScaler (z-score normalisation)
      3. Predict using the pre-trained IsolationForest model
      4. Return anomaly_score + is_anomaly flag + per-feature analysis

    Returns:
      {
        "anomaly_score": float,   # decision_function output (negative = more anomalous)
        "is_anomaly": bool,       # True if model predicts -1 (outlier)
        "feature_analysis": dict, # per-feature z-scores and contribution
      }
    """
    if _model is None or _scaler is None:
        logger.warning("[Anomaly] Model not loaded — skipping anomaly detection")
        return {"anomaly_score": 0.0, "is_anomaly": False, "feature_analysis": {}}

    try:
        # Step 1: Extract raw feature values (order must match training)
        raw_values = []
        for f in ANOMALY_FEATURES:
            val = features.get(f, 0)
            # Handle booleans: True→1, False→0
            if isinstance(val, bool):
                val = int(val)
            raw_values.append(float(val or 0))

        raw_array = np.array(raw_values).reshape(1, -1)

        # Step 2: Scale using pre-trained StandardScaler
        scaled_array = _scaler.transform(raw_array)

        # Step 3: Predict
        prediction = int(_model.predict(scaled_array)[0])    # 1=normal, -1=anomaly
        anomaly_score = float(_model.decision_function(scaled_array)[0])
        is_anomaly = prediction == -1

        # Step 4: Per-feature z-score analysis (for logging)
        z_scores = scaled_array[0]
        feature_analysis = {}
        for i, feat_name in enumerate(ANOMALY_FEATURES):
            z = float(z_scores[i])
            raw = raw_values[i]
            mean = float(_scaler.mean_[i])
            std = float(_scaler.scale_[i])

            # Flag features that deviate significantly (|z| > 2)
            if abs(z) > 3:
                severity = "EXTREME"
            elif abs(z) > 2:
                severity = "HIGH"
            elif abs(z) > 1:
                severity = "MODERATE"
            else:
                severity = "NORMAL"

            feature_analysis[feat_name] = {
                "raw_value": raw,
                "z_score": round(z, 3),
                "mean": round(mean, 3),
                "std": round(std, 3),
                "severity": severity,
            }

        # ── Detailed logging ──
        logger.info(f"\n  {'─'*70}")
        logger.info(f"  ML ANOMALY DETECTION — Pre-trained IsolationForest")
        logger.info(f"  Model: contamination={_model.contamination}, n_estimators={_model.n_estimators}")
        logger.info(f"  {'─'*70}")

        logger.info(f"\n  {'Feature':<25} {'Raw Value':<15} {'Z-Score':<10} {'Mean':<12} {'Severity'}")
        logger.info(f"  {'─'*75}")

        flagged_features = []
        for feat_name in ANOMALY_FEATURES:
            fa = feature_analysis[feat_name]
            raw_str = f"{fa['raw_value']:.2f}" if isinstance(fa['raw_value'], float) and fa['raw_value'] != int(fa['raw_value']) else str(int(fa['raw_value']))
            z_str = f"{fa['z_score']:+.3f}"
            mean_str = f"{fa['mean']:.2f}"
            sev = fa['severity']

            # Add visual indicator for flagged features
            flag = ""
            if sev == "EXTREME":
                flag = " <<< EXTREME OUTLIER"
            elif sev == "HIGH":
                flag = " << HIGH DEVIATION"
            elif sev == "MODERATE":
                flag = " < elevated"

            logger.info(f"  {feat_name:<25} {raw_str:<15} {z_str:<10} {mean_str:<12} {sev}{flag}")

            if sev in ("HIGH", "EXTREME"):
                direction = "above" if fa['z_score'] > 0 else "below"
                flagged_features.append(f"{feat_name} is {abs(fa['z_score']):.1f} std {direction} mean")

        logger.info(f"  {'─'*75}")
        logger.info(f"\n  DECISION FUNCTION SCORE: {anomaly_score:.6f}")
        logger.info(f"  PREDICTION:             {'ANOMALY (-1)' if is_anomaly else 'NORMAL (1)'}")

        if is_anomaly:
            logger.warning(f"  RESULT: ANOMALY DETECTED — Score will be CAPPED at Tier C (max 599)")
            if flagged_features:
                logger.warning(f"  REASON: {'; '.join(flagged_features)}")
        else:
            logger.info(f"  RESULT: Normal agent — no anomaly detected")

        if flagged_features:
            logger.info(f"\n  Flagged features ({len(flagged_features)}):")
            for ff in flagged_features:
                logger.info(f"    - {ff}")

        logger.info(f"  {'─'*70}\n")

        return {
            "anomaly_score": round(anomaly_score, 6),
            "is_anomaly": is_anomaly,
            "feature_analysis": feature_analysis,
        }

    except Exception as e:
        logger.error(f"[Anomaly] Detection failed: {e}", exc_info=True)
        return {"anomaly_score": 0.0, "is_anomaly": False, "feature_analysis": {}}
