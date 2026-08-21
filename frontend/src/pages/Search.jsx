import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { blogApi } from "../api/blog";
import PostCard from "../components/PostCard";

export default function Search() {
  const [params] = useSearchParams();
  const q = params.get("q") || "";
  const [posts, setPosts] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    let alive = true;
    blogApi
      .posts({ search: q })
      .then((data) => alive && setPosts(data.results || []))
      .catch((e) => alive && setErr(e.message));
    return () => {
      alive = false;
    };
  }, [q]);

  return (
    <>
      <section className="hero compact">
        <h1>Search</h1>
        <p className="lede">{q ? `Results for “${q}”` : "Type a keyword in the header."}</p>
      </section>
      {err ? <p className="empty">{err}</p> : null}
      <div className="grid full">
        {posts.map((post) => (
          <PostCard key={post.id} post={post} />
        ))}
      </div>
      {!err && !posts.length ? <p className="empty">Nothing matched.</p> : null}
      <p className="meta">
        <Link to="/">← Home</Link>
      </p>
    </>
  );
}
