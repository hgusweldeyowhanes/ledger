import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { blogApi } from "../api/blog";
import PostCard from "../components/PostCard";

export default function Trending() {
  const [posts, setPosts] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    blogApi
      .trending()
      .then((d) => setPosts(d.results || []))
      .catch((e) => setErr(e.message));
  }, []);

  return (
    <>
      <section className="hero compact">
        <h1>Trending</h1>
        <p className="lede">The stories everyone is reading right now.</p>
      </section>

      {err ? <p className="empty">{err}</p> : null}
      <div className="grid full">
        {posts.map((post) => (
          <PostCard key={post.id} post={post} />
        ))}
      </div>
      {!posts.length && !err ? (
        <p className="empty">
          No trending stories yet. <Link to="/">Browse the archive</Link>
        </p>
      ) : null}
    </>
  );
}
