import { useEffect, useMemo, useRef, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";
const ACTIONS = ["RETRY", "RETRY_WITH_CAUTION", "DO_NOT_RETRY", "HUMAN_REVIEW"];

function formatCurrency(paise) {
  if (paise == null) return "—";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(paise) / 100);
}
function formatRupees(value) {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(value));
}
function formatPaymentId(id) {
  if (!id) return "—";
  return id.length <= 22 ? id : `${id.slice(0, 11)}...${id.slice(-6)}`;
}
function actionLabel(action) {
  return action ? action.replaceAll("_", " ").toLowerCase() : "—";
}
function pct(value) {
  return `${Number(value ?? 0).toFixed(1)}%`;
}
function failureLabel(payment) {
  const text = String(payment?.error_description || payment?.error_reason || payment?.error_code || "").toLowerCase();
  if (["timeout", "network", "temporary"].some((x) => text.includes(x))) return "Temporary";
  return payment?.status === "failed" ? "Failed" : "Unknown";
}

function App() {
  const [page, setPage] = useState("overview");
  const [payments, setPayments] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loadingPayments, setLoadingPayments] = useState(true);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [error, setError] = useState("");

  const [summary, setSummary] = useState(null);
  const [evaluationError, setEvaluationError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [filename, setFilename] = useState("");
  const fileRef = useRef(null);

  useEffect(() => {
    fetch(`${API_URL}/payments?count=100`)
      .then((r) => {
        if (!r.ok) throw new Error("Unable to load payments.");
        return r.json();
      })
      .then((data) => {
        const items = data?.items || data || [];
        setPayments(items);
        setSelectedId(items.find((p) => p.status === "failed")?.id || null);
      })
      .catch((e) => {
        console.error(e);
        setError("Could not connect to RecoverAI. Make sure FastAPI is running on port 8000.");
      })
      .finally(() => setLoadingPayments(false));
  }, []);

  useEffect(() => {
    fetch(`${API_URL}/evaluation/summary`)
      .then((r) => r.json())
      .then((data) => {
        if (data?.available && data?.summary) {
          setSummary(data.summary);
          setFilename(data.filename || "");
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setAnalysis(null);
      return;
    }
    setLoadingAnalysis(true);
    setAnalysis(null);
    fetch(`${API_URL}/payments/${selectedId}/analyze`)
      .then((r) => {
        if (!r.ok) throw new Error("Unable to analyze payment.");
        return r.json();
      })
      .then(setAnalysis)
      .catch((e) => {
        console.error(e);
        setError("Unable to analyze the selected payment.");
      })
      .finally(() => setLoadingAnalysis(false));
  }, [selectedId]);

  const failedPayments = useMemo(() => payments.filter((p) => p.status === "failed"), [payments]);
  const failedValue = useMemo(() => failedPayments.reduce((n, p) => n + (p.amount || 0), 0), [failedPayments]);
  const selectedPayment = useMemo(() => payments.find((p) => p.id === selectedId) || null, [payments, selectedId]);

  function selectPayment(id, destination = "workspace") {
    setSelectedId(id);
    setPage(destination);
  }

  async function uploadCsv(file) {
    if (!file) return;
    setUploading(true);
    setEvaluationError("");
    try {
      const body = new FormData();
      body.append("file", file);
      const response = await fetch(`${API_URL}/evaluation/upload`, { method: "POST", body });
      const data = await response.json();
      if (!response.ok || !data?.available || !data?.summary) {
        throw new Error(data?.message || "The evaluation upload could not be completed.");
      }
      setSummary(data.summary);
      setFilename(data.filename || file.name);
      setPage("evaluation");
    } catch (e) {
      console.error(e);
      setEvaluationError(e?.message || "Unable to upload the CSV. Make sure FastAPI is running.");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  if (loadingPayments && payments.length === 0) {
    return <div className="app-shell"><Sidebar activePage={page} navigate={setPage}/><main className="main"><header className="topbar"><div><div className="breadcrumb">RecoverAI</div><h1>Overview</h1></div><div className="topbar-right"><div className="connection"><span className="status-dot"/>Connecting to Razorpay</div><div className="top-avatar">G</div></div></header><div className="content"><div className="card" style={{padding:40}}>Loading RecoverAI data...</div></div></main></div>;
  }

  return <div className="app-shell">
    <Sidebar activePage={page} navigate={setPage}/>
    <main className="main">
      <header className="topbar">
        <div><div className="breadcrumb">RecoverAI <span>/</span> {pageTitle(page)}</div><h1>{pageTitle(page)}</h1></div>
        <div className="topbar-right"><div className="connection"><span className="status-dot"/>Razorpay connected</div><div className="top-avatar">G</div></div>
      </header>
      {error && <Alert>{error}</Alert>}
      {page === "overview" && <Overview failedPayments={failedPayments} failedValue={failedValue} analysis={analysis} selectedPayment={selectedPayment} loadingAnalysis={loadingAnalysis} navigate={setPage} selectPayment={selectPayment}/>}
      {page === "opportunities" && <Opportunities payments={failedPayments} selectedId={selectedId} selectPayment={selectPayment}/>}
      {page === "workspace" && <Workspace analysis={analysis} payment={selectedPayment} loading={loadingAnalysis} navigate={setPage}/>}
      {page === "results" && <Results analysis={analysis} payment={selectedPayment} navigate={setPage}/>}
      {page === "evaluation" && <EvaluationImpact summary={summary} filename={filename} uploading={uploading} error={evaluationError} fileRef={fileRef} onFile={(e)=>uploadCsv(e.target.files?.[0])} chooseFile={()=>fileRef.current?.click()}/>}
    </main>
  </div>;
}

function Alert({children}) {
  return <div style={{margin:"16px 42px 0",padding:"12px 15px",background:"#fef3f2",border:"1px solid #fecdca",borderRadius:8,color:"#b42318",fontSize:12}}>{children}</div>;
}
function Sidebar({activePage,navigate}) {
  return <aside className="sidebar">
    <div className="brand"><div className="brand-mark">R</div><div><div className="brand-name">RecoverAI</div><div className="brand-subtitle">Revenue recovery</div></div></div>
    <div className="sidebar-section"><div className="sidebar-label">WORKSPACE</div>
      <NavItem icon="⌂" label="Overview" active={activePage==="overview"} onClick={()=>navigate("overview")}/>
      <NavItem icon="↗" label="Recovery Opportunities" active={activePage==="opportunities"} onClick={()=>navigate("opportunities")}/>
      <NavItem icon="◇" label="Decision Workspace" active={activePage==="workspace"} onClick={()=>navigate("workspace")}/>
      <NavItem icon="✓" label="Recovery Results" active={activePage==="results"} onClick={()=>navigate("results")}/>
      <NavItem icon="▣" label="Evaluation & Impact" active={activePage==="evaluation"} onClick={()=>navigate("evaluation")}/>
    </div>
    <div className="sidebar-bottom"><div className="engine-status"><span className="status-dot"/><div><strong>Recovery engine</strong><small>Operational</small></div></div><div className="merchant"><div className="merchant-avatar">M</div><div><strong>Merchant account</strong><small>Razorpay connected</small></div></div></div>
  </aside>;
}
function NavItem({icon,label,active,onClick}) { return <button type="button" className={`nav-item ${active?"active":""}`} onClick={onClick}><span>{icon}</span>{label}</button>; }

function Overview({failedPayments,failedValue,analysis,selectedPayment,loadingAnalysis,navigate,selectPayment}) {
  return <div className="content">
    <section className="hero-section"><div><div className="eyebrow">RECOVERY INTELLIGENCE</div><h2>Recover revenue with better decisions.</h2><p>RecoverAI analyzes failed payments, customer history and recovery signals to identify the safest next action.</p></div><button className="primary-button" onClick={()=>navigate("opportunities")}>View opportunities →</button></section>
    <section className="stats-grid"><Stat label="Failed payments" value={failedPayments.length} note="from Razorpay"/><Stat label="Failed payment value" value={formatCurrency(failedValue)} note="current payment set"/><Stat label="Recovery score" value={analysis?.score?.score??"—"} note={analysis?.score?.tier?`${analysis.score.tier} opportunity`:"Analyze a payment"}/><Stat label="Recommended action" value={actionLabel(analysis?.recommendation?.action)} note={analysis?.recommendation?.confidence?`${analysis.recommendation.confidence} confidence`:"Awaiting analysis"}/></section>
    <section className="dashboard-grid">
      <div className="card opportunity-card"><div className="card-header"><div><div className="eyebrow">TOP OPPORTUNITY</div><h3>Payment needs attention</h3></div><span className="badge warning">{analysis?.score?.tier||"—"}</span></div><div className="payment-row"><div><div className="field-label">PAYMENT</div><strong>{formatPaymentId(selectedPayment?.id)}</strong></div><div className="amount">{formatCurrency(selectedPayment?.amount)}</div></div><div className="score-section"><div className="score-ring"><strong>{analysis?.score?.score??"—"}</strong><span>/ 100</span></div><div className="score-copy"><div className="field-label">RECOVERY SCORE</div><strong>{loadingAnalysis?"Analyzing...":analysis?.recommendation?.title||"Awaiting analysis"}</strong><p>{analysis?.recommendation?.reason||"RecoverAI is evaluating this payment."}</p></div></div><button className="secondary-button full" disabled={!selectedPayment} onClick={()=>selectedPayment&&selectPayment(selectedPayment.id,"workspace")}>Open decision workspace →</button></div>
      <Signals analysis={analysis}/>
    </section>
    <Activity payments={failedPayments.slice(0,5)} navigate={navigate}/>
  </div>;
}
function Stat({label,value,note}) { return <div className="stat-card"><div className="stat-label">{label}</div><div className="stat-value">{value}</div><div className="stat-change">{note}</div></div>; }
function Signals({analysis}) { const signals=analysis?.diagnosis?.signals||[]; return <div className="card signals-card"><div className="eyebrow">AI SIGNALS</div><h3>Why this payment matters</h3><div className="signals-list">{signals.length?signals.map((s,i)=><div className="signal" key={i}><span className="signal-check">✓</span>{s}</div>):<div className="signal">Waiting for payment analysis...</div>}</div></div>; }
function Activity({payments,navigate}) { return <div className="card activity-card"><div className="card-header"><div><div className="eyebrow">RECENT ACTIVITY</div><h3>Failed payment opportunities</h3></div><button className="text-button" onClick={()=>navigate("opportunities")}>View all →</button></div><div className="table"><div className="table-row table-head"><div>PAYMENT</div><div>AMOUNT</div><div>FAILURE</div><div>STATUS</div><div>RECOVERY</div></div>{payments.map(p=><div className="table-row" key={p.id}><div className="payment-id">{formatPaymentId(p.id)}</div><div>{formatCurrency(p.amount)}</div><div><span className="badge warning">{failureLabel(p)}</span></div><div>—</div><div>Analyze payment</div></div>)}</div></div>; }

function Opportunities({payments,selectedId,selectPayment}) { return <div className="content"><section className="page-intro"><div><div className="eyebrow">RECOVERY OPPORTUNITIES</div><h2>Failed payments worth reviewing.</h2><p>Review real failed Razorpay payments and send them through the RecoverAI decision pipeline.</p></div><div className="opportunity-summary"><span>{payments.length}</span><small>payments to review</small></div></section><div className="opportunity-list">{payments.map(p=><div className={`card opportunity-card ${p.id===selectedId?"selected":""}`} key={p.id}><div className="opportunity-main"><div className="opportunity-payment"><div className="field-label">PAYMENT</div><strong>{formatPaymentId(p.id)}</strong><span className="opportunity-source">Razorpay payment</span></div><div className="opportunity-amount"><div className="field-label">AMOUNT</div><strong>{formatCurrency(p.amount)}</strong></div><div className="opportunity-failure"><div className="field-label">FAILURE TYPE</div><span className="badge warning">{failureLabel(p)}</span></div><div className="opportunity-score"><div className="field-label">RECOVERY</div><strong>—</strong><span>Awaiting analysis</span></div><button className="primary-button opportunity-action" onClick={()=>selectPayment(p.id,"workspace")}>Analyze payment →</button></div></div>)}</div></div>; }

function Workspace({analysis,payment,loading,navigate}) {
  if(!payment) return <div className="content"><section className="page-intro"><div><div className="eyebrow">DECISION WORKSPACE</div><h2>Select a payment to review.</h2><p>Choose a failed payment from Recovery Opportunities.</p></div><button className="primary-button" onClick={()=>navigate("opportunities")}>View opportunities →</button></section></div>;
  const signals=analysis?.diagnosis?.signals||[];
  return <div className="content"><section className="page-intro"><div><div className="eyebrow">DECISION WORKSPACE</div><h2>Review this recovery decision.</h2><p>RecoverAI evaluates payment history, failure signals and guardrails before recommending the safest action.</p></div><button className="secondary-button" onClick={()=>navigate("opportunities")}>← Back to opportunities</button></section>
    <div className="card decision-card"><div className="decision-top"><div><div className="field-label">PAYMENT</div><h3>{formatPaymentId(payment.id)}</h3></div><div className="decision-amount">{formatCurrency(payment.amount)}</div></div></div>
    <div className="workspace-grid"><div className="decision-main"><div className="card decision-card"><div className="eyebrow">RECOVERY DECISION</div><div className="decision-score"><div className="score-ring large"><strong>{analysis?.score?.score??"—"}</strong><span>/ 100</span></div><div><div className="field-label">RECOMMENDED ACTION</div><h3>{loading?"Analyzing...":analysis?.recommendation?.title||"Awaiting decision"}</h3><p>{analysis?.recommendation?.reason||"RecoverAI is evaluating this payment."}</p></div></div></div><div className="card diagnosis-card"><div className="eyebrow">DIAGNOSIS</div><h3>Why RecoverAI reached this decision</h3><p>{analysis?.diagnosis?.summary||analysis?.diagnosis?.reason||"The payment analysis is being prepared."}</p></div><div className="ai-signals-card"><div className="eyebrow">AI SIGNALS</div><h3>Signals considered</h3><div className="signals-list">{signals.length?signals.map((s,i)=><div className="ai-signal" key={i}><span className="ai-signal-check">✓</span>{s}</div>):"No signals available yet."}</div></div></div><div className="decision-side"><div className="card guardrail-card"><div className="eyebrow">GUARDRAIL</div><h3>{analysis?.guardrail?.guardrail_triggered?"Guardrail triggered":"Guardrail check"}</h3><p>{analysis?.guardrail?.reason||"Evaluating recovery guardrails..."}</p></div><div className="card context-card"><div className="eyebrow">PAYMENT CONTEXT</div><h3>Selected payment</h3><div className="context-list"><div><span>Payment ID</span><strong>{formatPaymentId(payment.id)}</strong></div><div><span>Amount</span><strong>{formatCurrency(payment.amount)}</strong></div><div><span>Failure</span><strong>{failureLabel(payment)}</strong></div></div></div></div></div>
    <div className="card decision-actions-card"><div><div className="eyebrow">DECISION</div><h3>{analysis?.recommendation?.title||"Decision pending"}</h3></div><button className="primary-button" disabled={!analysis||loading} onClick={()=>navigate("results")}>Continue to result →</button></div>
  </div>;
}

function Results({analysis,payment,navigate}) { if(!analysis) return <div className="content"><section className="page-intro"><div><div className="eyebrow">RECOVERY RESULTS</div><h2>No recovery decision yet.</h2></div><button className="primary-button" onClick={()=>navigate("opportunities")}>View opportunities →</button></section></div>; const ex=analysis.execution; return <div className="content"><section className="page-intro"><div><div className="eyebrow">RECOVERY RESULTS</div><h2>Recovery decision completed.</h2><p>This result reflects the RecoverAI decision, guardrail evaluation and simulated execution.</p></div></section><div className="card result-card"><div className="result-icon">✓</div><div><div className="field-label">EXECUTION STATUS</div><h3>{ex?.action||analysis.recommendation?.action||"Decision completed"}</h3><p>{ex?.message||"The recovery decision has been evaluated."}</p></div><span className="badge success">{ex?.status||"Completed"}</span></div><div className="result-grid"><div className="card"><div className="eyebrow">DECISION</div><h3>{analysis.recommendation?.title||"No recommendation"}</h3><p>Confidence: {analysis.recommendation?.confidence||"—"}</p></div><div className="card"><div className="eyebrow">GUARDRAIL</div><h3>{analysis.guardrail?.guardrail_triggered?"Triggered":"Not triggered"}</h3><p>{analysis.guardrail?.reason||"No guardrail reason provided."}</p></div><div className="card"><div className="eyebrow">EXECUTION</div><h3 className="success-text">{ex?.executed?"Simulated":"Not executed"}</h3><p>No real payment retry was performed.</p></div></div>{payment&&<div className="card" style={{marginTop:18}}><div className="eyebrow">PAYMENT</div><h3>{formatPaymentId(payment.id)}</h3><p>{formatCurrency(payment.amount)}</p></div>}</div>; }

function EvaluationImpact({summary,filename,uploading,error,fileRef,onFile,chooseFile}) {
  const r=summary?.revenue||{}, rec=summary?.recovery||{}, safe=summary?.safety||{}, ai=summary?.ai_safety||{}, pol=summary?.policy||{}, acc=summary?.accuracy||{}, cls=summary?.classification||{};
  return <div className="content">
    <section className="page-intro"><div><div className="eyebrow">EVALUATION & IMPACT</div><h2>Measure recovery performance.</h2><p>Upload a batch evaluation dataset and see updated business impact, recovery and safety metrics.</p></div><div><input ref={fileRef} type="file" accept=".csv,text/csv" onChange={onFile} style={{display:"none"}}/><button className="primary-button" disabled={uploading} onClick={chooseFile}>{uploading?"Evaluating...":"Upload evaluation CSV ↑"}</button></div></section>
    {filename&&<div className="card" style={{padding:"11px 15px",marginBottom:18,fontSize:12}}>Latest evaluation: <strong>{filename}</strong>{summary?.total_cases!=null&&<> · {summary.total_cases} cases</>}</div>}
    {error&&<Alert>{error}</Alert>}
    {!summary&&!uploading&&<div className="card" style={{padding:35,marginBottom:20}}><div className="eyebrow">NO EVALUATION LOADED</div><h3>Upload a CSV to generate your metrics.</h3><p>The uploaded batch will be evaluated and displayed here.</p><button className="secondary-button" onClick={chooseFile}>Choose CSV file →</button></div>}
    {uploading&&<div className="card" style={{padding:24,marginBottom:20}}><strong>Evaluating uploaded batch...</strong><p style={{marginBottom:0}}>RecoverAI is running the AI evaluation pipeline and calculating the updated metrics.</p></div>}
    {summary&&<>
      <section style={{marginBottom:24}}><div className="eyebrow">REVENUE IMPACT</div><h2 style={{margin:"5px 0 12px"}}>Recovery value at a glance.</h2><div className="stats-grid"><Impact label="Revenue at risk" value={formatRupees(r.total_at_risk)} note="total payment value evaluated"/><Impact label="Recoverable revenue" value={formatRupees(r.recoverable_at_risk)} note="revenue classified as recoverable"/><Impact featured label="Recovery opportunity" value={formatRupees(r.recovery_opportunity)} note={`${pct(r.opportunity_rate)} opportunity rate`}/><Impact label="Safely blocked" value={formatRupees(r.safely_blocked)} note="non-recoverable revenue protected"/></div></section>
      <MetricSection title="RECOVERY PERFORMANCE"><div className="dashboard-grid"><Metric label="Recoverable cases" value={rec.recoverable_cases} note="recoverable cases"/><Metric label="Retry opportunities" value={rec.retry_opportunities} note="cases receiving retry opportunity"/><Metric label="Recovery recall" value={pct(rec.recall)} note="recoverable cases captured"/></div></MetricSection>
      <MetricSection title="SAFETY"><div className="dashboard-grid"><Metric featured label="Safety rate" value={pct(safe.safety_rate)} note="unsafe automatic retries prevented"/><Metric label="Unsafe final retries" value={safe.unsafe_final_retries??0} note="target: zero"/><Metric label="Non-recoverable cases" value={safe.non_recoverable_cases??0} note="cases requiring safe handling"/></div></MetricSection>
      <MetricSection title="AI / POLICY"><div className="dashboard-grid"><Metric label="AI accuracy" value={pct(acc.ai)} note="AI vs expected action"/><Metric label="Policy agreement" value={pct(pol.agreement_rate)} note={`${pol.ai_policy_agreements??0} agreements`}/><Metric label="Decisions changed downstream" value={pct(pol.decision_change_rate)} note={`${pol.decisions_changed??0} decisions changed`}/><Metric label="AI unsafe recommendations" value={ai.unsafe_recommendations??0} note="unsafe AI retry recommendations"/></div></MetricSection>
      <MetricSection title="CLASSIFICATION PERFORMANCE"><div className="card" style={{overflowX:"auto"}}><table style={tableStyle}><thead><tr><th style={th}>ACTION</th><th style={th}>PRECISION</th><th style={th}>RECALL</th></tr></thead><tbody>{ACTIONS.map(a=><tr key={a}><td style={td}>{actionLabel(a)}</td><td style={td}>{pct(cls.precision?.[a])}</td><td style={td}>{pct(cls.recall?.[a])}</td></tr>)}</tbody></table></div></MetricSection>
      <MetricSection title="CONFUSION MATRIX"><div className="card" style={{overflowX:"auto"}}><table style={{...tableStyle,minWidth:700}}><thead><tr><th style={th}>EXPECTED</th>{ACTIONS.map(a=><th style={th} key={a}>{actionLabel(a)}</th>)}</tr></thead><tbody>{ACTIONS.map(e=><tr key={e}><td style={td}>{actionLabel(e)}</td>{ACTIONS.map(a=><td style={{...td,textAlign:"center",fontWeight:800}} key={a}>{cls.confusion_matrix?.[e]?.[a]??0}</td>)}</tr>)}</tbody></table></div></MetricSection>
      <div className="card" style={{padding:24,display:"flex",justifyContent:"space-between",alignItems:"center",gap:20,flexWrap:"wrap"}}><div><div className="eyebrow">RUN ANOTHER EVALUATION</div><h3 style={{margin:"5px 0"}}>Replace these metrics with another batch.</h3><p style={{margin:0}}>Upload another CSV to generate a fresh snapshot.</p></div><button className="primary-button" disabled={uploading} onClick={chooseFile}>{uploading?"Evaluating...":"Upload another CSV →"}</button></div>
    </>}
  </div>;
}

function Impact({label,value,note,featured}) { return <div className="stat-card" style={featured?{border:"1px solid #b8c7e8",boxShadow:"0 4px 16px rgba(16,42,90,.08)"}:undefined}><div className="stat-label">{label}</div><div className="stat-value" style={featured?{fontSize:28}:undefined}>{value}</div><div className="stat-change">{note}</div></div>; }
function Metric({label,value,note,featured}) { return <div className="card" style={{padding:22,minHeight:120,border:featured?"1px solid #b8c7e8":undefined}}><div className="stat-label">{label}</div><div style={{marginTop:10,fontSize:25,fontWeight:800,color:"#101828"}}>{value}</div><div style={{marginTop:8,fontSize:11,color:"#98a2b3"}}>{note}</div></div>; }
function MetricSection({title,children}) { return <section style={{marginBottom:24}}><div className="eyebrow">{title}</div>{children}</section>; }

const tableStyle={width:"100%",borderCollapse:"collapse",fontSize:12};
const th={textAlign:"left",padding:"12px 10px",borderBottom:"1px solid #eaecf0",color:"#667085",fontSize:10,textTransform:"uppercase",letterSpacing:".08em"};
const td={padding:"13px 10px",borderBottom:"1px solid #f2f4f7",color:"#344054"};

function pageTitle(page) {
  return {overview:"Overview",opportunities:"Recovery Opportunities",workspace:"Decision Workspace",results:"Recovery Results",evaluation:"Evaluation & Impact"}[page] || "Overview";
}

export default App;
