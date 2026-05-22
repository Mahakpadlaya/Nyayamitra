import { useEffect, useState } from "react";
import "./App.css";
import { fetchHealth } from "./api";
import { clearAuth } from "./authStorage";
import { ADVISOR } from "./avatars";
import { ChatPanel } from "./components/ChatPanel";
import { PlanPanel } from "./components/PlanPanel";

export function MainApp({ user, onLogout }) {
  const [tab, setTab] = useState("chat");
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState(null);

  useEffect(() => {
    fetchHealth()
      .then((h) => {
        setHealth(h);
        setHealthError(null);
      })
      .catch(() => {
        setHealth(null);
        setHealthError(
          "API unreachable — check backend or VITE_API_BASE_URL on Vercel",
        );
      });
  }, []);

  const synthOn = health?.synthesis_enabled ?? health?.openai_configured;
  const displayName = user
    ? `${user.first_name} ${user.last_name}`.trim()
    : "";

  function handleLogout() {
    clearAuth();
    onLogout();
  }

  return (
    <div className="app">
      <div className="app-bg" aria-hidden />

      <header className="header">
        <div className="header-inner">
          <div className="brand">
            <div className="brand-mark" aria-hidden>
              <span className="brand-icon">⚖</span>
            </div>
            <div>
              <p className="eyebrow">India · RAG · educational</p>
              <h1 className="title">
                <span className="title-accent">{ADVISOR.name}</span>
              </h1>
              <p className="subtitle">
                {ADVISOR.shortBio} — not a substitute for a real lawyer
              </p>
            </div>
          </div>

          <div className="status-cluster">
            {displayName && (
              <span className="pill pill-muted" title={user?.email}>
                {displayName}
              </span>
            )}
            <button
              type="button"
              className="btn-ghost auth-logout"
              onClick={handleLogout}
            >
              Log out
            </button>
            {healthError ? (
              <span className="pill pill-warn">{healthError}</span>
            ) : health ? (
              <>
                <span className="pill pill-glow">
                  <span className="dot dot-ok" />
                  {health.chroma_documents} chunks indexed
                </span>
                <span className={`pill ${synthOn ? "pill-glow" : "pill-muted"}`}>
                  <span className={`dot ${synthOn ? "dot-ok" : "dot-off"}`} />
                  {synthOn ? (
                    <>
                      LLM <strong>{health.llm_provider ?? "on"}</strong>
                    </>
                  ) : (
                    <>Add GROQ or GEMINI key</>
                  )}
                </span>
              </>
            ) : (
              <span className="pill pill-muted">Checking API…</span>
            )}
          </div>
        </div>

        <nav className="tabs" aria-label="Views">
          <div className="tabs-inner">
            <button
              type="button"
              className={`tab ${tab === "chat" ? "tab-on" : ""}`}
              onClick={() => setTab("chat")}
            >
              <span className="tab-icon">💬</span>
              Chat
            </button>
            <button
              type="button"
              className={`tab ${tab === "plan" ? "tab-on" : ""}`}
              onClick={() => setTab("plan")}
            >
              <span className="tab-icon">📋</span>
              Action plan
            </button>
          </div>
        </nav>
      </header>

      <main className="main">
        <div className="main-card">
          {tab === "chat" ? <ChatPanel /> : <PlanPanel />}
        </div>
      </main>

      <footer className="footer">
        <p>
          Outputs are for learning only. Verify against official sources and a
          qualified advocate for your matter.
        </p>
        <p className="footer-note">
          Face avatars via{" "}
          <a href="https://www.dicebear.com" target="_blank" rel="noreferrer">
            DiceBear
          </a>
          .
        </p>
      </footer>
    </div>
  );
}
