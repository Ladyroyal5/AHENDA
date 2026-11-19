
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


RANDOM_STATE = 42
SAMPLE_COUNT = 3000

NUMERIC_FEATURES = [
    "case_age_days",
    "days_in_current_status",
    "has_due_date",
    "pending_tasks",
    "in_progress_tasks",
    "overdue_tasks",
    "unassigned_tasks",
    "completed_tasks",
    "pending_referrals",
    "unacknowledged_referrals",
    "rejected_referrals",
    "accepted_referrals",
    "completed_referrals",
    "no_show_appointments",
    "cancelled_appointments",
    "attended_appointments",
    "scheduled_appointments",
    "failed_notifications",
    "delivered_notifications",
    "pending_notifications",
    "sent_notifications",
    "understood_acknowledgements",
    "needs_clarification_acknowledgements",
    "unable_to_respond_acknowledgements",
    "received_acknowledgements",
]

CATEGORICAL_FEATURES = [
    "case_status",
    "case_priority",
]

FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def generate_synthetic_dataset(
    sample_count: int = SAMPLE_COUNT,
    random_state: int = RANDOM_STATE,
) -> pd.DataFrame:
    """
    Generate synthetic operational examples for a prototype.

    These examples are simulated, not real patient records
    or historical AHENDA outcomes.
    """

    rng = np.random.default_rng(random_state)

    data = {
        "case_age_days": rng.integers(0, 31, sample_count),
        "days_in_current_status": rng.integers(0, 15, sample_count),
        "has_due_date": rng.integers(0, 2, sample_count),
        "pending_tasks": rng.poisson(1.5, sample_count),
        "in_progress_tasks": rng.poisson(1.0, sample_count),
        "overdue_tasks": rng.poisson(0.7, sample_count),
        "unassigned_tasks": rng.poisson(0.5, sample_count),
        "completed_tasks": rng.poisson(2.0, sample_count),
        "pending_referrals": rng.poisson(0.6, sample_count),
        "unacknowledged_referrals": rng.poisson(0.4, sample_count),
        "rejected_referrals": rng.poisson(0.2, sample_count),
        "accepted_referrals": rng.poisson(0.7, sample_count),
        "completed_referrals": rng.poisson(0.5, sample_count),
        "no_show_appointments": rng.poisson(0.3, sample_count),
        "cancelled_appointments": rng.poisson(0.2, sample_count),
        "attended_appointments": rng.poisson(0.8, sample_count),
        "scheduled_appointments": rng.poisson(0.7, sample_count),
        "failed_notifications": rng.poisson(0.4, sample_count),
        "delivered_notifications": rng.poisson(1.2, sample_count),
        "pending_notifications": rng.poisson(0.4, sample_count),
        "sent_notifications": rng.poisson(0.8, sample_count),
        "understood_acknowledgements": rng.poisson(0.8, sample_count),
        "needs_clarification_acknowledgements": rng.poisson(0.3, sample_count),
        "unable_to_respond_acknowledgements": rng.poisson(0.2, sample_count),
        "received_acknowledgements": rng.poisson(0.7, sample_count),
    }

    data["case_status"] = rng.choice(
        [
            "OPEN",
            "IN_PROGRESS",
            "AWAITING_PATIENT",
            "AWAITING_FACILITY",
            "AWAITING_TEST",
            "AWAITING_APPOINTMENT",
            "UNDER_TREATMENT",
            "UNDER_SURVEILLANCE",
        ],
        sample_count,
    )

    data["case_priority"] = rng.choice(
        ["ROUTINE", "LOW", "HIGH", "URGENT"],
        sample_count,
    )

    df = pd.DataFrame(data)

    # Simulated operational outcome mechanism.
    # This creates prototype labels, not real-world evidence.
    risk_signal = (
        0.65 * df["overdue_tasks"]
        + 0.55 * df["unassigned_tasks"]
        + 0.65 * df["failed_notifications"]
        + 0.75 * df["unable_to_respond_acknowledgements"]
        + 0.45 * df["needs_clarification_acknowledgements"]
        + 0.75 * df["no_show_appointments"]
        + 0.75 * df["rejected_referrals"]
        + 0.35 * df["pending_referrals"]
        + 0.12 * df["case_age_days"]
        + 0.16 * df["days_in_current_status"]
        - 0.20 * df["completed_tasks"]
        - 0.20 * df["attended_appointments"]
        - 0.15 * df["understood_acknowledgements"]
    )

    # Convert the simulated signal into probabilities.
    probability = 1 / (1 + np.exp(-(risk_signal - 2.5)))
    probability = np.clip(probability, 0.02, 0.98)

    df["dropoff"] = rng.binomial(1, probability)

    return df


def train_model():
    df = generate_synthetic_dataset()

    X = df[FEATURE_COLUMNS]
    y = df["dropoff"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    preprocessing = ColumnTransformer(
        transformers=[
            (
                "numeric",
                StandardScaler(),
                NUMERIC_FEATURES,
            ),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL_FEATURES,
            ),
        ]
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessing", preprocessing),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=200,
                    max_depth=10,
                    min_samples_split=5,
                    min_samples_leaf=2,
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )

    pipeline.fit(X_train, y_train)

    predictions = pipeline.predict(X_test)
    probabilities = pipeline.predict_proba(X_test)[:, 1]

    print("\nAHENDA Random Forest prototype")
    print("--------------------------------")
    print("Training examples:", len(X_train))
    print("Testing examples:", len(X_test))
    print("Accuracy:", round(accuracy_score(y_test, predictions), 4))
    print("Synthetic holdout ROC-AUC:", round(
        roc_auc_score(y_test, probabilities), 4
    ))

    print("\nClassification report:")
    print(classification_report(y_test, predictions))

    model_package = {
        "pipeline": pipeline,
        "feature_columns": FEATURE_COLUMNS,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "model_name": "AHENDA_RANDOM_FOREST_DROPOFF",
        "model_version": "1.0.0",
        "training_data": "SYNTHETIC",
        "clinical_validation": False,
        "training_examples": SAMPLE_COUNT,
        "random_state": RANDOM_STATE,
    }

    model_path = Path(__file__).with_name("dropoff_model.joblib")
    joblib.dump(model_package, model_path)

    print("\nModel saved successfully:")
    print(model_path)


if __name__ == "__main__":
    train_model()
