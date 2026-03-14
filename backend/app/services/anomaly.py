import logging
import numpy as np
from sklearn.ensemble import IsolationForest

logger = logging.getLogger("agentscore.services.anomaly")

# Features used for anomaly detection
ANOMALY_FEATURES = [
    "wallet_age_days",
    "tx_count_90d",
    "tvl_usd",
    "defi_protocol_count",
    "erc8004_reputation",
    "erc8004_job_count",
    "balance_eth",
    "heyelsa_risk_score",
    "total_pnl_usd",
    "win_rate",
]


def run_anomaly_detection(features: dict, historical_features: list[dict] = None) -> dict:
    """
    Run IsolationForest anomaly detection on agent features.

    For cold start (no historical data), returns is_anomaly=False.
    Once we have enough data, trains on historical features.
    """
    try:
        # Extract numeric feature values for this agent
        current = np.array(
            [float(features.get(f, 0) or 0) for f in ANOMALY_FEATURES]
        ).reshape(1, -1)

        # Cold start: need at least 10 samples to train meaningfully
        if not historical_features or len(historical_features) < 10:
            return {"anomaly_score": 0.0, "is_anomaly": False}

        # Build training matrix from historical data
        X = np.array(
            [
                [float(h.get(f, 0) or 0) for f in ANOMALY_FEATURES]
                for h in historical_features
            ]
        )

        # Add current agent to training data
        X_all = np.vstack([X, current])

        # Fit IsolationForest
        clf = IsolationForest(
            contamination=0.05,
            random_state=42,
            n_estimators=100,
        )
        clf.fit(X_all)

        # Score the current agent
        anomaly_score = float(clf.decision_function(current)[0])
        is_anomaly = bool(clf.predict(current)[0] == -1)

        return {
            "anomaly_score": anomaly_score,
            "is_anomaly": is_anomaly,
        }

    except Exception as e:
        logger.warning(f"Anomaly detection failed: {e}")
        return {"anomaly_score": 0.0, "is_anomaly": False}
