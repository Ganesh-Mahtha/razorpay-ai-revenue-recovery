import { useEffect, useMemo, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function formatCurrency(amountInPaise) {
  if (amountInPaise === undefined || amountInPaise === null) {
    return "—";
  }

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amountInPaise / 100);
}

function formatPaymentId(id) {
  if (!id) return "—";

  if (id.length <= 22) return id;

  return `${id.slice(0, 11)}...${id.slice(-6)}`;
}

function getFailureLabel(payment) {
  const description =
    payment?.error_description ||
    payment?.error_reason ||
    payment?.error_code ||
    "";

  const text = description.toLowerCase();

  if (
    text.includes("timeout") ||
    text.includes("network") ||
    text.includes("temporary")
  ) {
    return "Temporary";
  }

  return payment?.status === "failed" ? "Failed" : "Unknown";
}

// ==================================================
// APP
// ==================================================

function App() {
  const [activePage, setActivePage] = useState("overview");

  const [payments, setPayments] = useState([]);
  const [analysis, setAnalysis] = useState(null);

  // No hard-coded payment.
  // This gets populated with the first failed payment after API data loads.
  const [selectedPaymentId, setSelectedPaymentId] = useState(null);

  const [loadingPayments, setLoadingPayments] = useState(true);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [error, setError] = useState("");

  // --------------------------------------------------
  // Fetch Razorpay payments
  // --------------------------------------------------

  useEffect(() => {
    async function loadPayments() {
      try {
        setLoadingPayments(true);
        setError("");

        const response = await fetch(`${API_URL}/payments?count=100`);

        if (!response.ok) {
          throw new Error("Unable to load payments.");
        }

        const data = await response.json();
        const items = data?.items || data || [];

        setPayments(items);

        // Automatically select the first failed payment.
        // This gives Overview a useful top opportunity
        // without hard-coding a payment ID.
        const firstFailedPayment = items.find(
          (payment) => payment.status === "failed"
        );

        if (firstFailedPayment?.id) {
          setSelectedPaymentId(firstFailedPayment.id);
        } else {
          setSelectedPaymentId(null);
        }
      } catch (err) {
        console.error(err);

        setError(
          "Could not connect to RecoverAI. Make sure FastAPI is running on port 8000."
        );
      } finally {
        setLoadingPayments(false);
      }
    }

    loadPayments();
  }, []);

  // --------------------------------------------------
  // Selected payment
  // --------------------------------------------------

  const failedPayments = useMemo(() => {
    return payments.filter((payment) => payment.status === "failed");
  }, [payments]);

  const failedPaymentValue = useMemo(() => {
    return failedPayments.reduce(
      (total, payment) => total + (payment.amount || 0),
      0
    );
  }, [failedPayments]);

  const selectedPayment = useMemo(() => {
    if (!selectedPaymentId) return null;

    return (
      payments.find((payment) => payment.id === selectedPaymentId) || null
    );
  }, [payments, selectedPaymentId]);

  // --------------------------------------------------
  // Analyze selected payment
  // --------------------------------------------------

  useEffect(() => {
    async function loadAnalysis() {
      if (!selectedPaymentId) {
        setAnalysis(null);
        return;
      }

      try {
        setLoadingAnalysis(true);
        setError("");

        // Clear old analysis immediately so that analysis
        // from Payment A cannot temporarily appear for Payment B.
        setAnalysis(null);

        const response = await fetch(
          `${API_URL}/payments/${selectedPaymentId}/analyze`
        );

        if (!response.ok) {
          throw new Error("Unable to analyze payment.");
        }

        const data = await response.json();

        setAnalysis(data);
      } catch (err) {
        console.error(err);

        setAnalysis(null);
        setError("Unable to analyze the selected payment.");
      } finally {
        setLoadingAnalysis(false);
      }
    }

    loadAnalysis();
  }, [selectedPaymentId]);

  // --------------------------------------------------
  // Navigation
  // --------------------------------------------------

  function navigate(page) {
    setActivePage(page);
  }

  function selectPayment(paymentId, page = "workspace") {
    setSelectedPaymentId(paymentId);
    setActivePage(page);
  }

  // --------------------------------------------------
  // Loading state
  // --------------------------------------------------

  if (loadingPayments && payments.length === 0) {
    return (
      <div className="app-shell">
        <Sidebar activePage={activePage} navigate={navigate} />

        <main className="main">
          <header className="topbar">
            <div>
              <div className="breadcrumb">RecoverAI</div>
              <h1>Overview</h1>
            </div>

            <div className="topbar-right">
              <div className="connection">
                <span className="status-dot" />
                Connecting to Razorpay
              </div>

              <div className="top-avatar">G</div>
            </div>
          </header>

          <div className="content">
            <div className="card" style={{ padding: 40 }}>
              Loading RecoverAI data...
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <Sidebar activePage={activePage} navigate={navigate} />

      <main className="main">
        <header className="topbar">
          <div>
            <div className="breadcrumb">
              RecoverAI <span>/</span> {pageTitle(activePage)}
            </div>

            <h1>{pageTitle(activePage)}</h1>
          </div>

          <div className="topbar-right">
            <div className="connection">
              <span className="status-dot" />
              Razorpay connected
            </div>

            <div className="top-avatar">G</div>
          </div>
        </header>

        {error && (
          <div
            style={{
              margin: "16px 42px 0",
              padding: "12px 15px",
              background: "#fef3f2",
              border: "1px solid #fecdca",
              borderRadius: "8px",
              color: "#b42318",
              fontSize: "12px",
            }}
          >
            {error}
          </div>
        )}

        {/* ==================================================
            OVERVIEW
            ================================================== */}

        {activePage === "overview" && (
          <Overview
            failedPayments={failedPayments}
            failedPaymentValue={failedPaymentValue}
            analysis={analysis}
            selectedPayment={selectedPayment}
            loadingAnalysis={loadingAnalysis}
            navigate={navigate}
            selectPayment={selectPayment}
          />
        )}

        {/* ==================================================
            RECOVERY OPPORTUNITIES
            ================================================== */}

        {activePage === "opportunities" && (
          <Opportunities
            failedPayments={failedPayments}
            selectedPaymentId={selectedPaymentId}
            selectPayment={selectPayment}
          />
        )}

        {/* ==================================================
            DECISION WORKSPACE
            IMPORTANT:
            This receives ONLY selectedPayment + analysis.
            It does NOT receive failedPayments.
            ================================================== */}

        {activePage === "workspace" && (
          <DecisionWorkspace
            analysis={analysis}
            selectedPayment={selectedPayment}
            loadingAnalysis={loadingAnalysis}
            navigate={navigate}
          />
        )}

        {/* ==================================================
            RECOVERY RESULTS
            ================================================== */}

        {activePage === "results" && (
          <RecoveryResults
            analysis={analysis}
            selectedPayment={selectedPayment}
            navigate={navigate}
          />
        )}
      </main>
    </div>
  );
}

// ==================================================
// SIDEBAR
// ==================================================

function Sidebar({ activePage, navigate }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">R</div>

        <div>
          <div className="brand-name">RecoverAI</div>
          <div className="brand-subtitle">Revenue recovery</div>
        </div>
      </div>

      <div className="sidebar-section">
        <div className="sidebar-label">WORKSPACE</div>

        <NavItem
          icon="⌂"
          label="Overview"
          active={activePage === "overview"}
          onClick={() => navigate("overview")}
        />

        <NavItem
          icon="↗"
          label="Recovery Opportunities"
          active={activePage === "opportunities"}
          onClick={() => navigate("opportunities")}
        />

        <NavItem
          icon="◇"
          label="Decision Workspace"
          active={activePage === "workspace"}
          onClick={() => navigate("workspace")}
        />

        <NavItem
          icon="✓"
          label="Recovery Results"
          active={activePage === "results"}
          onClick={() => navigate("results")}
        />
      </div>

      <div className="sidebar-bottom">
        <div className="engine-status">
          <span className="status-dot" />

          <div>
            <strong>Recovery engine</strong>
            <small>Operational</small>
          </div>
        </div>

        <div className="merchant">
          <div className="merchant-avatar">M</div>

          <div>
            <strong>Merchant account</strong>
            <small>Razorpay connected</small>
          </div>
        </div>
      </div>
    </aside>
  );
}

