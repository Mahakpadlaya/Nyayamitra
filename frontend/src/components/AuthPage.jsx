import { useState } from "react";
import { postLogin, postSignup } from "../api";
import { setAuth } from "../authStorage";

export function AuthPage({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data =
        mode === "login"
          ? await postLogin({ email: email.trim(), password })
          : await postSignup({
              email: email.trim(),
              password,
              first_name: firstName.trim(),
              last_name: lastName.trim(),
            });
      setAuth(data.access_token, data.user);
      onAuthenticated(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-screen">
      <div className="app-bg" aria-hidden />
      <div className="auth-card">
        <div className="auth-brand">
          <span className="brand-icon" aria-hidden>
            ⚖
          </span>
          <h1 className="auth-title">NyayaMitra</h1>
          <p className="auth-sub">
            Sign in to use the educational legal assistant (India · RAG).
          </p>
        </div>

        <div className="auth-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "login"}
            className={`auth-tab ${mode === "login" ? "auth-tab-on" : ""}`}
            onClick={() => {
              setMode("login");
              setError(null);
            }}
          >
            Log in
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "signup"}
            className={`auth-tab ${mode === "signup" ? "auth-tab-on" : ""}`}
            onClick={() => {
              setMode("signup");
              setError(null);
            }}
          >
            Sign up
          </button>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {mode === "signup" && (
            <div className="auth-row">
              <label className="auth-label" htmlFor="auth-first">
                First name <span className="auth-req">*</span>
              </label>
              <input
                id="auth-first"
                className="auth-input"
                type="text"
                required
                autoComplete="given-name"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                disabled={loading}
              />
              <label className="auth-label" htmlFor="auth-last">
                Last name <span className="auth-req">*</span>
              </label>
              <input
                id="auth-last"
                className="auth-input"
                type="text"
                required
                autoComplete="family-name"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                disabled={loading}
              />
            </div>
          )}

          <label className="auth-label" htmlFor="auth-email">
            Email <span className="auth-req">*</span>
          </label>
          <input
            id="auth-email"
            className="auth-input"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
          />

          <label className="auth-label" htmlFor="auth-password">
            Password <span className="auth-req">*</span>
            {mode === "signup" && (
              <span className="auth-hint"> (min. 8 characters)</span>
            )}
          </label>
          <input
            id="auth-password"
            className="auth-input"
            type="password"
            required
            minLength={mode === "signup" ? 8 : 1}
            autoComplete={
              mode === "login" ? "current-password" : "new-password"
            }
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
          />

          {error && (
            <p className="auth-error" role="alert">
              {error}
            </p>
          )}

          <button
            type="submit"
            className="btn-primary auth-submit"
            disabled={loading}
          >
            {loading
              ? "Please wait…"
              : mode === "login"
                ? "Log in"
                : "Create account"}
          </button>
        </form>
      </div>
    </div>
  );
}
