import { useEffect, useState } from "react";
import "./App.css";
import { fetchMe } from "./api";
import { clearAuth, getStoredUser, getToken } from "./authStorage";
import { AuthPage } from "./components/AuthPage";
import { MainApp } from "./MainApp";

export default function App() {
  const [user, setUser] = useState(() => getStoredUser());
  const [checking, setChecking] = useState(() => Boolean(getToken()));

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setChecking(false);
      return;
    }
    fetchMe()
      .then((u) => {
        setUser(u);
        setChecking(false);
      })
      .catch(() => {
        clearAuth();
        setUser(null);
        setChecking(false);
      });
  }, []);

  if (checking) {
    return (
      <div className="auth-screen auth-screen-loading">
        <div className="app-bg" aria-hidden />
        <p className="auth-sub">Loading…</p>
      </div>
    );
  }

  if (!user || !getToken()) {
    return (
      <AuthPage
        onAuthenticated={(data) => {
          setUser(data.user);
        }}
      />
    );
  }

  return (
    <MainApp
      user={user}
      onLogout={() => {
        setUser(null);
      }}
    />
  );
}
