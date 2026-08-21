import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { blogApi } from "../api/blog";

export default function SeriesList() {
  const [items, setItems] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    blogApi
      .seriesList()
      .then((d) => setItems(d.results || d || []))
      .catch((e) => setErr(e.message));
  }, []);

  return (
    <>
      <section className="hero compact">
        <h1>Series</h1>
        <p className="lede">Multi-part essays, collected.</p>
      </section>
      {err ? <p className="empty">{err}</p> : null}
      <div className="grid full">
        {items.map((s) => (
          <article className="card" key={s.id}>
            <div className="card-body">
              <p className="meta">
                {s.author?.username} · {s.post_count ?? s.memberships?.length ?? 0} parts
              </p>
              <h2>
                <Link to={`/series/${s.slug}`}>{s.title}</Link>
              </h2>
              <p>{s.description}</p>
            </div>
          </article>
        ))}
      </div>
    </>
  );
}
