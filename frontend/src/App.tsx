
import {
  Activity,
  LayoutDashboard,
  Users,
  ClipboardList,
  Stethoscope,
  BrainCircuit,
  ArrowUpRight,
  Search,
  Bell,
  ChevronDown,
  Clock3,
  AlertTriangle,
  CheckCircle2,
  CircleDot,
  CalendarDays,
  Menu,
  HeartPulse,
  Settings,
  ShieldCheck,
} from 'lucide-react'
import './App.css'
import Login from "./components/Login";
import { useAuth } from "./context/AuthContext";
import { useEffect, useState } from "react";
import {
  getCareCoordinationDashboard,
  getLatestFacilityRiskAssessments,
  type DashboardData,
  type FacilityRiskAssessments,
} from "./services/api";


const navigation = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'Patients', icon: Users },
  { label: 'Screening Results', icon: ClipboardList },
  { label: 'Care Cases', icon: Stethoscope },
  { label: 'Tasks & Follow-ups', icon: CalendarDays },
  { label: 'AI Insights', icon: BrainCircuit },
]


function App() {
  const { isAuthenticated, token } = useAuth();

  const [dashboardData, setDashboardData] = useState<DashboardData | null>(
    null,
  );
  const [riskData, setRiskData] = useState<FacilityRiskAssessments | null>(
    null,
  );
  const [showRiskDetails, setShowRiskDetails] = useState(false);
  const [isDashboardLoading, setIsDashboardLoading] = useState(true);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [activePage, setActivePage] = useState("Overview");
  useEffect(() => {
    if (!isAuthenticated || !token) return;

    const authToken: string = token;
    let isActive = true;

    async function loadDashboard() {
      setIsDashboardLoading(true);
      setDashboardError(null);

      try {
        const data = await getCareCoordinationDashboard(authToken, 1);
        const risks = await getLatestFacilityRiskAssessments(authToken, 1);

        if (isActive) {
          setDashboardData(data);
          setRiskData(risks);
        }

      } catch (error) {
        if (isActive) {
          setDashboardError(
            error instanceof Error
              ? error.message
              : "Unable to load dashboard data.",
          );
        }
      } finally {
        if (isActive) {
          setIsDashboardLoading(false);
        }
      }
    }

    void loadDashboard();

    return () => {
      isActive = false;
    };
  }, [isAuthenticated, token]);
  const cases = dashboardData?.cases ?? [];

  if (!isAuthenticated) {
    return <Login />;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <HeartPulse size={25} />
          </div>
          <div>
            <h1>AHENDA</h1>
            <span>HEALTHCARE CONTINUITY</span>
          </div>
        </div>

        <div className="workspace-label">WORKSPACE</div>
        <nav className="navigation">
          {navigation.map((item) => {
            const Icon = item.icon;
            return (
              <button
                className={`nav-item ${activePage === item.label ? "active" : ""}`}
                key={item.label}
                onClick={() => setActivePage(item.label)}
              >
                <Icon size={19} />
                <span>{item.label}</span>
                {item.label === "AI Insights" && (
                  <span className="new-tag">AI</span>
                )}
              </button>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <div className="security-note">
            <ShieldCheck size={19} />
            <div>
              <strong>Secure workspace</strong>
              <span>Role-based access enabled</span>
            </div>
          </div>
          <button className="nav-item">
            <Settings size={19} />
            <span>Settings</span>
          </button>
          <div className="sidebar-footer">
            <span>AHENDA v1.0</span>
            <span>© 2026 AHENDA</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <button className="mobile-menu" aria-label="Open navigation">
            <Menu size={21} />
          </button>
          <div className="breadcrumb">
            Workspace <span></span> <strong>{activePage}</strong>
          </div>
          <div className="topbar-actions">
            <div className="facility-selector">
              <Activity size={17} />
              <span>Facility 01</span>
              <ChevronDown size={15} />
            </div>
            <button className="icon-button" aria-label="Search">
              <Search size={19} />
            </button>
            <button
              className="icon-button notification"
              aria-label="Notifications"
            >
              <Bell size={19} />
              <i />
            </button>
            <div className="profile">
              <div className="avatar">TC</div>
              <div className="profile-info">
                <strong>Test Clinician</strong>
                <span>Healthcare Professional</span>
              </div>
              <ChevronDown size={15} />
            </div>
          </div>
        </header>

        <div className="dashboard">
          {isDashboardLoading && (
            <div className="panel">Loading AHENDA dashboard data...</div>
          )}

          {dashboardError && (
            <div className="panel" role="alert">
              Unable to load dashboard: {dashboardError}
            </div>
          )}

          {activePage !== "Overview" && (
            <div className="page-placeholder">
              <h2>{activePage}</h2>
              <p>Welcome to the {activePage} workspace.</p>
            </div>

          )}
          <div style={{ display: activePage === "Overview" ? "block" : "none" }}></div>

              <section className="welcome-section">
                <div>
                  <div className="eyebrow">CARE COORDINATION CENTRE</div>
                  <h2>Good afternoon, Team.</h2>
                  <p>
                    Here's what's happening across your care coordination
                    workspace today.
                  </p>
                </div>
                <div className="date-display">
                  <CalendarDays size={17} />
                  November 18, 2026
                </div>
              </section>

          <section className="metrics-grid">
            <MetricCard
              label="Active Care Cases"
              value={
                dashboardData ? String(dashboardData.summary.active_cases) : "—"
              }
              note="Currently being coordinated"
              icon={HeartPulse}
              tone="blue"
              trend="Live overview"
            />
            <MetricCard
              label="Overdue Tasks"
              value={
                dashboardData
                  ? String(dashboardData.summary.overdue_tasks)
                  : "—"
              }
              note="Requires follow-up"
              icon={Clock3}
              tone="orange"
              trend="Needs attention"
            />
            <MetricCard
              label="Unassigned Cases"
              value={
                dashboardData
                  ? String(dashboardData.summary.unassigned_cases)
                  : "—"
              }
              note="All cases have an owner"
              icon={Users}
              tone="green"
              trend="On track"
            />
            <MetricCard
              label="Open Escalations"
              value={
                dashboardData
                  ? String(dashboardData.summary.open_escalations)
                  : "—"
              }
              note="Requires review"
              icon={AlertTriangle}
              tone="purple"
              trend="Active"
            />
          </section>

          <section className="insight-banner">
            <div className="insight-icon">
              <BrainCircuit size={23} />
            </div>

            <div className="insight-copy">
              <span>AHENDA INTELLIGENCE</span>
              <strong>Potential care delays need attention.</strong>
              <p>
                Operational risk signals have identified cases requiring
                follow-up review. Recommendations remain subject to healthcare
                professional approval.
              </p>
            </div>

            <button
              className="insight-button"
              onClick={() => setShowRiskDetails(true)}
            >
              Explore AI insights <ArrowUpRight size={16} />
            </button>
          </section>

          <section className="content-grid">
            <div className="panel cases-panel">
              <div className="panel-heading">
                <div>
                  <h3>Active care cases</h3>
                  <p>Monitor patient journeys and care ownership.</p>
                </div>

                <button className="text-button">
                  View all <ArrowUpRight size={15} />
                </button>
              </div>

              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>CASE / PATIENT</th>
                      <th>SCREENING TEST</th>
                      <th>URGENCY</th>
                      <th>STATUS</th>
                      <th>OWNER</th>
                    </tr>
                  </thead>

                  <tbody>
                    {cases.length > 0 ? (
                      cases.map((item) => (
                        <tr key={item.case_id}>
                          <td>
                            <strong>Case #{item.case_id}</strong>
                            <span className="sub-cell">Screening record</span>
                          </td>

                          <td>{item.test_name}</td>

                          <td>
                            <span
                              className={`urgency ${item.clinical_urgency.toLowerCase()}`}
                            >
                              <CircleDot size={12} />
                              {item.clinical_urgency}
                            </span>
                          </td>

                          <td>
                            <span className="status-pill">
                              {item.case_status}
                            </span>
                          </td>

                          <td>{item.current_owner || "Unassigned"}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td
                          colSpan={5}
                          style={{
                            textAlign: "center",
                            padding: "24px",
                          }}
                        >
                          {isDashboardLoading
                            ? "Loading care cases..."
                            : "No active care cases found."}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              <div className="panel-footer">
                <span>Demonstration records · Synthetic data</span>
                <span>Showing {cases.length} records</span>
              </div>
            </div>

            <div className="right-column">
              <div className="panel activity-panel">
                <div className="panel-heading">
                  <div>
                    <h3>AI risk overview</h3>
                    <p>Operational drop-off signals</p>
                  </div>

                  <BrainCircuit size={20} className="muted-icon" />
                </div>

                <div className="risk-score">
                  <div>
                    <span>
                      {riskData?.assessments
                        ?.find(
                          (a) =>
                            a.model_name === "AHENDA_RANDOM_FOREST_DROPOFF",
                        )
                        ?.risk_level?.replace("_", " ") ?? "NO ASSESSMENT"}
                    </span>
                    <strong>
                      {riskData?.assessments
                        ?.find(
                          (a) =>
                            a.model_name === "AHENDA_RANDOM_FOREST_DROPOFF",
                        )
                        ?.risk_score?.toFixed(2) ?? "N/A"}
                    </strong>
                    <small>Random Forest drop-off prediction</small>
                  </div>

                  <div className="risk-indicator">
                    <AlertTriangle size={25} />
                  </div>
                </div>

                <div className="risk-progress">
                  <div
                    style={{
                      width: `${(riskData?.assessments?.find((a) => a.model_name === "AHENDA_RANDOM_FOREST_DROPOFF")?.risk_score ?? 0) * 100}%`,
                    }}
                  />
                </div>

                <div className="risk-detail">
                  <span>Overdue tasks</span>
                  <strong>
                    {riskData?.assessments
                      ?.find(
                        (a) => a.model_name === "AHENDA_RANDOM_FOREST_DROPOFF",
                      )
                      ?.contributing_factors?.some((f) =>
                        f.factor.toLowerCase().includes("overdue"),
                      )
                      ? "Detected"
                      : "Not detected"}
                  </strong>
                </div>

                <div className="risk-detail">
                  <span>Prolonged case status</span>
                  <strong>
                    {riskData?.assessments
                      ?.find(
                        (a) => a.model_name === "AHENDA_RANDOM_FOREST_DROPOFF",
                      )
                      ?.contributing_factors?.some((f) =>
                        f.factor.toLowerCase().includes("status"),
                      )
                      ? "Detected"
                      : "Not detected"}
                  </strong>
                </div>

                <div className="risk-detail">
                  <span>Unassigned follow-up tasks</span>
                  <strong>
                    {riskData?.assessments
                      ?.find(
                        (a) => a.model_name === "AHENDA_RANDOM_FOREST_DROPOFF",
                      )
                      ?.contributing_factors?.some((f) =>
                        f.factor.toLowerCase().includes("unassigned"),
                      )
                      ? "Detected"
                      : "Not detected"}
                  </strong>
                </div>

                <div className="risk-detail">
                  <span>Model validation</span>
                  <strong>Not clinically validated</strong>
                </div>

                <button
                  className="full-width-button"
                  onClick={() => setShowRiskDetails(true)}
                >
                  Review risk assessments
                </button>
              </div>

              <div className="panel recommendations-panel">
                <div className="panel-heading">
                  <div>
                    <h3>Intervention queue</h3>
                    <p>Human-reviewed recommendations</p>
                  </div>

                  <span className="queue-count">
                    {dashboardData
                      ? dashboardData.summary.recommendations_pending_review
                      : "—"}
                  </span>
                </div>

                <div className="recommendation-item">
                  <div className="recommendation-icon">
                    <Clock3 size={17} />
                  </div>

                  <div>
                    <strong>Care recommendations</strong>
                    <span>Subject to professional review</span>
                  </div>
                </div>

                <div className="recommendation-footer">
                  <span>Awaiting approval</span>
                  <ArrowUpRight size={15} />
                </div>
              </div>
            </div>
          </section>
          {showRiskDetails && (
            <div className="panel" style={{ marginBottom: "24px" }}>
              <div className="panel-heading">
                <div>
                  <h3>Risk Assessment Details</h3>
                  <p>Latest AI-generated drop-off assessment</p>
                </div>
                <button
                  className="text-button"
                  onClick={() => setShowRiskDetails(false)}
                >
                  Close ✕
                </button>
              </div>

              {riskData?.assessments?.find(
                (a) => a.model_name === "AHENDA_RANDOM_FOREST_DROPOFF",
              ) ? (
                (() => {
                  const assessment = riskData.assessments.find(
                    (a) => a.model_name === "AHENDA_RANDOM_FOREST_DROPOFF",
                  );

                  if (!assessment) return null;

                  return (
                    <>
                      <div className="risk-detail">
                        <span>Case ID</span>
                        <strong>#{assessment.case_id}</strong>
                      </div>

                      <div className="risk-detail">
                        <span>Risk score</span>
                        <strong>{assessment.risk_score.toFixed(5)}</strong>
                      </div>

                      <div className="risk-detail">
                        <span>Risk level</span>
                        <strong>{assessment.risk_level}</strong>
                      </div>

                      <div className="risk-detail">
                        <span>Model</span>
                        <strong>{assessment.model_name}</strong>
                      </div>

                      <div className="risk-detail">
                        <span>Model version</span>
                        <strong>{assessment.model_version}</strong>
                      </div>

                      <h4 style={{ marginTop: "20px" }}>
                        Contributing factors
                      </h4>

                      {assessment.contributing_factors.map((factor, index) => (
                        <div className="risk-detail" key={index}>
                          <span>{factor.factor}</span>
                          <strong>
                            {factor.observed_value ?? factor.points ?? "—"}
                          </strong>
                        </div>
                      ))}

                      <div className="risk-detail">
                        <span>Assessed at</span>
                        <strong>
                          {new Date(assessment.assessed_at).toLocaleString()}
                        </strong>
                      </div>

                      <p
                        style={{
                          marginTop: "16px",
                          fontSize: "12px",
                          color: "#888",
                        }}
                      >
                        Demonstration assessment using synthetic data. This
                        model has not been clinically validated. Predictions are
                        decision-support signals, not clinical diagnoses.
                      </p>
                    </>
                  );
                })()
              ) : (
                <p>No Random Forest assessment is currently available.</p>
              )}
            </div>
          )}

          <section className="bottom-note">
            <div>
              <CheckCircle2 size={17} />
              <span>
                Every result tells a story. Every life deserves care that
                follows you all the way.
              </span>
            </div>
            <span>AHENDA · No Result Left Behind.</span>
          </section>

        </div>
      </main>
    </div>
  );
}

function MetricCard({
  label,
  value,
  note,
  icon: Icon,
  tone,
  trend,
}: {
  label: string
  value: string
  note: string
  icon: React.ElementType
  tone: string
  trend: string
}) {
  return (
    <div className="metric-card">
      <div className="metric-top">
        <span>{label}</span>
        <div className={`metric-icon ${tone}`}>
          <Icon size={19} />
        </div>
      </div>
      <div className="metric-value">{value}</div>
      <div className="metric-bottom">
        <span>{note}</span>
        <span className="metric-trend">{trend}</span>
      </div>
    </div>
  )
}

  

export default App


