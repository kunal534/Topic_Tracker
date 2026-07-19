import { FormEvent, useState } from "react";
import { useMutation, useQuery } from "@apollo/client/react";
import {
  CREATE_TOPIC, LOGIN, MARK_READ, REGISTER, SUBSCRIBE, SUBSCRIPTIONS,
  TOPIC_UPDATES, UNSUBSCRIBE,
} from "./operations";

type Topic = { id: string; name: string; baselineSummary?: string | null; baselineUpdatedAt?: string | null };
type Subscription = { id: string; cadence: string; active: boolean; topic: Topic };
type Update = { id: string; title: string; summary: string; confidence: string; detectedAt: string; sourceUrls: string[]; serviceNotice?: string | null };
type Notification = { id: string; read: boolean; createdAt: string; topicUpdate: Update };

function AuthScreen({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [message, setMessage] = useState("");
  const [login] = useMutation(LOGIN);
  const [register] = useMutation(REGISTER);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    try {
      const action = mode === "login" ? login : register;
      const result = await action({ variables: { email, password } });
      const token = mode === "login" ? result.data.login.accessToken : result.data.register.accessToken;
      localStorage.setItem("topic-tracker-token", token);
      onAuthenticated();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to authenticate");
    }
  }

  return <main className="auth-shell"><section className="auth-card">
    <p className="eyebrow">TOPIC TRACKER</p><h1>Stay ahead of the conversation.</h1>
    <p>Subscribe once. Get the change, not the noise.</p>
    <form onSubmit={submit}>
      <label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
      <label>Password<input type="password" minLength={12} value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
      {message && <p className="error">{message}</p>}
      <button>{mode === "login" ? "Log in" : "Create account"}</button>
    </form>
    <button className="text-button" onClick={() => setMode(mode === "login" ? "register" : "login")}> {mode === "login" ? "Need an account? Register" : "Already registered? Log in"} </button>
  </section></main>;
}

function Updates({ topic }: { topic: Topic }) {
  const { data, loading } = useQuery<{ topicUpdates: Update[] }>(TOPIC_UPDATES, { variables: { topicId: topic.id }, pollInterval: 30_000 });
  return <section className="updates"><div className="section-heading"><div><p className="eyebrow">TOPIC TIMELINE</p><h2>{topic.name}</h2></div><span className="badge">Monitoring</span></div>
    {topic.baselineSummary && <aside className="baseline"><strong>Current baseline</strong><p>{topic.baselineSummary}</p></aside>}
    {loading ? <p>Loading updates…</p> : data?.topicUpdates.length ? data.topicUpdates.map((update) => <article className="update-card" key={update.id}>
      <div className="update-meta"><span>{update.confidence} confidence</span><time>{new Date(update.detectedAt).toLocaleString()}</time></div>
      <h3>{update.title}</h3><p>{update.summary}</p>
      {update.serviceNotice ? <p className="notice">{update.serviceNotice}</p> : null}
      {update.sourceUrls.filter((url) => /^https?:\/\//i.test(url)).map((url) => <a key={url} href={url} target="_blank" rel="noreferrer">View source ↗</a>)}
    </article>) : <div className="empty">No material updates yet. We’ll add them here when the topic changes.</div>}
  </section>;
}

function Dashboard({ onLogout }: { onLogout: () => void }) {
  const [topicName, setTopicName] = useState("");
  const [cadence, setCadence] = useState("daily");
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);
  const { data, loading, refetch } = useQuery<{ subscriptions: Subscription[]; notifications: Notification[] }>(SUBSCRIPTIONS, { fetchPolicy: "cache-and-network", pollInterval: 30_000 });
  const [createTopic] = useMutation(CREATE_TOPIC);
  const [subscribe] = useMutation(SUBSCRIBE);
  const [unsubscribe] = useMutation(UNSUBSCRIBE);
  const [markRead] = useMutation(MARK_READ);

  async function addTopic(event: FormEvent) {
    event.preventDefault();
    if (!topicName.trim()) return;
    const created = await createTopic({ variables: { name: topicName } });
    await subscribe({ variables: { topicId: created.data.createTopic.id, cadence } });
    setTopicName("");
    await refetch();
    if (created.data?.createTopic?.id) {
      setSelectedTopic({ id: created.data.createTopic.id, name: topicName.trim(), baselineSummary: null, baselineUpdatedAt: null });
    }
  }
  const subscriptions = data?.subscriptions ?? [];
  const active = selectedTopic ?? subscriptions[0]?.topic ?? null;

  return <main className="app-shell"><header><div><p className="eyebrow">TOPIC TRACKER</p><h1>Your signal desk</h1></div><button className="text-button" onClick={onLogout}>Log out</button></header>
    <div className="layout"><aside className="sidebar"><form className="topic-form" onSubmit={addTopic}><label>Add a topic<input placeholder="e.g. India AI regulation" value={topicName} onChange={(e) => setTopicName(e.target.value)} /></label><label>Alert cadence<select value={cadence} onChange={(e) => setCadence(e.target.value)}><option value="immediate">Immediate</option><option value="daily">Daily digest</option><option value="weekly">Weekly digest</option></select></label><button>Start monitoring</button></form>
      <nav><p className="eyebrow">SUBSCRIPTIONS</p>{loading ? <p>Loading…</p> : subscriptions.map((subscription) => <div className="subscription-row" key={subscription.id}><button className={active?.id === subscription.topic.id ? "topic-button selected" : "topic-button"} onClick={() => setSelectedTopic(subscription.topic)}>{subscription.topic.name}</button><button className="icon-button" title="Unsubscribe" onClick={async () => { await unsubscribe({ variables: { subscriptionId: subscription.id } }); setSelectedTopic(null); await refetch(); }}>×</button></div>)}</nav>
      <section className="notifications"><p className="eyebrow">RECENT ALERTS</p>{data?.notifications.map((notification) => <button className={notification.read ? "notification read" : "notification"} key={notification.id} onClick={async () => { await markRead({ variables: { notificationId: notification.id }, optimisticResponse: { markNotificationRead: true } }); await refetch(); }}><strong>{notification.topicUpdate.title}</strong><span>{new Date(notification.createdAt).toLocaleDateString()}</span></button>)}</section>
    </aside>{active ? <Updates topic={active} /> : <section className="updates empty">Add your first topic to begin monitoring.</section>}</div>
  </main>;
}

export default function App() {
  const isDevelopment = process.env.REACT_APP_ENV !== "production";
  const [authenticated, setAuthenticated] = useState(() => Boolean(localStorage.getItem("topic-tracker-token")) || isDevelopment);

  function handleLogout() {
    localStorage.removeItem("topic-tracker-token");
    setAuthenticated(false);
  }

  return authenticated ? <Dashboard onLogout={handleLogout} /> : <AuthScreen onAuthenticated={() => setAuthenticated(true)} />;
}
