import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { postChat } from "../api";
import {
  ADVISOR,
  USER_AVATAR_PRESETS,
  loadSavedUserAvatarUrl,
  saveUserAvatarUrl,
} from "../avatars";

const FEMALE_PRESETS = USER_AVATAR_PRESETS.filter((p) => p.gender === "female");
const MALE_PRESETS = USER_AVATAR_PRESETS.filter((p) => p.gender === "male");

const SUGGESTIONS = [
  "What does Article 21 protect?",
  "Explain the POCSO Act in brief.",
  "What is the difference between murder and culpable homicide?",
  "When is an offence typically non-bailable?",
];

function AvatarImg({ src, alt, className }) {
  return (
    <img
      src={src}
      alt={alt}
      className={className}
      loading="lazy"
      decoding="async"
      referrerPolicy="no-referrer"
    />
  );
}

function Avatar({ role, userAvatarUrl }) {
  if (role === "user") {
    return (
      <div className="avatar avatar-user avatar-ring" title="You">
        <AvatarImg
          src={userAvatarUrl}
          alt=""
          className="avatar-img"
        />
      </div>
    );
  }
  return (
    <div
      className="avatar avatar-bot avatar-ring avatar-law"
      title={`${ADVISOR.name} — AI advisor`}
    >
      <AvatarImg
        src={ADVISOR.avatarUrl}
        alt={ADVISOR.avatarAlt ?? ""}
        className="avatar-img avatar-img-law"
      />
    </div>
  );
}

