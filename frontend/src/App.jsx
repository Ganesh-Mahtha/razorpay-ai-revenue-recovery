import { useEffect, useMemo, useRef, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const ACTIONS = [
  "RETRY",
  "RETRY_WITH_CAUTION",
  "DO_NOT_RETRY",
  "HUMAN_REVIEW",
];

function formatCurrency(paise) {
  if (paise == null) return "—";

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(paise) / 100);
}

function formatRupees(value) {
  if (value == null) return "—";

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(value));
}

function formatPaymentId(id) {
  if (!id) return "—";

  return id.length <= 22
    ? id
    : `${id.slice(0, 11)}...${id.slice(-6)}`;
}

function actionLabel(action) {
  return action
    ? action.replaceAll("_", " ").toLowerCase()
    : "—";
}

function pct(value) {
  return `${Number(value ?? 0).toFixed(1)}%`;
}

function failureLabel(payment) {
  const text = String(
    payment?.error_description ||
      payment?.error_reason ||
      payment?.error_code ||
      ""
  ).toLowerCase();

  if (
    ["timeout", "network", "temporary"].some((x) =>
      text.includes(x)
    )
  ) {
    return "Temporary";
  }

  return payment?.status === "failed"
    ? "Failed"
    : "Unknown";
}

// ==================================================
// APP
// ==================================================

function App() {
  const [page, setPage] = useState("overview");

  const [payments, setPayments] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [analysis, setAnalysis] = useState(null);

  const [loadingPayments, setLoadingPayments] = useState(true);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);

  const [error, setError] = useState("");

  // Evaluation
  const [summary, setSummary] = useState(null);
  const [evaluationError, setEvaluationError] =
    useState("");
  const [uploading, setUploading] = useState(false);
  const [filename, setFilename] = useState("");

  const fileRef = useRef(null);

  // ==================================================
  // LOAD RAZORPAY PAYMENTS
  // ==================================================

  useEffect(() => {
    fetch(`${API_URL}/payments?count=100`)
      .then((response) => {
        if (!response.ok) {
          throw new Error(
            "Unable to load payments."
          );
        }

        return response.json();
      })
      .then((data) => {
        const items =
          data?.items || data || [];

        setPayments(items);

        const firstFailed = items.find(
          (payment) =>
            payment.status === "failed"
        );

        setSelectedId(
          firstFailed?.id || null
        );
      })
      .catch((err) => {
        console.error(err);

        setError(
          "Could not connect to RecoverAI. Make sure FastAPI is running on port 8000."
        );
      })
      .finally(() => {
        setLoadingPayments(false);
      });
  }, []);

  // ==================================================
  // LOAD LATEST EVALUATION
  // ==================================================

  useEffect(() => {
    fetch(`${API_URL}/evaluation/summary`)
      .then((response) => response.json())
      .then((data) => {
        if (
          data?.available &&
          data?.summary
        ) {
          setSummary(data.summary);
          setFilename(
            data.filename || ""
          );
        }
      })
      .catch(() => {});
  }, []);

  // ==================================================
// ANALYZE SELECTED PAYMENT
// ==================================================

useEffect(() => {
  if (!selectedId) {
    return;
  }

  let cancelled = false;

  const analyzePayment = async () => {
    try {
      // Defer this state update so React's
      // set-state-in-effect lint rule is satisfied.
      if (!cancelled) {
        setLoadingAnalysis(true);
      }

      const response = await fetch(
        `${API_URL}/payments/${selectedId}/analyze`
      );

      if (!response.ok) {
        throw new Error(
          "Unable to analyze payment."
        );
      }

      const data = await response.json();

      if (!cancelled) {
        setAnalysis(data);
        setLoadingAnalysis(false);
      }
    } catch (err) {
      console.error(err);

      if (!cancelled) {
        setAnalysis(null);
        setLoadingAnalysis(false);

        setError(
          "Unable to analyze the selected payment."
        );
      }
    }
  };

  queueMicrotask(analyzePayment);

  return () => {
    cancelled = true;
  };
}, [selectedId]);
  // ==================================================
  // DERIVED PAYMENT DATA
  // ==================================================

  const failedPayments = useMemo(
    () =>
      payments.filter(
        (payment) =>
          payment.status === "failed"
      ),
    [payments]
  );

  const failedValue = useMemo(
    () =>
      failedPayments.reduce(
        (total, payment) =>
          total + (payment.amount || 0),
        0
      ),
    [failedPayments]
  );

  const selectedPayment = useMemo(
    () =>
      payments.find(
        (payment) =>
          payment.id === selectedId
      ) || null,
    [payments, selectedId]
  );

  // ==================================================
  // NAVIGATION
  // ==================================================

  function selectPayment(
    id,
    destination = "workspace"
  ) {
    setSelectedId(id);
    setPage(destination);
  }

  // ==================================================
  // CSV UPLOAD
  // ==================================================

  async function uploadCsv(file) {
    if (!file) return;

    setUploading(true);
    setEvaluationError("");

    try {
      const body = new FormData();

      body.append("file", file);

      const response = await fetch(
        `${API_URL}/evaluation/upload`,
        {
          method: "POST",
          body,
        }
      );

      const data =
        await response.json();

      if (
        !response.ok ||
        !data?.available ||
        !data?.summary
      ) {
        throw new Error(
          data?.message ||
            "The evaluation upload could not be completed."
        );
      }

      setSummary(data.summary);

      setFilename(
        data.filename || file.name
      );

      setPage("evaluation");
    } catch (err) {
      console.error(err);

      setEvaluationError(
        err?.message ||
          "Unable to upload the CSV. Make sure FastAPI is running."
      );
    } finally {
      setUploading(false);

      if (fileRef.current) {
        fileRef.current.value = "";
      }
    }
  }

  // ==================================================
  // INITIAL LOADING
  // ==================================================

  if (
    loadingPayments &&
    payments.length === 0
  ) {
    return (
      <div className="app-shell">
        <Sidebar
          activePage={page}
          navigate={setPage}
        />

        <main className="main">
          <header className="topbar">
            <div>
              <div className="breadcrumb">
                RecoverAI
              </div>

              <h1>Overview</h1>
            </div>

            <div className="topbar-right">
              <div className="connection">
                <span className="status-dot" />
                Connecting to Razorpay
              </div>

              <div className="top-avatar">
                G
              </div>
            </div>
          </header>

          <div className="content">
            <div
              className="card"
              style={{ padding: 40 }}
            >
              Loading RecoverAI data...
            </div>
          </div>
        </main>
      </div>
    );
  }

  // ==================================================
  // MAIN APP
  // ==================================================

  return (
    <div className="app-shell">
      <Sidebar
        activePage={page}
        navigate={setPage}
      />

      <main className="main">
        <header className="topbar">
          <div>
            <div className="breadcrumb">
              RecoverAI{" "}
              <span>/</span>{" "}
              {pageTitle(page)}
            </div>

            <h1>
              {pageTitle(page)}
            </h1>
          </div>

          <div className="topbar-right">
            <div className="connection">
              <span className="status-dot" />
              Razorpay connected
            </div>

            <div className="top-avatar">
              G
            </div>
          </div>
        </header>

        {error && (
          <Alert>{error}</Alert>
        )}

        {page === "overview" && (
          <Overview
            failedPayments={
              failedPayments
            }
            failedValue={failedValue}
            analysis={analysis}
            selectedPayment={
              selectedPayment
            }
            loadingAnalysis={
              loadingAnalysis
            }
            navigate={setPage}
            selectPayment={
              selectPayment
            }
            summary={summary}
            filename={filename}
          />
        )}

        {page === "opportunities" && (
          <Opportunities
            payments={failedPayments}
            selectedId={selectedId}
            selectPayment={
              selectPayment
            }
          />
        )}

        {page === "workspace" && (
          <Workspace
            analysis={analysis}
            payment={selectedPayment}
            loading={loadingAnalysis}
            navigate={setPage}
          />
        )}

        {page === "results" && (
          <Results
            analysis={analysis}
            payment={selectedPayment}
            navigate={setPage}
          />
        )}

        {page === "evaluation" && (
          <EvaluationImpact
            summary={summary}
            filename={filename}
            uploading={uploading}
            error={evaluationError}
            fileRef={fileRef}
            onFile={(event) =>
              uploadCsv(
                event.target.files?.[0]
              )
            }
            chooseFile={() =>
              fileRef.current?.click()
            }
          />
        )}
      </main>
    </div>
  );
}

