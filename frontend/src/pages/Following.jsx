import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { blogApi } from "../api/blog";
import PostCard from "../components/PostCard";
import { useAuth } from "../context/AuthContext";

export default function Following() {
  const { isAuth, loading } = useAuth();
  const [posts, setPosts] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!isAuth) return;
    blogApi
      .followingFeed()
      .then((d) => setPosts(d.results || []))
      .catch((e) => setErr(e.message));
  }, [isAuth]);

  if (loading) return <p className="empty">Loading…</p>;
  if (!isAuth) return <Navigate to="/login" replace />;

  return (
    <>
      <section className="hero compact">
        <h1>Following</h1>
        <p className="lede">New work from authors you follow.</p>
      </section>
      {err ? <p className="empty">{err}</p> : null}
      <div className="grid full">
        {posts.map((p) => (
          <PostCard key={p.id} post={p} />
        ))}
      </div>
      {!posts.length && !err ? (
        <p className="empty">
          Follow authors from a post page. <Link to="/">Browse</Link>
        </p>
      ) : null}
    </>
  );
}
