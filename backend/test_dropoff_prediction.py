
from app.ai.dropoff_prediction import predict_dropoff_risk

test_features = {
    "case_age_days": 8,
    "days_in_current_status": 5,
    "status_history_matches_current_status": True,
    "case_status": "AWAITING_PATIENT",
    "case_priority": "HIGH",
    "overdue_tasks": 2,
    "unassigned_tasks": 1,
    "failed_notifications": 1,
    "no_show_appointments": 1,
    "pending_referrals": 1,
}

result = predict_dropoff_risk(test_features)

print("\nAHENDA PREDICTION TEST")
print("=====================")

for key, value in result.items():
    print(f"{key}: {value}")
