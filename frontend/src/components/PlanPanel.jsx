import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { postPlan } from "../api";
import { ADVISOR } from "../avatars";

function PlanCard({ title, children }) {
  return (
    <section className="plan-card">
      <h3 className="plan-card-h">{title}</h3>
      <div className="plan-card-body md">{children}</div>
    </section>
  );
}

function ListBlock({ items }) {
  if (!items?.length) return <p className="plan-empty">None listed.</p>;
  return (
    <ol className="plan-ol">
      {items.map((x, i) => (
        <li key={i}>{x}</li>
      ))}
    </ol>
  );
}

export function PlanPanel() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [plan, setPlan] = useState(null);
  const [sources, setSources] = useState([]);
  const [mode, setMode] = useState(null);
  const [error, setError] = useState(null);

  async function onSubmit(e) {
    e.preventDefault();
    const q = question.trim();
    if (!q || loading) return;
    setLoading(true);
    setError(null);
    setPlan(null);
    setSources([]);
    setMode(null);
    try {
      const data = await postPlan(q);
      setPlan(data.plan);
      setSources(data.sources);
      setMode(data.mode);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="plan-layout">
      <p className="toolbar-text">
        <strong>{ADVISOR.name}</strong> builds this via <kbd>/api/plan</kbd> —
        educational framing only.
      </p>

      <form className="plan-form" onSubmit={onSubmit}>
        <label className="plan-label" htmlFor="plan-q">
          Describe your question or situation
        </label>
        <textarea
          id="plan-q"
          className="composer-field plan-area"
          rows={4}
          placeholder="e.g. I want to understand reporting timelines under POCSO, or what documents help before seeing a lawyer…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          className="btn-primary"
          disabled={loading || !question.trim()}
        >
          {loading ? "Building plan…" : "Generate plan"}
        </button>
      </form>

      {error && (
        <div className="banner-error md">
          <ReactMarkdown>{`**Error**\n\n${error}`}</ReactMarkdown>
        </div>
      )}

      {plan && (
        <div className="plan-stack">
          {mode && (
            <p className="plan-meta">
              Model: <strong>{mode}</strong>
            </p>
          )}
          <PlanCard title="Understanding">
            <ReactMarkdown>{plan.understanding}</ReactMarkdown>
          </PlanCard>
          <PlanCard title="Relevant framework">
            <ReactMarkdown>{plan.relevant_framework}</ReactMarkdown>
          </PlanCard>
          <PlanCard title="Information to gather">
            <ListBlock items={plan.information_you_should_gather} />
          </PlanCard>
          <PlanCard title="Possible next steps">
            <ListBlock items={plan.possible_next_steps} />
          </PlanCard>
          <PlanCard title="Limits & risks">
            <ReactMarkdown>{plan.limits_and_risks}</ReactMarkdown>
          </PlanCard>
          <PlanCard title="When to consult a lawyer">
            <ReactMarkdown>{plan.consult_lawyer_when}</ReactMarkdown>
          </PlanCard>
          <PlanCard title="Disclaimer">
            <ReactMarkdown>{plan.disclaimer}</ReactMarkdown>
          </PlanCard>

          {sources.length > 0 && (
            <details className="src plan-src">
              <summary>Sources ({sources.length})</summary>
              <ol>
                {sources.map((s, j) => (
                  <li key={j}>
                    <span className="src-meta">
                      {s.distance != null ? `${s.distance.toFixed(4)} · ` : ""}
                      {s.metadata && Object.keys(s.metadata).length
                        ? JSON.stringify(s.metadata)
                        : ""}
                    </span>
                    <div className="src-snippet">{s.text}</div>
                  </li>
                ))}
              </ol>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
