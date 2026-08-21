import { Link } from "react-router-dom";

export default function PostCard({ post }) {
  return (
    <article className="card">
      {post.cover_image ? <img src={post.cover_image} alt="" /> : null}
      <div className="card-body">
        <div className="cats">
          {(post.categories || []).map((c) => (
            <Link key={c.id} to={`/?category=${c.slug}`}>
              {c.name}
            </Link>
          ))}
        </div>
        <h2>
          <Link to={`/post/${post.slug}`}>{post.title}</Link>
        </h2>
        <p>{post.excerpt}</p>
        <p className="meta">
          <Link to={`/author/${post.author?.username}`}>{post.author?.username}</Link>
          {" · "}
          {post.reading_time} min · {post.likes_count ?? 0} likes
        </p>
      </div>
    </article>
  );
}