// ==================================================
// ALERT
// ==================================================

function Alert({ children }) {
  return (
    <div
      style={{
        margin: "16px 42px 0",
        padding: "12px 15px",
        background: "#fef3f2",
        border: "1px solid #fecdca",
        borderRadius: 8,
        color: "#b42318",
        fontSize: 12,
      }}
    >
      {children}
    </div>
  );
}

// ==================================================
// SIDEBAR
// ==================================================

function Sidebar({
  activePage,
  navigate,
}) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">
          R
        </div>

        <div>
          <div className="brand-name">
            RecoverAI
          </div>

          <div className="brand-subtitle">
            Revenue recovery
          </div>
        </div>
      </div>

      <div className="sidebar-section">
        <div className="sidebar-label">
          WORKSPACE
        </div>

        <NavItem
          icon="⌂"
          label="Overview"
          active={
            activePage === "overview"
          }
          onClick={() =>
            navigate("overview")
          }
        />

        <NavItem
          icon="↗"
          label="Recovery Opportunities"
          active={
            activePage ===
            "opportunities"
          }
          onClick={() =>
            navigate("opportunities")
          }
        />

        <NavItem
          icon="◇"
          label="Decision Workspace"
          active={
            activePage === "workspace"
          }
          onClick={() =>
            navigate("workspace")
          }
        />

        <NavItem
          icon="✓"
          label="Recovery Results"
          active={
            activePage === "results"
          }
          onClick={() =>
            navigate("results")
          }
        />

        <NavItem
          icon="▣"
          label="Evaluation & Impact"
          active={
            activePage ===
            "evaluation"
          }
          onClick={() =>
            navigate("evaluation")
          }
        />
      </div>

      <div className="sidebar-bottom">
        <div className="engine-status">
          <span className="status-dot" />

          <div>
            <strong>
              Recovery engine
            </strong>

            <small>
              Operational
            </small>
          </div>
        </div>

        <div className="merchant">
          <div className="merchant-avatar">
            M
          </div>

          <div>
            <strong>
              Merchant account
            </strong>

            <small>
              Razorpay connected
            </small>
          </div>
        </div>
      </div>
    </aside>
  );
}

// ==================================================
// NAV ITEM
// ==================================================

function NavItem({
  icon,
  label,
  active,
  onClick,
}) {
  return (
    <button
      type="button"
      className={`nav-item ${
        active ? "active" : ""
      }`}
      onClick={onClick}
    >
      <span>{icon}</span>
      {label}
    </button>
  );
}

// ==================================================
// OVERVIEW
// ==================================================

