import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { blogApi } from "../api/blog";
import { useAuth } from "../context/AuthContext";

export default function Notifications() {
  const { isAuth, loading } = useAuth();
  const [items, setItems] = useState([]);
  const [err, setErr] = useState("");

  const load = () =>
    blogApi
      .notifications()
      .then((d) => setItems(d.results || d || []))
      .catch((e) => setErr(e.message));

  useEffect(() => {
    if (isAuth) load();
  }, [isAuth]);

  if (loading) return <p className="empty">Loading…</p>;
  if (!isAuth) return <Navigate to="/login" replace />;

  const markAll = async () => {
    await blogApi.markNotificationsRead();
    load();
  };

  const label = (n) => {
    if (n.verb === "liked") return "liked your post";
    if (n.verb === "commented") return "commented on your post";
    if (n.verb === "followed") return "followed you";
    if (n.verb === "comment_approved") return "approved your comment";
    return n.verb;
  };

  return (
    <>
      <section className="hero compact">
        <h1>Notifications</h1>
        <p className="lede">Likes, comments, follows, and approvals.</p>
        <button type="button" className="btn ghost" onClick={markAll}>
          Mark all read
        </button>
      </section>
      {err ? <p className="empty">{err}</p> : null}
      <ul className="notif-list">
        {items.map((n) => (
          <li key={n.id} className={n.is_read ? "" : "unread"}>
            <strong>{n.actor?.username || "Ledger"}</strong> {label(n)}
            {n.post_slug ? (
              <>
                {" · "}
                <Link to={`/post/${n.post_slug}`}>{n.post_title}</Link>
              </>
            ) : null}
            <time>{new Date(n.created_at).toLocaleString()}</time>
          </li>
        ))}
      </ul>
      {!items.length ? <p className="empty">No notifications yet.</p> : null}
    </>
  );
}