function NavItem({ icon, label, active, onClick }) {
  return (
    <button
      type="button"
      className={`nav-item ${active ? "active" : ""}`}
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
  failedPaymentValue,
  analysis,
  selectedPayment,
  loadingAnalysis,
  navigate,
  selectPayment,
}) {
  return (
    <div className="content">
      <section className="hero-section">
        <div>
          <div className="eyebrow">RECOVERY INTELLIGENCE</div>

          <h2>Recover revenue with better decisions.</h2>

          <p>
            RecoverAI analyzes failed payments, customer history and recovery
            signals to identify the safest next action.
          </p>
        </div>

        <button
          className="primary-button"
          onClick={() => navigate("opportunities")}
        >
          View opportunities →
        </button>
      </section>

      {/* SUMMARY ONLY */}
      <section className="stats-grid">
        <StatCard
          label="Failed payments"
          value={failedPayments.length}
          note="from Razorpay"
        />

        <StatCard
          label="Failed payment value"
          value={formatCurrency(failedPaymentValue)}
          note="current payment set"
        />

        <StatCard
          label="Recovery score"
          value={analysis?.score?.score ?? "—"}
          note={
            analysis?.score?.tier
              ? `${analysis.score.tier} opportunity`
              : "Analyze a payment"
          }
        />

        <StatCard
          label="Recommended action"
          value={
            analysis?.recommendation?.action
              ? analysis.recommendation.action
                  .replaceAll("_", " ")
                  .toLowerCase()
              : "—"
          }
          note={
            analysis?.recommendation?.confidence
              ? `${analysis.recommendation.confidence} confidence`
              : "Awaiting analysis"
          }
        />
      </section>

      {/* TOP OPPORTUNITY + AI SIGNALS */}
      <section className="dashboard-grid">
        <OpportunityCard
          analysis={analysis}
          selectedPayment={selectedPayment}
          loadingAnalysis={loadingAnalysis}
          navigate={navigate}
          selectPayment={selectPayment}
        />

        <SignalsCard analysis={analysis} />
      </section>

      {/* SMALL RECENT ACTIVITY SUMMARY */}
      <ActivityCard
        payments={failedPayments.slice(0, 5)}
        navigate={navigate}
      />
    </div>
  );
}

