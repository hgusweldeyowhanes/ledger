import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { blogApi } from "../api/blog";
import PostCard from "../components/PostCard";

export default function Popular() {
  const [posts, setPosts] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    blogApi
      .popular()
      .then((d) => setPosts(d.results || []))
      .catch((e) => setErr(e.message));
  }, []);

  return (
    <>
      <section className="hero compact">
        <h1>Popular</h1>
        <p className="lede">The stories readers keep coming back to.</p>
      </section>

      {err ? <p className="empty">{err}</p> : null}
      <div className="grid full">
        {posts.map((post) => (
          <PostCard key={post.id} post={post} />
        ))}
      </div>
      {!posts.length && !err ? (
        <p className="empty">
          No popular stories yet. <Link to="/">Browse the latest</Link>
        </p>
      ) : null}
    </>
  );
}