function Overview({
  failedPayments,
  analysis,
  selectedPayment,
  loadingAnalysis,
  navigate,
  selectPayment,
  summary,
  filename,
}) {
  const revenue =
    summary?.revenue || {};

  const recovery =
    summary?.recovery || {};

  const safety =
    summary?.safety || {};

  const aiSafety =
    summary?.ai_safety || {};

  const policy =
    summary?.policy || {};

  const accuracy =
    summary?.accuracy || {};

  const hasEvaluation =
    Boolean(summary);

  return (
    <div className="content">

      {/* HERO */}

      <section className="hero-section">
        <div>
          <div className="eyebrow">
            RECOVERY INTELLIGENCE
          </div>

          <h2>
            Recover revenue with better
            decisions.
          </h2>

          <p>
            RecoverAI analyzes failed
            payments, customer history
            and recovery signals to
            identify the safest next
            action.
          </p>
        </div>

        <button
          className="primary-button"
          onClick={() =>
            navigate("opportunities")
          }
        >
          View opportunities →
        </button>
      </section>

      {/* REVENUE IMPACT */}

      <section className="overview-impact-section">
        <div className="overview-section-header">
          <div>
            <div className="eyebrow">
              REVENUE IMPACT
            </div>

            <h3>
              Recovery value at a glance.
            </h3>

            <p>
              Business impact calculated
              from the latest evaluation.
            </p>
          </div>

          <button
            className="text-button"
            onClick={() =>
              navigate("evaluation")
            }
          >
            View full evaluation →
          </button>
        </div>

        {hasEvaluation ? (
          <>
            <div className="stats-grid">
              <Impact
                label="Revenue at risk"
                value={formatRupees(
                  revenue.total_at_risk
                )}
                note="total payment value evaluated"
              />

              <Impact
                label="Recoverable revenue"
                value={formatRupees(
                  revenue.recoverable_at_risk
                )}
                note="revenue classified as recoverable"
              />

              <Impact
                featured
                label="Recovery opportunity"
                value={formatRupees(
                  revenue.recovery_opportunity
                )}
                note={`${pct(
                  revenue.opportunity_rate
                )} opportunity rate`}
              />

              <Impact
                label="Safely blocked"
                value={formatRupees(
                  revenue.safely_blocked
                )}
                note="non-recoverable revenue protected"
              />
            </div>

            {filename && (
              <div className="overview-source">
                <span>
                  Latest evaluation
                </span>

                <strong>
                  {filename}
                </strong>

                <span>
                  {summary.total_cases ??
                    0}{" "}
                  cases
                </span>
              </div>
            )}
          </>
        ) : (
          <div className="card overview-empty-state">
            <div>
              <div className="eyebrow">
                NO EVALUATION DATA
              </div>

              <h3>
                Upload a batch to see
                revenue impact.
              </h3>

              <p>
                Run an evaluation to
                calculate recovery
                opportunity, recoverable
                revenue and safety
                metrics.
              </p>
            </div>

            <button
              className="primary-button"
              onClick={() =>
                navigate("evaluation")
              }
            >
              Upload evaluation CSV →
            </button>
          </div>
        )}
      </section>

      {/* RECOVERY PERFORMANCE */}

      {hasEvaluation && (
        <MetricSection title="RECOVERY PERFORMANCE">
          <div className="dashboard-grid">
            <Metric
              label="Recoverable cases"
              value={
                recovery.recoverable_cases ??
                0
              }
              note="cases classified as recoverable"
            />

            <Metric
              label="Retry opportunities"
              value={
                recovery.retry_opportunities ??
                0
              }
              note="cases receiving retry opportunity"
            />

            <Metric
              featured
              label="Recovery recall"
              value={pct(
                recovery.recall
              )}
              note="recoverable cases captured"
            />
          </div>
        </MetricSection>
      )}

      {/* SAFETY */}

      {hasEvaluation && (
        <MetricSection title="SAFETY">
          <div className="dashboard-grid">
            <Metric
              featured
              label="Safety rate"
              value={pct(
                safety.safety_rate
              )}
              note="unsafe automatic retries prevented"
            />

            <Metric
              label="Unsafe final retries"
              value={
                safety.unsafe_final_retries ??
                0
              }
              note="target: zero"
            />

            <Metric
              label="Non-recoverable cases"
              value={
                safety.non_recoverable_cases ??
                0
              }
              note="cases requiring safe handling"
            />
          </div>
        </MetricSection>
      )}

      {/* AI / POLICY */}

      {hasEvaluation && (
        <MetricSection title="AI / POLICY">
          <div className="dashboard-grid">
            <Metric
              label="AI accuracy"
              value={pct(
                accuracy.ai
              )}
              note="AI vs expected action"
            />

            <Metric
              label="Policy agreement"
              value={pct(
                policy.agreement_rate
              )}
              note={`${policy.ai_policy_agreements ?? 0} agreements`}
            />

            <Metric
              label="Decisions changed downstream"
              value={pct(
                policy.decision_change_rate
              )}
              note={`${policy.decisions_changed ?? 0} decisions changed`}
            />

            <Metric
              label="AI unsafe recommendations"
              value={
                aiSafety.unsafe_recommendations ??
                0
              }
              note="unsafe AI retry recommendations"
            />
          </div>
        </MetricSection>
      )}

      {/* LIVE RAZORPAY */}

      <section className="overview-live-section">
        <div className="overview-section-header">
          <div>
            <div className="eyebrow">
              LIVE RAZORPAY OPPORTUNITY
            </div>

            <h3>
              Payment needs attention.
            </h3>

            <p>
              Select a real failed
              Razorpay payment to inspect
              its recovery decision.
            </p>
          </div>

          <button
            className="text-button"
            onClick={() =>
              navigate("opportunities")
            }
          >
            View all →
          </button>
        </div>

        <section className="dashboard-grid">
          <div className="card opportunity-card">
            <div className="card-header">
              <div>
                <div className="eyebrow">
                  TOP OPPORTUNITY
                </div>

                <h3>
                  Payment needs attention
                </h3>
              </div>

              <span className="badge warning">
                {analysis?.score?.tier ||
                  "—"}
              </span>
            </div>

            <div className="payment-row">
              <div>
                <div className="field-label">
                  PAYMENT
                </div>

                <strong>
                  {formatPaymentId(
                    selectedPayment?.id
                  )}
                </strong>
              </div>

              <div className="amount">
                {formatCurrency(
                  selectedPayment?.amount
                )}
              </div>
            </div>

            <div className="score-section">
              <div className="score-ring">
                <strong>
                  {analysis?.score?.score ??
                    "—"}
                </strong>

                <span>
                  / 100
                </span>
              </div>

              <div className="score-copy">
                <div className="field-label">
                  RECOVERY SCORE
                </div>

                <strong>
                  {loadingAnalysis
                    ? "Analyzing..."
                    : analysis?.recommendation
                        ?.title ||
                      "Awaiting analysis"}
                </strong>

                <p>
                  {analysis?.recommendation
                    ?.reason ||
                    "RecoverAI is evaluating this payment."}
                </p>
              </div>
            </div>

            <button
              className="secondary-button full"
              disabled={
                !selectedPayment
              }
              onClick={() =>
                selectedPayment &&
                selectPayment(
                  selectedPayment.id,
                  "workspace"
                )
              }
            >
              Open decision workspace →
            </button>
          </div>

          <Signals
            analysis={analysis}
          />
        </section>
      </section>

      {/* RECENT ACTIVITY */}

      <Activity
        payments={failedPayments.slice(
          0,
          5
        )}
        navigate={navigate}
      />
    </div>
  );
}

// ==================================================
// OVERVIEW COMPONENTS
// ==================================================

function Impact({
  label,
  value,
  note,
  featured,
}) {
  return (
    <div
      className="stat-card"
      style={
        featured
          ? {
              border:
                "1px solid #b8c7e8",
              boxShadow:
                "0 4px 16px rgba(16,42,90,.08)",
            }
          : undefined
      }
    >
      <div className="stat-label">
        {label}
      </div>

      <div
        className="stat-value"
        style={
          featured
            ? { fontSize: 28 }
            : undefined
        }
      >
        {value}
      </div>

      <div className="stat-change">
        {note}
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  note,
  featured,
}) {
  return (
    <div
      className="card"
      style={{
        padding: 22,
        minHeight: 120,
        border: featured
          ? "1px solid #b8c7e8"
          : undefined,
      }}
    >
      <div className="stat-label">
        {label}
      </div>

      <div
        style={{
          marginTop: 10,
          fontSize: 25,
          fontWeight: 800,
          color: "#101828",
        }}
      >
        {value}
      </div>

      <div
        style={{
          marginTop: 8,
          fontSize: 11,
          color: "#98a2b3",
        }}
      >
        {note}
      </div>
    </div>
  );
}

