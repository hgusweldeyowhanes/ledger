import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { blogApi } from "../api/blog";
import PostCard from "../components/PostCard";
import { useAuth } from "../context/AuthContext";

export default function Studio() {
  const { isAuth, loading } = useAuth();
  const [mine, setMine] = useState([]);
  const [saved, setSaved] = useState([]);
  const [pending, setPending] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [seriesTitle, setSeriesTitle] = useState("");
  const [seriesDesc, setSeriesDesc] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    const [m, s, p, a] = await Promise.all([
      blogApi.mine(),
      blogApi.saved(),
      blogApi.pendingComments().catch(() => ({ results: [] })),
      blogApi.analytics().catch(() => null),
    ]);
    setMine(m.results || []);
    setSaved(s.results || []);
    setPending(p.results || []);
    setAnalytics(a);
  };

  useEffect(() => {
    if (isAuth) load().catch((e) => setMsg(e.message));
  }, [isAuth]);

  if (loading) return <p className="empty">Loading…</p>;
  if (!isAuth) return <Navigate to="/login" replace />;

  const moderate = async (id, action) => {
    if (action === "approve") await blogApi.approveComment(id);
    else await blogApi.rejectComment(id);
    load();
  };

  const createSeries = async (e) => {
    e.preventDefault();
    await blogApi.createSeries({ title: seriesTitle, description: seriesDesc });
    setSeriesTitle("");
    setSeriesDesc("");
    setMsg("Series created.");
  };

  const totals = analytics?.totals || {};

  return (
    <>
      <section className="hero compact">
        <h1>Studio</h1>
        <p className="lede">Drafts, moderation, series, and readership analytics.</p>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginTop: "0.5rem" }}>
          <Link className="btn" to="/write">
            Write
          </Link>
          <Link className="btn ghost" to="/analytics">
            View Full Analytics →
          </Link>
        </div>
      </section>
      {msg ? <p className="flash">{msg}</p> : null}

      {/* Studio Analytics Snapshot */}
      {analytics && (
        <section className="studio-analytics-snapshot">
          <div className="section-header-flex">
            <h2>Performance Snapshot</h2>
            <Link to="/analytics" className="link-subtle">
              Deep-dive metrics & trends →
            </Link>
          </div>
          <div className="analytics-kpi-grid mini">
            <div className="kpi-card">
              <span className="kpi-label">Total Views</span>
              <div className="kpi-value">{totals.views?.toLocaleString() || 0}</div>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Total Likes</span>
              <div className="kpi-value">{totals.likes?.toLocaleString() || 0}</div>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Bookmarks</span>
              <div className="kpi-value">{totals.bookmarks?.toLocaleString() || 0}</div>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Followers</span>
              <div className="kpi-value">{totals.followers?.toLocaleString() || 0}</div>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Engagement</span>
              <div className="kpi-value">{totals.engagement_rate || 0}%</div>
            </div>
          </div>
        </section>
      )}

      <section className="moderation">
        <h2>Pending comments</h2>
        <ul className="mod-list">
          {pending.map((c) => (
            <li key={c.id}>
              <p>
                <strong>{c.author?.username}</strong> on{" "}
                <Link to={`/post/${c.post_slug}`}>{c.post_title}</Link>
              </p>
              <p>{c.body}</p>
              <div className="inline-forms">
                <button type="button" className="btn" onClick={() => moderate(c.id, "approve")}>
                  Approve
                </button>
                <button type="button" className="btn ghost" onClick={() => moderate(c.id, "reject")}>
                  Reject
                </button>
              </div>
            </li>
          ))}
          {!pending.length ? <li className="empty">No comments waiting.</li> : null}
        </ul>
      </section>

      <h2>Your posts</h2>
      <table className="table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Status</th>
            <th>Views</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {mine.map((p) => (
            <tr key={p.id}>
              <td>
                <Link to={`/post/${p.slug}`}>{p.title}</Link>
              </td>
              <td>{p.status}</td>
              <td>{p.view_count}</td>
              <td>
                <Link to={`/write/${p.slug}`}>Edit</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <form className="stack series-create" onSubmit={createSeries}>
        <h3>New series</h3>
        <label>Title</label>
        <input value={seriesTitle} onChange={(e) => setSeriesTitle(e.target.value)} required />
        <label>Description</label>
        <textarea rows={3} value={seriesDesc} onChange={(e) => setSeriesDesc(e.target.value)} />
        <button className="btn" type="submit">
          Create series
        </button>
      </form>

      <h2>Saved</h2>
      <div className="grid">
        {saved.map((p) => (
          <PostCard key={p.id} post={p} />
        ))}
        {!saved.length ? <p className="empty">Nothing saved yet.</p> : null}
      </div>
    </>
  );
}