// ==================================================
// STAT
// ==================================================

function StatCard({ label, value, note }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>

      <div className="stat-value">{value}</div>

      <div className="stat-change">{note}</div>
    </div>
  );
}

// ==================================================
// OVERVIEW TOP OPPORTUNITY
// ==================================================

function OpportunityCard({
  analysis,
  selectedPayment,
  loadingAnalysis,
  navigate,
  selectPayment,
}) {
  const score = analysis?.score?.score ?? "—";

  const paymentId = selectedPayment?.id || analysis?.payment_id;

  const paymentAmount = selectedPayment?.amount;

  function openWorkspace() {
    if (paymentId) {
      selectPayment(paymentId, "workspace");
    } else {
      navigate("opportunities");
    }
  }

  return (
    <div className="card opportunity-card">
      <div className="card-header">
        <div>
          <div className="eyebrow">TOP OPPORTUNITY</div>

          <h3>Payment needs attention</h3>
        </div>

        <span className="badge warning">
          {analysis?.score?.tier || "—"}
        </span>
      </div>

      <div className="payment-row">
        <div>
          <div className="field-label">PAYMENT</div>

          <strong>{formatPaymentId(paymentId)}</strong>
        </div>

        <div className="amount">
          {formatCurrency(paymentAmount)}
        </div>
      </div>

      <div className="score-section">
        <div className="score-ring">
          <strong>{score}</strong>
          <span>/ 100</span>
        </div>

        <div className="score-copy">
          <div className="field-label">RECOVERY SCORE</div>

          <strong>
            {loadingAnalysis
              ? "Analyzing..."
              : analysis?.recommendation?.title || "Awaiting analysis"}
          </strong>

          <p>
            {analysis?.recommendation?.reason ||
              "RecoverAI is evaluating this payment."}
          </p>
        </div>
      </div>

      <button
        className="secondary-button full"
        onClick={openWorkspace}
        disabled={!paymentId}
      >
        Open decision workspace →
      </button>
    </div>
  );
}

