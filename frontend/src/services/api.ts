const API_BASE_URL = "http://127.0.0.1:8000/api/v1";

type RequestOptions = RequestInit & {
  token?: string;
};

async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {},
): Promise<T> {
  const { token, headers, ...requestOptions } = options;

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...requestOptions,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail || `Request failed (${response.status})`);
  }

  return response.json() as Promise<T>;
}

export interface DashboardSummary {
  active_cases: number;
  overdue_tasks: number;
  unassigned_cases: number;
  open_escalations: number;
  recommendations_pending_review: number;
  recommendations_approved: number;
  recommendations_implemented: number;
  recommendations_rejected: number;
}

export interface DashboardCase {
  case_id: number;
  patient_reference: string;
  test_name: string;
  result_classification: string;
  clinical_urgency: string;
  case_status: string;
  case_priority: string;
  current_owner: string | null;
  next_task: string | null;
  task_due_at: string | null;
  pending_tasks_count: number;
  overdue_tasks_count: number;
  is_overdue: boolean;
  risk_score: number;
  risk_level: string;
  contributing_factors: Array<{
    factor: string;
    points: number;
  }>;
  risk_assessed_at: string | null;
  ml_risk_score: number | null;
  ml_risk_level: string | null;
  ml_training_data: string | null;
  ml_clinical_validation: boolean | null;
  intervention_recommendations: Array<{
    recommendation_id: number;
    recommendation_type: string;
    recommendation: string;
    recommendation_status: string;
    created_at: string;
    reviewed_at: string | null;
    executed_at: string | null;
  }>;
}

export interface DashboardData {
  summary: DashboardSummary;
  cases: DashboardCase[];
}

export function getCareCoordinationDashboard(token: string, facilityId = 1) {
  return apiRequest<DashboardData>(
    `/dashboard/care-coordination?facility_id=${facilityId}`,
    { token },
  );
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    public_id: string;
    first_name: string;
    last_name: string;
    email: string;
    account_type: string;
  };
}

export async function loginUser(
  email: string,
  password: string,
): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export interface RiskAssessment {
  assessment_id: number;
  case_id: number;
  risk_score: number;
  risk_level: string;
  model_name: string;
  model_version: string;
  contributing_factors: Array<{
    factor: string;
    points?: number;
    observed_value?: number;
  }>;
  assessed_at: string;
}

export interface FacilityRiskAssessments {
  facility_id: number;
  total: number;
  assessments: RiskAssessment[];
}

export function getLatestFacilityRiskAssessments(
  token: string,
  facilityId = 1,
) {
  return apiRequest<FacilityRiskAssessments>(
    `/risk-assessments/facility/latest?facility_id=${facilityId}`,
    { token },
  );
}