function MetricSection({
  title,
  children,
}) {
  return (
    <section
      style={{
        marginBottom: 24,
      }}
    >
      <div className="eyebrow">
        {title}
      </div>

      {children}
    </section>
  );
}

function Signals({ analysis }) {
  const signals =
    analysis?.ai_assessment?.signals ||
    analysis?.diagnosis?.signals ||
    [];

  return (
    <div className="card signals-card">
      <div className="eyebrow">
        AI SIGNALS
      </div>

      <h3>
        Why this payment matters
      </h3>

      <div className="signals-list">
        {signals.length ? (
          signals.map(
            (signal, index) => (
              <div
                className="signal"
                key={index}
              >
                <span className="signal-check">
                  ✓
                </span>

                {typeof signal ===
                "string"
                  ? signal
                  : signal?.interpretation ||
                    signal?.value ||
                    JSON.stringify(
                      signal
                    )}
              </div>
            )
          )
        ) : (
          <div className="signal">
            Waiting for payment
            analysis...
          </div>
        )}
      </div>
    </div>
  );
}

function Activity({
  payments,
  navigate,
}) {
  return (
    <div className="card activity-card">
      <div className="card-header">
        <div>
          <div className="eyebrow">
            RECENT ACTIVITY
          </div>

          <h3>
            Failed payment opportunities
          </h3>
        </div>

        <button
          className="text-button"
          onClick={() =>
            navigate("opportunities")
          }
        >
          View all →
        </button>
      </div>

      <div className="table">
        <div className="table-row table-head">
          <div>PAYMENT</div>
          <div>AMOUNT</div>
          <div>FAILURE</div>
          <div>STATUS</div>
          <div>RECOVERY</div>
        </div>

        {payments.map((payment) => (
          <div
            className="table-row"
            key={payment.id}
          >
            <div className="payment-id">
              {formatPaymentId(
                payment.id
              )}
            </div>

            <div>
              {formatCurrency(
                payment.amount
              )}
            </div>

            <div>
              <span className="badge warning">
                {failureLabel(
                  payment
                )}
              </span>
            </div>

            <div>—</div>

            <div>
              Analyze payment
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ==================================================
// RECOVERY OPPORTUNITIES
// ==================================================

function Opportunities({
  payments,
  selectedId,
  selectPayment,
}) {
  return (
    <div className="content">
      <section className="page-intro">
        <div>
          <div className="eyebrow">
            RECOVERY OPPORTUNITIES
          </div>

          <h2>
            Failed payments worth
            reviewing.
          </h2>

          <p>
            Review real failed Razorpay
            payments and send them
            through the RecoverAI
            decision pipeline.
          </p>
        </div>

        <div className="opportunity-summary">
          <span>
            {payments.length}
          </span>

          <small>
            payments to review
          </small>
        </div>
      </section>

      <div className="opportunity-list">
        {payments.map((payment) => (
          <div
            className={`card opportunity-card ${
              payment.id === selectedId
                ? "selected"
                : ""
            }`}
            key={payment.id}
          >
            <div className="opportunity-main">
              <div className="opportunity-payment">
                <div className="field-label">
                  PAYMENT
                </div>

                <strong>
                  {formatPaymentId(
                    payment.id
                  )}
                </strong>

                <span className="opportunity-source">
                  Razorpay payment
                </span>
              </div>

              <div className="opportunity-amount">
                <div className="field-label">
                  AMOUNT
                </div>

                <strong>
                  {formatCurrency(
                    payment.amount
                  )}
                </strong>
              </div>

              <div className="opportunity-failure">
                <div className="field-label">
                  FAILURE TYPE
                </div>

                <span className="badge warning">
                  {failureLabel(
                    payment
                  )}
                </span>
              </div>

              <div className="opportunity-score">
                <div className="field-label">
                  RECOVERY
                </div>

                <strong>—</strong>

                <span>
                  Awaiting analysis
                </span>
              </div>

              <button
                className="primary-button opportunity-action"
                onClick={() =>
                  selectPayment(
                    payment.id,
                    "workspace"
                  )
                }
              >
                Analyze payment →
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ==================================================
// TRACE STEP
// ==================================================

function TraceStep({
  number,
  title,
  value,
  detail,
  status = "complete",
}) {
  return (
    <div
      className={`trace-step trace-${status}`}
    >
      <div className="trace-step-number">
        {number}
      </div>

      <div className="trace-step-content">
        <div className="trace-step-title">
          {title}
        </div>

        <strong>
          {value || "—"}
        </strong>

        <p>
          {detail || "—"}
        </p>
      </div>

      <div className="trace-step-status">
        {status === "complete"
          ? "✓"
          : status === "warning"
            ? "!"
            : "•"}
      </div>
    </div>
  );
}

// ==================================================
// TRACE CONNECTOR
// ==================================================

function TraceConnector() {
  return (
    <div className="trace-connector">
      <span />
    </div>
  );
}

// ==================================================
// DECISION WORKSPACE
// ==================================================

function Workspace({
  analysis,
  payment,
  loading,
  navigate,
}) {
  if (!payment) {
    return (
      <div className="content">
        <section className="page-intro">
          <div>
            <div className="eyebrow">
              DECISION WORKSPACE
            </div>

            <h2>
              Select a payment to review.
            </h2>

            <p>
              Choose a failed payment
              from Recovery Opportunities.
            </p>
          </div>

          <button
            className="primary-button"
            onClick={() =>
              navigate("opportunities")
            }
          >
            View opportunities →
          </button>
        </section>
      </div>
    );
  }

  const ai =
    analysis?.ai_assessment || {};

  const score =
    analysis?.score || {};

  const recommendation =
    analysis?.recommendation || {};

  const guardrail =
    analysis?.guardrail || {};

  const execution =
    analysis?.execution || {};

  const audit =
    analysis?.audit_trail || {};

  const signals =
    ai?.signals ||
    analysis?.diagnosis?.signals ||
    [];

  const aiAction =
    ai?.recommended_action ||
    "—";

  const policyAction =
    recommendation?.action ||
    score?.recommended_action ||
    "—";

  const reconciledAction =
    analysis?.reconciled_action ||
    "—";

  const finalAction =
    guardrail?.action ||
    execution?.action ||
    reconciledAction ||
    policyAction ||
    "—";

  const isGuardrailTriggered =
    Boolean(
      guardrail?.guardrail_triggered
    );

  return (
    <div className="content">

      {/* PAGE HEADER */}

      <section className="page-intro">
        <div>
          <div className="eyebrow">
            DECISION WORKSPACE
          </div>

          <h2>
            Review this recovery
            decision.
          </h2>

          <p>
            RecoverAI evaluates payment
            history, failure signals and
            guardrails before
            recommending the safest
            action.
          </p>
        </div>

        <button
          className="secondary-button"
          onClick={() =>
            navigate("opportunities")
          }
        >
          ← Back to opportunities
        </button>
      </section>

      {/* PAYMENT HEADER */}

      <div className="card decision-card">
        <div className="decision-top">
          <div>
            <div className="field-label">
              PAYMENT
            </div>

            <h3>
              {formatPaymentId(
                payment.id
              )}
            </h3>
          </div>

          <div className="decision-amount">
            {formatCurrency(
              payment.amount
            )}
          </div>
        </div>
      </div>

      {/* ==================================================
          DECISION TRACE
          ================================================== */}

      <div className="card decision-trace-card">
        <div className="decision-trace-header">
          <div>
            <div className="eyebrow">
              DECISION TRACE
            </div>

            <h3>
              From AI recommendation to
              bounded, auditable action
            </h3>

            <p>
              Every stage is evaluated
              before a recovery action can
              be executed.
            </p>
          </div>

          <span className="trace-status">
            {audit?.audit_id
              ? "Decision recorded"
              : loading
                ? "Analyzing"
                : "Decision bounded"}
          </span>
        </div>

        <div className="decision-trace">

          {/* 01 */}

          <TraceStep
            number="01"
            title="AI assessment"
            value={aiAction}
            detail={
              ai?.reasoning ||
              ai?.diagnosis ||
              "AI assessment is being prepared."
            }
            status={
              aiAction !== "—"
                ? "complete"
                : "pending"
            }
          />

          <TraceConnector />

          {/* 02 */}

          <TraceStep
            number="02"
            title="Deterministic policy"
            value={policyAction}
            detail={
              score?.reasons?.join(
                " · "
              ) ||
              `Score ${
                score?.score ?? "—"
              }/100 · ${
                score?.tier || "—"
              }`
            }
            status={
              score?.score != null
                ? "complete"
                : "pending"
            }
          />

          <TraceConnector />

          {/* 03 */}

          <TraceStep
            number="03"
            title="Policy reconciliation"
            value={reconciledAction}
            detail={
              analysis?.reconciliation_reason ||
              "AI recommendation and deterministic policy are reconciled."
            }
            status={
              analysis?.reconciled_action
                ? "complete"
                : "pending"
            }
          />

          <TraceConnector />

          {/* 04 */}

          <TraceStep
            number="04"
            title="Safety guardrail"
            value={
              isGuardrailTriggered
                ? "HUMAN REVIEW"
                : "PASSED"
            }
            detail={
              guardrail?.guardrail_reasons?.join(
                " · "
              ) ||
              guardrail?.reason ||
              "Safety boundaries evaluated."
            }
            status={
              guardrail
                ? isGuardrailTriggered
                  ? "warning"
                  : "complete"
                : "pending"
            }
          />

          <TraceConnector />

          {/* 05 */}

          <TraceStep
            number="05"
            title="Bounded execution"
            value={
              execution?.action ||
              "—"
            }
            detail={
              execution?.message ||
              "Waiting for bounded execution."
            }
            status={
              execution
                ? execution?.executed
                  ? "complete"
                  : "warning"
                : "pending"
            }
          />

          <TraceConnector />

          {/* 06 — AUDIT */}

          <TraceStep
            number="06"
            title="Audit trail"
            value={
              audit?.audit_id
                ? "RECORDED"
                : "—"
            }
            detail={
              audit?.audit_id
                ? `Audit ID ${audit.audit_id}`
                : loading
                  ? "Generating audit record..."
                  : "Audit record unavailable."
            }
            status={
              audit?.audit_id
                ? "complete"
                : "pending"
            }
          />
        </div>
      </div>

      {/* ==================================================
          MAIN WORKSPACE
          ================================================== */}

      <div className="workspace-grid">

        <div className="decision-main">

          {/* RECOVERY DECISION */}

          <div className="card decision-card">
            <div className="eyebrow">
              RECOVERY DECISION
            </div>

            <div className="decision-score">
              <div className="score-ring large">
                <strong>
                  {score?.score ??
                    "—"}
                </strong>

                <span>
                  / 100
                </span>
              </div>

              <div>
                <div className="field-label">
                  RECOMMENDED ACTION
                </div>

                <h3>
                  {loading
                    ? "Analyzing..."
                    : recommendation?.title ||
                      actionLabel(
                        finalAction
                      )}
                </h3>

                <p>
                  {recommendation?.reason ||
                    "RecoverAI is evaluating this payment."}
                </p>
              </div>
            </div>
          </div>

          {/* AI VS POLICY */}

          <div className="card comparison-card">
            <div className="eyebrow">
              AI VS POLICY
            </div>

            <h3>
              How the final action was
              determined
            </h3>

            <div className="comparison-grid">

              <div className="comparison-item">
                <span>
                  AI RECOMMENDATION
                </span>

                <strong>
                  {actionLabel(
                    aiAction
                  )}
                </strong>

                <small>
                  {ai?.reasoning ||
                    ai?.diagnosis ||
                    "No AI reasoning available."}
                </small>
              </div>

              <div className="comparison-arrow">
                →
              </div>

              <div className="comparison-item">
                <span>
                  DETERMINISTIC POLICY
                </span>

                <strong>
                  {actionLabel(
                    policyAction
                  )}
                </strong>

                <small>
                  {score?.reasons?.join(
                    " · "
                  ) ||
                    "Policy evidence evaluated."}
                </small>
              </div>

              <div className="comparison-arrow">
                →
              </div>

              <div className="comparison-item final-comparison">
                <span>
                  FINAL ACTION
                </span>

                <strong>
                  {actionLabel(
                    finalAction
                  )}
                </strong>

                <small>
                  {analysis?.reconciliation_reason ||
                    guardrail?.reason ||
                    "Final action bounded by safety policy."}
                </small>
              </div>
            </div>
          </div>

          {/* DIAGNOSIS */}

          <div className="card diagnosis-card">
            <div className="eyebrow">
              DIAGNOSIS
            </div>

            <h3>
              Why RecoverAI reached this
              decision
            </h3>

            <p>
              {ai?.diagnosis ||
                ai?.reasoning ||
                recommendation?.reason ||
                "The payment analysis is being prepared."}
            </p>
          </div>

          {/* AI SIGNALS */}

          <div className="card ai-signals-card">
            <div className="ai-signals-header">
              <div>
                <div className="eyebrow">
                  AI SIGNALS
                </div>

                <h3>
                  Evidence considered by
                  RecoverAI
                </h3>
              </div>

              {ai?.confidence && (
                <span className="badge neutral">
                  {ai.confidence}{" "}
                  confidence
                </span>
              )}
            </div>

            <div className="signals-list">
              {signals.length ? (
                signals.map(
                  (signal, index) => (
                    <div
                      className="ai-signal"
                      key={index}
                    >
                      <span className="ai-signal-check">
                        ✓
                      </span>

                      <span>
                        {typeof signal ===
                        "string"
                          ? signal
                          : signal?.interpretation ||
                            signal?.value ||
                            JSON.stringify(
                              signal
                            )}
                      </span>
                    </div>
                  )
                )
              ) : (
                <div className="ai-signal">
                  {loading
                    ? "Analyzing payment signals..."
                    : "No signals available."}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ==================================================
            RIGHT SIDE
            ================================================== */}

        <div className="decision-side">

          {/* GUARDRAIL */}

          <div className="card guardrail-card">
            <div className="eyebrow">
              GUARDRAIL
            </div>

            <h3>
              {isGuardrailTriggered
                ? "Guardrail triggered"
                : "Guardrail passed"}
            </h3>

            <p>
              {guardrail?.reason ||
                "Evaluating recovery guardrails..."}
            </p>

            {guardrail?.guardrail_reasons
              ?.length > 0 && (
              <div className="guardrail-reasons">
                {guardrail.guardrail_reasons.map(
                  (
                    reason,
                    index
                  ) => (
                    <div
                      key={index}
                      className="guardrail-reason"
                    >
                      <span>
                        ✓
                      </span>

                      {reason}
                    </div>
                  )
                )}
              </div>
            )}
          </div>

          {/* PAYMENT CONTEXT */}

          <div className="card context-card">
            <div className="eyebrow">
              PAYMENT CONTEXT
            </div>

            <h3>
              Selected payment
            </h3>

            <div className="context-list">

              <div>
                <span>
                  Payment ID
                </span>

                <strong>
                  {formatPaymentId(
                    payment.id
                  )}
                </strong>
              </div>

              <div>
                <span>
                  Amount
                </span>

                <strong>
                  {formatCurrency(
                    payment.amount
                  )}
                </strong>
              </div>

              <div>
                <span>
                  Failure
                </span>

                <strong>
                  {failureLabel(
                    payment
                  )}
                </strong>
              </div>

              <div>
                <span>
                  Customer success
                </span>

                <strong>
                  {analysis
                    ?.customer_history
                    ?.customer_success_count ??
                    "—"}
                </strong>
              </div>

              <div>
                <span>
                  Customer failures
                </span>

                <strong>
                  {analysis
                    ?.customer_history
                    ?.customer_failed_count ??
                    "—"}
                </strong>
              </div>

              <div>
                <span>
                  Last success
                </span>

                <strong>
                  {analysis
                    ?.customer_history
                    ?.hours_since_last_success !=
                  null
                    ? `${Number(
                        analysis
                          .customer_history
                          .hours_since_last_success
                      ).toFixed(
                        1
                      )}h ago`
                    : "—"}
                </strong>
              </div>
            </div>
          </div>

          {/* ==================================================
              FULL AUDIT TRAIL
              ================================================== */}

          <div className="card audit-summary-card">

            <div className="eyebrow">
              AUDIT TRAIL
            </div>

            <div className="audit-header-row">
              <div>
                <h3>
                  Decision recorded
                </h3>

                <p>
                  Complete decision path
                  captured for
                  traceability.
                </p>
              </div>

              <span className="audit-check">
                ✓
              </span>
            </div>

            {audit?.audit_id ? (
              <>
                <div className="audit-id">
                  {audit.audit_id}
                </div>

                {audit.created_at && (
                  <div className="audit-time">
                    Created{" "}
                    {new Date(
                      audit.created_at
                    ).toLocaleString(
                      "en-IN",
                      {
                        dateStyle:
                          "medium",
                        timeStyle:
                          "short",
                      }
                    )}
                  </div>
                )}

                <div className="audit-stages">

                  <div className="audit-stage">
                    <span>✓</span>
                    AI assessment
                  </div>

                  <div className="audit-stage">
                    <span>✓</span>
                    Deterministic policy
                  </div>

                  <div className="audit-stage">
                    <span>✓</span>
                    Policy reconciliation
                  </div>

                  <div className="audit-stage">
                    <span>✓</span>
                    Safety guardrail
                  </div>

                  <div className="audit-stage">
                    <span>✓</span>
                    Bounded execution
                  </div>

                </div>

                <div className="audit-final">
                  <span>
                    FINAL ACTION
                  </span>

                  <strong>
                    {actionLabel(
                      audit
                        ?.final_decision
                        ?.action ||
                        finalAction
                    )}
                  </strong>
                </div>
              </>
            ) : (
              <div className="audit-empty">
                {loading
                  ? "Generating audit record..."
                  : "Audit record not available."}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ==================================================
          EXECUTION RESULT
          ================================================== */}

      <div className="card decision-actions-card">
        <div>
          <div className="eyebrow">
            DECISION
          </div>

          <h3>
            {recommendation?.title ||
              actionLabel(
                finalAction
              )}
          </h3>

          <p>
            {execution?.message ||
              "Decision bounded by RecoverAI policy and safety controls."}
          </p>
        </div>

        <button
          className="primary-button"
          disabled={
            !analysis || loading
          }
          onClick={() =>
            navigate("results")
          }
        >
          Continue to result →
        </button>
      </div>
    </div>
  );
}

// ==================================================
// RECOVERY RESULTS
// ==================================================

function Results({
  analysis,
  payment,
  navigate,
}) {
  if (!analysis) {
    return (
      <div className="content">
        <section className="page-intro">
          <div>
            <div className="eyebrow">
              RECOVERY RESULTS
            </div>

            <h2>
              No recovery decision yet.
            </h2>
          </div>

          <button
            className="primary-button"
            onClick={() =>
              navigate("opportunities")
            }
          >
            View opportunities →
          </button>
        </section>
      </div>
    );
  }

  const execution =
    analysis.execution || {};

  const audit =
    analysis.audit_trail || {};

  const finalAction =
    analysis.guardrail?.action ||
    analysis.reconciled_action ||
    analysis.recommendation
      ?.action ||
    execution.action ||
    "—";

  return (
    <div className="content">

      <section className="page-intro">
        <div>
          <div className="eyebrow">
            RECOVERY RESULTS
          </div>

          <h2>
            Recovery decision completed.
          </h2>

          <p>
            This result reflects the
            RecoverAI decision, guardrail
            evaluation, bounded execution
            and audit record.
          </p>
        </div>
      </section>

      {/* RESULT */}

      <div className="card result-card">
        <div className="result-icon">
          ✓
        </div>

        <div>
          <div className="field-label">
            FINAL ACTION
          </div>

          <h3>
            {actionLabel(
              finalAction
            )}
          </h3>

          <p>
            {execution?.message ||
              "The recovery decision has been evaluated."}
          </p>
        </div>

        <span className="badge success">
          {execution?.status ||
            "Decision completed"}
        </span>
      </div>

      {/* RESULT GRID */}

      <div className="result-grid">

        <div className="card">
          <div className="eyebrow">
            DECISION
          </div>

          <h3>
            {analysis
              .recommendation
              ?.title ||
              actionLabel(
                finalAction
              )}
          </h3>

          <p>
            Confidence:{" "}
            {analysis
              .recommendation
              ?.confidence ||
              analysis
                .ai_assessment
                ?.confidence ||
              "—"}
          </p>
        </div>

        <div className="card">
          <div className="eyebrow">
            GUARDRAIL
          </div>

          <h3>
            {analysis.guardrail
              ?.guardrail_triggered
              ? "Triggered"
              : "Not triggered"}
          </h3>

          <p>
            {analysis.guardrail
              ?.reason ||
              "No guardrail reason provided."}
          </p>
        </div>

        <div className="card">
          <div className="eyebrow">
            EXECUTION
          </div>

          <h3 className="success-text">
            {execution?.executed
              ? "Simulated"
              : "Not executed"}
          </h3>

          <p>
            No real payment retry was
            performed.
          </p>
        </div>
      </div>

      {/* AUDIT RESULT */}

      <div className="card audit-result-card">

        <div>
          <div className="eyebrow">
            AUDIT TRAIL
          </div>

          <h3>
            Decision recorded
          </h3>

          <p>
            The final decision and
            safety controls were
            recorded for traceability.
          </p>
        </div>

        <div className="audit-result-meta">

          <span>
            AUDIT ID
          </span>

          <strong>
            {audit?.audit_id ||
              "—"}
          </strong>

          {audit?.created_at && (
            <small>
              {new Date(
                audit.created_at
              ).toLocaleString(
                "en-IN",
                {
                  dateStyle:
                    "medium",
                  timeStyle:
                    "short",
                }
              )}
            </small>
          )}
        </div>
      </div>

      {/* PAYMENT */}

      {payment && (
        <div
          className="card"
          style={{
            marginTop: 18,
          }}
        >
          <div className="eyebrow">
            PAYMENT
          </div>

          <h3>
            {formatPaymentId(
              payment.id
            )}
          </h3>

          <p>
            {formatCurrency(
              payment.amount
            )}
          </p>
        </div>
      )}
    </div>
  );
}

// ==================================================
// EVALUATION & IMPACT
// ==================================================

function EvaluationImpact({
  summary,
  filename,
  uploading,
  error,
  fileRef,
  onFile,
  chooseFile,
}) {
  const revenue =
    summary?.revenue || {};

  const recovery =
    summary?.recovery || {};

  const safety =
    summary?.safety || {};

  const aiSafety =
    summary?.ai_safety || {};

  const policy =
    summary?.policy || {};

  const accuracy =
    summary?.accuracy || {};

  const classification =
    summary?.classification || {};

  return (
    <div className="content">

      <section className="page-intro">
        <div>
          <div className="eyebrow">
            EVALUATION & IMPACT
          </div>

          <h2>
            Measure recovery performance.
          </h2>

          <p>
            Upload a batch evaluation
            dataset and see updated
            business impact, recovery
            and safety metrics.
          </p>
        </div>

        <div>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            onChange={onFile}
            style={{
              display: "none",
            }}
          />

          <button
            className="primary-button"
            disabled={uploading}
            onClick={chooseFile}
          >
            {uploading
              ? "Evaluating..."
              : "Upload evaluation CSV ↑"}
          </button>
        </div>
      </section>

      {filename && (
        <div
          className="card"
          style={{
            padding: "11px 15px",
            marginBottom: 18,
            fontSize: 12,
          }}
        >
          Latest evaluation:{" "}
          <strong>
            {filename}
          </strong>

          {summary?.total_cases !=
            null && (
            <>
              {" · "}
              {summary.total_cases}{" "}
              cases
            </>
          )}
        </div>
      )}

      {error && (
        <Alert>{error}</Alert>
      )}

      {!summary && !uploading && (
        <div
          className="card"
          style={{
            padding: 35,
            marginBottom: 20,
          }}
        >
          <div className="eyebrow">
            NO EVALUATION LOADED
          </div>

          <h3>
            Upload a CSV to generate
            your metrics.
          </h3>

          <p>
            The uploaded batch will be
            evaluated and displayed
            here.
          </p>

          <button
            className="secondary-button"
            onClick={chooseFile}
          >
            Choose CSV file →
          </button>
        </div>
      )}

      {uploading && (
        <div
          className="card"
          style={{
            padding: 24,
            marginBottom: 20,
          }}
        >
          <strong>
            Evaluating uploaded
            batch...
          </strong>

          <p
            style={{
              marginBottom: 0,
            }}
          >
            RecoverAI is running the
            AI evaluation pipeline and
            calculating the updated
            metrics.
          </p>
        </div>
      )}

      {summary && (
        <>
          {/* REVENUE */}

          <section
            style={{
              marginBottom: 24,
            }}
          >
            <div className="eyebrow">
              REVENUE IMPACT
            </div>

            <h2
              style={{
                margin:
                  "5px 0 12px",
              }}
            >
              Recovery value at a
              glance.
            </h2>

            <div className="stats-grid">
              <Impact
                label="Revenue at risk"
                value={formatRupees(
                  revenue.total_at_risk
                )}
                note="total payment value evaluated"
              />

              <Impact
                label="Recoverable revenue"
                value={formatRupees(
                  revenue.recoverable_at_risk
                )}
                note="revenue classified as recoverable"
              />

              <Impact
                featured
                label="Recovery opportunity"
                value={formatRupees(
                  revenue.recovery_opportunity
                )}
                note={`${pct(
                  revenue.opportunity_rate
                )} opportunity rate`}
              />

              <Impact
                label="Safely blocked"
                value={formatRupees(
                  revenue.safely_blocked
                )}
                note="non-recoverable revenue protected"
              />
            </div>
          </section>

          {/* RECOVERY */}

          <MetricSection title="RECOVERY PERFORMANCE">
            <div className="dashboard-grid">
              <Metric
                label="Recoverable cases"
                value={
                  recovery.recoverable_cases
                }
                note="recoverable cases"
              />

              <Metric
                label="Retry opportunities"
                value={
                  recovery.retry_opportunities
                }
                note="cases receiving retry opportunity"
              />

              <Metric
                label="Recovery recall"
                value={pct(
                  recovery.recall
                )}
                note="recoverable cases captured"
              />
            </div>
          </MetricSection>

          {/* SAFETY */}

          <MetricSection title="SAFETY">
            <div className="dashboard-grid">
              <Metric
                featured
                label="Safety rate"
                value={pct(
                  safety.safety_rate
                )}
                note="unsafe automatic retries prevented"
              />

              <Metric
                label="Unsafe final retries"
                value={
                  safety.unsafe_final_retries ??
                  0
                }
                note="target: zero"
              />

              <Metric
                label="Non-recoverable cases"
                value={
                  safety.non_recoverable_cases ??
                  0
                }
                note="cases requiring safe handling"
              />
            </div>
          </MetricSection>

          {/* AI / POLICY */}

          <MetricSection title="AI / POLICY">
            <div className="dashboard-grid">
              <Metric
                label="AI accuracy"
                value={pct(
                  accuracy.ai
                )}
                note="AI vs expected action"
              />

              <Metric
                label="Policy agreement"
                value={pct(
                  policy.agreement_rate
                )}
                note={`${policy.ai_policy_agreements ?? 0} agreements`}
              />

              <Metric
                label="Decisions changed downstream"
                value={pct(
                  policy.decision_change_rate
                )}
                note={`${policy.decisions_changed ?? 0} decisions changed`}
              />

              <Metric
                label="AI unsafe recommendations"
                value={
                  aiSafety.unsafe_recommendations ??
                  0
                }
                note="unsafe AI retry recommendations"
              />
            </div>
          </MetricSection>

          {/* CLASSIFICATION */}

          <MetricSection title="CLASSIFICATION PERFORMANCE">
            <div
              className="card"
              style={{
                overflowX: "auto",
              }}
            >
              <table
                style={tableStyle}
              >
                <thead>
                  <tr>
                    <th style={th}>
                      ACTION
                    </th>

                    <th style={th}>
                      PRECISION
                    </th>

                    <th style={th}>
                      RECALL
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {ACTIONS.map(
                    (action) => (
                      <tr key={action}>
                        <td style={td}>
                          {actionLabel(
                            action
                          )}
                        </td>

                        <td style={td}>
                          {pct(
                            classification
                              .precision?.[
                              action
                            ]
                          )}
                        </td>

                        <td style={td}>
                          {pct(
                            classification
                              .recall?.[
                              action
                            ]
                          )}
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
          </MetricSection>

          {/* CONFUSION MATRIX */}

          <MetricSection title="CONFUSION MATRIX">
            <div
              className="card"
              style={{
                overflowX: "auto",
              }}
            >
              <table
                style={{
                  ...tableStyle,
                  minWidth: 700,
                }}
              >
                <thead>
                  <tr>
                    <th style={th}>
                      EXPECTED
                    </th>

                    {ACTIONS.map(
                      (action) => (
                        <th
                          style={th}
                          key={action}
                        >
                          {actionLabel(
                            action
                          )}
                        </th>
                      )
                    )}
                  </tr>
                </thead>

                <tbody>
                  {ACTIONS.map(
                    (expected) => (
                      <tr
                        key={expected}
                      >
                        <td style={td}>
                          {actionLabel(
                            expected
                          )}
                        </td>

                        {ACTIONS.map(
                          (action) => (
                            <td
                              style={{
                                ...td,
                                textAlign:
                                  "center",
                                fontWeight:
                                  800,
                              }}
                              key={action}
                            >
                              {classification
                                .confusion_matrix?.[
                                expected
                              ]?.[
                                action
                              ] ?? 0}
                            </td>
                          )
                        )}
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
          </MetricSection>

          {/* ANOTHER EVALUATION */}

          <div
            className="card"
            style={{
              padding: 24,
              display: "flex",
              justifyContent:
                "space-between",
              alignItems:
                "center",
              gap: 20,
              flexWrap: "wrap",
            }}
          >
            <div>
              <div className="eyebrow">
                RUN ANOTHER EVALUATION
              </div>

              <h3
                style={{
                  margin:
                    "5px 0",
                }}
              >
                Replace these metrics
                with another batch.
              </h3>

              <p
                style={{
                  margin: 0,
                }}
              >
                Upload another CSV to
                generate a fresh
                snapshot.
              </p>
            </div>

            <button
              className="primary-button"
              disabled={uploading}
              onClick={chooseFile}
            >
              {uploading
                ? "Evaluating..."
                : "Upload another CSV →"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// ==================================================
// TABLE STYLES
// ==================================================

const tableStyle = {
  width: "100%",
  borderCollapse:
    "collapse",
  fontSize: 12,
};

const th = {
  textAlign: "left",
  padding: "12px 10px",
  borderBottom:
    "1px solid #eaecf0",
  color: "#667085",
  fontSize: 10,
  textTransform:
    "uppercase",
  letterSpacing: ".08em",
};

const td = {
  padding: "13px 10px",
  borderBottom:
    "1px solid #f2f4f7",
  color: "#344054",
};

// ==================================================
// PAGE TITLE
// ==================================================

function pageTitle(page) {
  return {
    overview: "Overview",
    opportunities:
      "Recovery Opportunities",
    workspace:
      "Decision Workspace",
    results:
      "Recovery Results",
    evaluation:
      "Evaluation & Impact",
  }[page] || "Overview";
}

export default App;