// ==================================================
// SIGNALS
// ==================================================

function SignalsCard({ analysis }) {
  const signals = analysis?.diagnosis?.signals || [];

  return (
    <div className="card signals-card">
      <div className="eyebrow">AI SIGNALS</div>

      <h3>Why this payment matters</h3>

      <div className="signals-list">
        {signals.length === 0 && (
          <div className="signal">
            Waiting for payment analysis...
          </div>
        )}

        {signals.map((signal, index) => (
          <div className="signal" key={`${signal}-${index}`}>
            <span className="signal-check">✓</span>
            {signal}
          </div>
        ))}
      </div>
    </div>
  );
}

// ==================================================
// RECENT ACTIVITY
// ==================================================

function ActivityCard({ payments, navigate }) {
  return (
    <div className="card activity-card">
      <div className="card-header">
        <div>
          <div className="eyebrow">RECENT ACTIVITY</div>

          <h3>Failed payment opportunities</h3>
        </div>

        <button
          className="text-button"
          onClick={() => navigate("opportunities")}
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
          <div className="table-row" key={payment.id}>
            <div className="payment-id">
              {formatPaymentId(payment.id)}
            </div>

            <div>{formatCurrency(payment.amount)}</div>

            <div>
              <span
                className={`badge ${
                  getFailureLabel(payment) === "Failed"
                    ? "danger"
                    : "warning"
                }`}
              >
                {getFailureLabel(payment)}
              </span>
            </div>

            <div className="score-number">—</div>

            <div>Analyze payment</div>
          </div>
        ))}

        {payments.length === 0 && (
          <div
            style={{
              padding: "30px 0",
              color: "#98a2b3",
              fontSize: "11px",
            }}
          >
            No failed payments returned by Razorpay.
          </div>
        )}
      </div>
    </div>
  );
}

// ==================================================
// RECOVERY OPPORTUNITIES
// ==================================================

