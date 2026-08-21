import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { blogApi } from "../api/blog";

export default function SeriesDetail() {
  const { slug } = useParams();
  const [series, setSeries] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    blogApi
      .series(slug)
      .then(setSeries)
      .catch((e) => setErr(e.message));
  }, [slug]);

  if (err) return <p className="empty">{err}</p>;
  if (!series) return <p className="empty">Loading…</p>;

  return (
    <>
      <section className="hero compact">
        <p className="eyebrow">Series</p>
        <h1>{series.title}</h1>
        <p className="lede">{series.description}</p>
        <p className="meta">
          by <Link to={`/author/${series.author?.username}`}>{series.author?.username}</Link>
        </p>
      </section>
      <ol className="series-parts">
        {(series.memberships || []).map((m) => (
          <li key={m.id}>
            <span className="meta">Part {m.position}</span>{" "}
            <Link to={`/post/${m.post_slug}`}>{m.post_title}</Link>
          </li>
        ))}
      </ol>
    </>
  );
}
