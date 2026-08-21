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
  const [seriesTitle, setSeriesTitle] = useState("");
  const [seriesDesc, setSeriesDesc] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    const [m, s, p] = await Promise.all([
      blogApi.mine(),
      blogApi.saved(),
      blogApi.pendingComments().catch(() => ({ results: [] })),
    ]);
    setMine(m.results || []);
    setSaved(s.results || []);
    setPending(p.results || []);
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

  return (
    <>
      <section className="hero compact">
        <h1>Studio</h1>
        <p className="lede">Drafts, moderation, and saved essays.</p>
        <p>
          <Link className="btn" to="/write">
            Write
          </Link>
        </p>
      </section>
      {msg ? <p className="flash">{msg}</p> : null}

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