function Opportunities({
  failedPayments,
  selectedPaymentId,
  selectPayment,
}) {
  return (
    <div className="content">
      <section className="page-intro">
        <div>
          <div className="eyebrow">RECOVERY OPPORTUNITIES</div>

          <h2>Failed payments worth reviewing.</h2>

          <p>
            Review real failed Razorpay payments and send them through the
            RecoverAI decision pipeline.
          </p>
        </div>

        <div className="opportunity-summary">
          <span>{failedPayments.length}</span>
          <small>payments to review</small>
        </div>
      </section>

      <div className="opportunity-list">
        {failedPayments.map((payment) => {
          const isSelected = payment.id === selectedPaymentId;
          const failureLabel = getFailureLabel(payment);

          return (
            <div
              className={`card opportunity-card ${
                isSelected ? "selected" : ""
              }`}
              key={payment.id}
              onClick={() => selectPayment(payment.id, "opportunities")}
            >
              <div className="opportunity-main">
                <div className="opportunity-payment">
                  <div className="field-label">PAYMENT</div>

                  <strong>{formatPaymentId(payment.id)}</strong>

                  <span className="opportunity-source">
                    Razorpay payment
                  </span>
                </div>

                <div className="opportunity-amount">
                  <div className="field-label">AMOUNT</div>

                  <strong>
                    {formatCurrency(payment.amount)}
                  </strong>
                </div>

                <div className="opportunity-failure">
                  <div className="field-label">FAILURE TYPE</div>

                  <span
                    className={`badge ${
                      failureLabel === "Failed"
                        ? "danger"
                        : "warning"
                    }`}
                  >
                    {failureLabel}
                  </span>
                </div>

                <div className="opportunity-score">
                  <div className="field-label">RECOVERY</div>

                  <strong>—</strong>

                  <span>Awaiting analysis</span>
                </div>

                <button
                  type="button"
                  className="primary-button opportunity-action"
                  onClick={(event) => {
                    event.stopPropagation();

                    // This is the ONLY place where the list
                    // sends the user into Decision Workspace.
                    selectPayment(payment.id, "workspace");
                  }}
                >
                  Analyze payment →
                </button>
              </div>

              {isSelected && (
                <div className="selected-indicator">
                  Selected for recovery analysis
                </div>
              )}
            </div>
          );
        })}

        {failedPayments.length === 0 && (
          <div className="card empty-opportunities">
            <div className="empty-icon">✓</div>

            <h3>No failed payments</h3>

            <p>
              There are currently no failed Razorpay payments
              requiring recovery review.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// ==================================================
// DECISION WORKSPACE
// IMPORTANT:
//
// This is deliberately NOT a payment list.
//
// It receives:
//   - selectedPayment
//   - analysis
//
// It does NOT receive:
//   - failedPayments
//
// ==================================================

function DecisionWorkspace({
  analysis,
  selectedPayment,
  loadingAnalysis,
  navigate,
}) {
  // --------------------------------------------------
  // No payment selected
  // --------------------------------------------------

  if (!selectedPayment) {
    return (
      <div className="content">
        <section className="page-intro">
          <div>
            <div className="eyebrow">DECISION WORKSPACE</div>

            <h2>Select a payment to review.</h2>

            <p>
              Choose a failed payment from Recovery Opportunities
              to evaluate its safest recovery action.
            </p>
          </div>

          <button
            className="primary-button"
            onClick={() => navigate("opportunities")}
          >
            View opportunities →
          </button>
        </section>

        <div className="card" style={{ padding: 35 }}>
          <div className="empty-icon">◇</div>

          <h3>No payment selected</h3>

          <p>
            Select a failed payment from the Recovery Opportunities
            page to open its decision workspace.
          </p>

          <button
            className="secondary-button"
            onClick={() => navigate("opportunities")}
          >
            Choose payment →
          </button>
        </div>
      </div>
    );
  }

  const paymentId = selectedPayment.id;
  const amount = selectedPayment.amount;

  const score = analysis?.score?.score ?? "—";

  const recommendation =
    analysis?.recommendation?.title ||
    "Awaiting decision";

  const recommendationReason =
    analysis?.recommendation?.reason ||
    "RecoverAI is evaluating this payment.";

  const failureLabel = getFailureLabel(selectedPayment);

  const recoveryStatus = loadingAnalysis
    ? "Analyzing..."
    : analysis
      ? "Analysis complete"
      : "Awaiting analysis";

  const signals = analysis?.diagnosis?.signals || [];

  return (
    <div className="content">
      {/* ==================================================
          WORKSPACE HEADER
          ================================================== */}

      <section className="page-intro">
        <div>
          <div className="eyebrow">DECISION WORKSPACE</div>

          <h2>Review this recovery decision.</h2>

          <p>
            RecoverAI evaluates payment history, failure signals
            and guardrails before recommending the safest action.
          </p>
        </div>

        <button
          className="secondary-button"
          onClick={() => navigate("opportunities")}
        >
          ← Back to opportunities
        </button>
      </section>

      {/* ==================================================
          SELECTED PAYMENT
          ================================================== */}

      <div className="card decision-card">
        <div className="decision-top">
          <div>
            <div className="field-label">PAYMENT</div>

            <h3>{formatPaymentId(paymentId)}</h3>

            <span className="opportunity-source">
              Razorpay payment
            </span>
          </div>

          <div className="decision-amount">
            {formatCurrency(amount)}
          </div>
        </div>

        {/* Consistent metadata rows — keeps failure/status aligned */}
        <div className="context-list decision-meta">
          <div>
            <span>Failure type</span>

            <strong>
              <span
                className={`badge ${
                  failureLabel === "Failed"
                    ? "danger"
                    : "warning"
                }`}
              >
                {failureLabel}
              </span>
            </strong>
          </div>

          <div>
            <span>Recovery status</span>
            <strong>{recoveryStatus}</strong>
          </div>
        </div>
      </div>

      {/* ==================================================
          MAIN WORKSPACE
          ================================================== */}

      <div className="workspace-grid">
        {/* LEFT */}
        <div className="decision-main">
          {/* SCORE / RECOMMENDATION */}
          <div className="card decision-card">
            <div className="eyebrow">RECOVERY DECISION</div>

            <div className="decision-score">
              <div className="score-ring large">
                <strong>{score}</strong>
                <span>/ 100</span>
              </div>

              <div>
                <div className="field-label">
                  RECOMMENDED ACTION
                </div>

                <h3>
                  {loadingAnalysis
                    ? "Analyzing..."
                    : recommendation}
                </h3>

                <p>
                  {recommendationReason}
                </p>

                {analysis?.recommendation?.confidence && (
                  <div className="stat-change">
                    Confidence:{" "}
                    {analysis.recommendation.confidence}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* DIAGNOSIS */}
          <div className="card diagnosis-card">
            <div className="eyebrow">DIAGNOSIS</div>

            <h3>Why RecoverAI reached this decision</h3>

            <p>
              {analysis?.diagnosis?.summary ||
                analysis?.diagnosis?.reason ||
                "The payment analysis is being prepared."}
            </p>

            <div className="diagnosis-grid">
              <div>
                <span>FAILURE TYPE</span>

                <strong>
                  {analysis?.diagnosis?.failure_type ||
                    failureLabel}
                </strong>
              </div>

              <div>
                <span>PAYMENT</span>

                <strong>
                  {formatPaymentId(paymentId)}
                </strong>
              </div>

              <div>
                <span>AMOUNT</span>

                <strong>
                  {formatCurrency(amount)}
                </strong>
              </div>
            </div>
          </div>

          {/* AI SIGNALS */}
          <div className="ai-signals-card">
            <div className="ai-signals-header">
              <div className="eyebrow">AI SIGNALS</div>
              <h3>Signals considered</h3>
            </div>

            <div className="signals-list">
              {signals.length === 0 && (
                <div className="ai-signal">
                  {loadingAnalysis
                    ? "Analyzing payment signals..."
                    : "No signals available yet."}
                </div>
              )}

              {signals.map((signal, index) => (
                <div
                  className="ai-signal"
                  key={`${signal}-${index}`}
                >
                  <span className="ai-signal-check">✓</span>
                  <span>{signal}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT */}
        <div className="decision-side">
          {/* GUARDRAIL */}
          <div className="card guardrail-card">
            <div className="eyebrow">GUARDRAIL</div>

            <h3>
              {analysis?.guardrail?.guardrail_triggered
                ? "Guardrail triggered"
                : "Guardrail check"}
            </h3>

            <p>
              {analysis?.guardrail?.reason ||
                (loadingAnalysis
                  ? "Evaluating recovery guardrails..."
                  : "No guardrail information available yet.")}
            </p>

            {analysis && (
              <span
                className={`badge ${
                  analysis.guardrail?.guardrail_triggered
                    ? "warning"
                    : "success"
                }`}
              >
                {analysis.guardrail?.guardrail_triggered
                  ? "Triggered"
                  : "Passed"}
              </span>
            )}
          </div>

          {/* PAYMENT CONTEXT */}
          <div className="card context-card">
            <div className="eyebrow">PAYMENT CONTEXT</div>

            <h3>Selected payment</h3>

            <div className="context-list">
              <div>
                <span>Payment ID</span>
                <strong>{formatPaymentId(paymentId)}</strong>
              </div>

              <div>
                <span>Amount</span>
                <strong>{formatCurrency(amount)}</strong>
              </div>

              <div>
                <span>Failure</span>
                <strong>{failureLabel}</strong>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ==================================================
          DECISION ACTIONS
          ================================================== */}

      <div className="card decision-actions-card">
        <div>
          <div className="eyebrow">DECISION</div>

          <h3>
            {analysis?.recommendation?.title ||
              "Decision pending"}
          </h3>

          <p>
            Review the recommendation and guardrail result before
            proceeding.
          </p>
        </div>

        <div className="decision-actions">
          <button
            className="secondary-button"
            onClick={() => navigate("opportunities")}
          >
            Choose another payment
          </button>

          <button
            className="primary-button"
            disabled={!analysis || loadingAnalysis}
            onClick={() => navigate("results")}
          >
            Continue to result →
          </button>
        </div>
      </div>
    </div>
  );
}

// ==================================================
// RESULTS
// ==================================================

function RecoveryResults({
  analysis,
  selectedPayment,
  navigate,
}) {
  if (!analysis) {
    return (
      <div className="content">
        <section className="page-intro">
          <div>
            <div className="eyebrow">RECOVERY RESULTS</div>

            <h2>No recovery decision yet.</h2>

            <p>
              Analyze a failed payment in the Decision Workspace
              before viewing its recovery result.
            </p>
          </div>

          <button
            className="primary-button"
            onClick={() => navigate("opportunities")}
          >
            View opportunities →
          </button>
        </section>

        <div className="card" style={{ padding: 35 }}>
          No recovery decision available yet.
        </div>
      </div>
    );
  }

  const execution = analysis.execution;

  return (
    <div className="content">
      <section className="page-intro">
        <div>
          <div className="eyebrow">RECOVERY RESULTS</div>

          <h2>Recovery decision completed.</h2>

          <p>
            This result reflects the RecoverAI decision,
            guardrail evaluation and simulated execution.
          </p>
        </div>
      </section>

      {/* EXECUTION STATUS */}
      <div className="card result-card">
        <div className="result-icon">✓</div>

        <div>
          <div className="field-label">EXECUTION STATUS</div>

          <h3>
            {execution?.action ||
              analysis.recommendation?.action ||
              "Decision completed"}
          </h3>

          <p>
            {execution?.message ||
              "The recovery decision has been evaluated."}
          </p>
        </div>

        <span className="badge success">
          {execution?.status || "Completed"}
        </span>
      </div>

      {/* RESULT CARDS */}
      <div className="result-grid">
        <div className="card">
          <div className="eyebrow">DECISION</div>

          <h3>
            {analysis.recommendation?.title ||
              "No recommendation"}
          </h3>

          <p className="stat-change">
            Confidence:{" "}
            {analysis.recommendation?.confidence || "—"}
          </p>
        </div>

        <div className="card">
          <div className="eyebrow">GUARDRAIL</div>

          <h3>
            {analysis.guardrail?.guardrail_triggered
              ? "Triggered"
              : "Not triggered"}
          </h3>

          <p className="stat-change">
            {analysis.guardrail?.reason ||
              "No guardrail reason provided."}
          </p>
        </div>

        <div className="card">
          <div className="eyebrow">EXECUTION</div>

          <h3 className="success-text">
            {execution?.executed
              ? "Simulated"
              : "Not executed"}
          </h3>

          <p className="stat-change">
            No real payment retry was performed.
          </p>
        </div>
      </div>

      {/* PAYMENT REFERENCE */}
      {selectedPayment && (
        <div className="card payment-reference-card">
          <div className="payment-reference-info">
            <div className="eyebrow">PAYMENT</div>

            <h3>
              {formatPaymentId(selectedPayment.id)}
            </h3>
          </div>

          <div className="payment-reference-amount">
            {formatCurrency(selectedPayment.amount)}
          </div>
        </div>
      )}

      <div style={{ marginTop: 18 }}>
        <button
          className="secondary-button"
          onClick={() => navigate("overview")}
        >
          ← Back to overview
        </button>
      </div>
    </div>
  );
}

// ==================================================
// HELPERS
// ==================================================

function pageTitle(page) {
  const titles = {
    overview: "Overview",
    opportunities: "Recovery Opportunities",
    workspace: "Decision Workspace",
    results: "Recovery Results",
  };

  return titles[page] || "Overview";
}

export default App;