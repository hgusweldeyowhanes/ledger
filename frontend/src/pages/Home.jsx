import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { blogApi } from "../api/blog";
import PostCard from "../components/PostCard";

export default function Home() {
  const [params] = useSearchParams();
  const [data, setData] = useState(null);
  const [cats, setCats] = useState([]);
  const [trending, setTrending] = useState([]);
  const [err, setErr] = useState("");
  const category = params.get("category") || "";

  useEffect(() => {
    let alive = true;
    setErr("");
    const q = { ordering: "-published_at" };
    if (category) q["categories__slug"] = category;
    Promise.all([
      blogApi.posts(q),
      blogApi.categories().catch(() => ({ results: [] })),
      blogApi.trending().catch(() => ({ results: [] })),
    ])
      .then(([posts, categories, trend]) => {
        if (!alive) return;
        setData(posts);
        setCats(categories.results || categories || []);
        setTrending(trend.results || trend || []);
      })
      .catch((e) => alive && setErr(e.message));
    return () => {
      alive = false;
    };
  }, [category]);

  const posts = data?.results || [];
  const featured = posts.find((p) => p.featured) || posts[0];

  return (
    <>
      <section className="hero">
        <p className="eyebrow">Ledger</p>
        <h1>{featured ? <Link to={`/post/${featured.slug}`}>{featured.title}</Link> : "Essays that ship"}</h1>
        <p className="lede">
          {featured?.excerpt || "Magazine-style writing powered by the Django Ledger API."}
        </p>
      </section>

      <div className="grid-wrap">
        <div>
          {err ? <p className="empty">{err}</p> : null}
          <div className="grid">
            {posts.map((post) => (
              <PostCard key={post.id} post={post} />
            ))}
          </div>
          {!err && !posts.length ? <p className="empty">No posts yet. Run seed_blog on the API.</p> : null}
        </div>
        <aside>
          <h3>Trending</h3>
          <ol className="trending">
            {trending.slice(0, 5).map((post) => (
              <li key={post.id}>
                <Link to={`/post/${post.slug}`}>{post.title}</Link>
                <span>{post.view_count} views</span>
              </li>
            ))}
          </ol>

          <h3>Topics</h3>
          <div className="tag-cloud">
            <Link to="/">All</Link>
            {cats.map((c) => (
              <Link key={c.id} to={`/?category=${c.slug}`}>
                {c.name}
              </Link>
            ))}
          </div>
        </aside>
      </div>
    </>
  );
}