export function ChatPanel() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [userAvatarUrl, setUserAvatarUrl] = useState(() =>
    loadSavedUserAvatarUrl(),
  );
  const [pickerOpen, setPickerOpen] = useState(false);
  const bottomRef = useRef(null);
  const pickerRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (!pickerOpen) return;
    function onPointerDown(e) {
      if (pickerRef.current && !pickerRef.current.contains(e.target)) {
        setPickerOpen(false);
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [pickerOpen]);

  function pickUserAvatar(url) {
    setUserAvatarUrl(url);
    saveUserAvatarUrl(url);
    setPickerOpen(false);
  }

  async function sendMessage(textOverride) {
    const q = (textOverride ?? input).trim();
    if (!q || loading) return;
    setInput("");
    const next = [...messages, { role: "user", content: q }];
    setMessages(next);
    setLoading(true);
    const payload = next.map(({ role, content }) => ({ role, content }));
    try {
      const data = await postChat(payload);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources,
          mode: data.mode,
        },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: `**Something went wrong**\n\n${err instanceof Error ? err.message : String(err)}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(e) {
    e.preventDefault();
    void sendMessage();
  }

  function clearChat() {
    if (loading) return;
    setMessages([]);
  }

  return (
    <div className="chat-layout">
      <div className="chat-toolbar">
        <div className="toolbar-left">
          <p className="toolbar-text">
            <strong>{ADVISOR.name}</strong> runs on <kbd>/api/chat</kbd> with
            your full thread for follow-ups.
          </p>
          <div className="avatar-picker-wrap" ref={pickerRef}>
            <button
              type="button"
              className="avatar-picker-trigger"
              onClick={(e) => {
                e.stopPropagation();
                setPickerOpen((o) => !o);
              }}
              aria-expanded={pickerOpen}
              aria-haspopup="dialog"
            >
              <AvatarImg
                src={userAvatarUrl}
                alt=""
                className="avatar-picker-thumb"
              />
              <span>Your look</span>
            </button>
            {pickerOpen ? (
              <div
                className="avatar-picker-popover"
                role="dialog"
                aria-label="Choose your avatar"
              >
                <p className="avatar-picker-title">Pick your avatar</p>
                <p className="avatar-picker-section">Female</p>
                <div className="avatar-picker-grid">
                  {FEMALE_PRESETS.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      className={`avatar-picker-opt ${userAvatarUrl === p.url ? "picked" : ""}`}
                      onClick={() => pickUserAvatar(p.url)}
                      title={`${p.label} (female preset)`}
                    >
                      <AvatarImg
                        src={p.url}
                        alt={p.label}
                        className="avatar-picker-opt-img"
                      />
                      <span className="avatar-picker-opt-label">{p.label}</span>
                    </button>
                  ))}
                </div>
                <p className="avatar-picker-section">Male</p>
                <div className="avatar-picker-grid">
                  {MALE_PRESETS.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      className={`avatar-picker-opt ${userAvatarUrl === p.url ? "picked" : ""}`}
                      onClick={() => pickUserAvatar(p.url)}
                      title={`${p.label} (male preset)`}
                    >
                      <AvatarImg
                        src={p.url}
                        alt={p.label}
                        className="avatar-picker-opt-img"
                      />
                      <span className="avatar-picker-opt-label">{p.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </div>
        <button
          type="button"
          className="btn-text"
          onClick={clearChat}
          disabled={loading || messages.length === 0}
        >
          Clear
        </button>
      </div>

      <div className="chat-scroll">
        {messages.length === 0 && !loading && (
          <div className="hero-empty">
            <div className="hero-advisor">
              <AvatarImg
                src={ADVISOR.avatarUrl}
                alt={ADVISOR.avatarAlt ?? ""}
                className="hero-advisor-img"
              />
              <div>
                <h2 className="hero-title">Hey, I&apos;m {ADVISOR.name}</h2>
                <p className="hero-tagline">{ADVISOR.shortBio}</p>
              </div>
            </div>
            <p className="hero-lead">
              Ask about the Constitution, stuff in your legal index, or
              procedure — I pull sources first, then explain.
            </p>
            <div className="chips">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  className="chip"
                  onClick={() => void sendMessage(s)}
                  disabled={loading}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="thread">
          {messages.map((msg, i) => (
            <div key={i} className={`row row-${msg.role}`}>
              <Avatar
                role={msg.role}
                userAvatarUrl={userAvatarUrl}
              />
              <div className={`bubble bubble-${msg.role}`}>
                <div className="bubble-top">
                  <span className="bubble-name">
                    {msg.role === "user" ? "You" : ADVISOR.name}
                  </span>
                  {msg.mode ? (
                    <span className="bubble-badge">{msg.mode}</span>
                  ) : null}
                </div>
                <div className="md">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
                {msg.sources?.length > 0 ? (
                  <details className="src">
                    <summary>
                      Sources · {msg.sources.length}
                    </summary>
                    <ol>
                      {msg.sources.map((s, j) => (
                        <li key={j}>
                          <span className="src-meta">
                            {s.distance != null
                              ? `${s.distance.toFixed(4)} · `
                              : ""}
                            {s.metadata && Object.keys(s.metadata).length
                              ? JSON.stringify(s.metadata)
                              : ""}
                          </span>
                          <div className="src-snippet">{s.text}</div>
                        </li>
                      ))}
                    </ol>
                  </details>
                ) : null}
              </div>
            </div>
          ))}

          {loading && (
            <div className="row row-assistant">
              <Avatar role="assistant" userAvatarUrl={userAvatarUrl} />
              <div className="bubble bubble-assistant bubble-pending">
                <div className="typing">
                  <span />
                  <span />
                  <span />
                </div>
                <span className="typing-label">
                  {ADVISOR.name} is thinking…
                </span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <form className="composer" onSubmit={onSubmit}>
        <div className="composer-inner">
          <AvatarImg
            src={userAvatarUrl}
            alt=""
            className="composer-avatar"
          />
          <textarea
            className="composer-field"
            rows={2}
            placeholder={`Message ${ADVISOR.name}…`}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void sendMessage();
              }
            }}
            disabled={loading}
          />
          <button
            type="submit"
            className="composer-send"
            disabled={loading || !input.trim()}
            aria-label="Send"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden>
              <path
                fill="currentColor"
                d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"
              />
            </svg>
          </button>
        </div>
      </form>
    </div>
  );
}
