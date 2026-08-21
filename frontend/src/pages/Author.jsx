import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { blogApi } from "../api/blog";
import PostCard from "../components/PostCard";
import { useAuth } from "../context/AuthContext";

export default function Author() {
  const { username } = useParams();
  const { user, isAuth } = useAuth();
  const [posts, setPosts] = useState([]);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    blogApi
      .posts({ author__username: username })
      .then((d) => setPosts(d.results || []))
      .catch((e) => setErr(e.message));
  }, [username]);

  // filterset uses author which is pk - need to check. Looking at filterset_fields = ["status", "featured", "author", "categories__slug", "tags__slug"]
  // author is pk not username. So author__username won't work unless django-filter supports it via related lookup... filterset_fields with author only accepts pk.
  // I need to fix - either add author__username to filter or filter client side from all posts, or search.
  // Better: use search or fix API. Quick fix on frontend: fetch posts and filter, or add filter.
  // I'll update API filterset to include author__username

  const follow = async () => {
    const res = await blogApi.follow(username);
    setMsg(res.following ? `Following ${username}` : `Unfollowed ${username}`);
  };

  return (
    <>
      <section className="hero compact">
        <h1>{username}</h1>
        <p className="lede">Published work</p>
        {isAuth && user?.username !== username ? (
          <button type="button" className="btn" onClick={follow}>
            Follow / Unfollow
          </button>
        ) : null}
        {msg ? <p className="meta">{msg}</p> : null}
      </section>
      {err ? <p className="empty">{err}</p> : null}
      <div className="grid full">
        {posts.map((p) => (
          <PostCard key={p.id} post={p} />
        ))}
      </div>
      {!posts.length && !err ? (
        <p className="empty">
          No posts. <Link to="/">Home</Link>
        </p>
      ) : null}
    </>
  );
}
