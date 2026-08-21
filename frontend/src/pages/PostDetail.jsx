import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { blogApi } from "../api/blog";
import Markdown from "../components/Markdown";
import Share from "../components/Share";
import { useAuth } from "../context/AuthContext";

export default function PostDetail() {
  const { slug } = useParams();
  const { user, isAuth } = useAuth();
  const [post, setPost] = useState(null);
  const [body, setBody] = useState("");
  const [replyTo, setReplyTo] = useState(null);
  const [replyBody, setReplyBody] = useState("");
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = () =>
    blogApi
      .post(slug)
      .then(setPost)
      .catch((e) => setErr(e.message));

  useEffect(() => {
    load();
  }, [slug]);

  if (err) return <p className="empty">{err}</p>;
  if (!post) return <p className="empty">Loading…</p>;

  const absoluteUrl = `${window.location.origin}/post/${post.slug}`;
  const isAuthor = user && post.author?.id === user.id;

  const toggleLike = async () => {
    const res = await blogApi.like(post.slug);
    setPost((p) => ({ ...p, is_liked: res.liked, likes_count: res.likes_count }));
  };

  const toggleBookmark = async () => {
    const res = await blogApi.bookmark(post.slug);
    setPost((p) => ({ ...p, is_bookmarked: res.bookmarked }));
  };

  const follow = async () => {
    await blogApi.follow(post.author.username);
    setMsg(`Updated follow for ${post.author.username}`);
  };

  const submitComment = async (e) => {
    e.preventDefault();
    try {
      const comment = await blogApi.addComment({ post: post.id, body });
      setBody("");
      setMsg(comment.is_approved ? "Comment posted." : "Comment submitted for review.");
      if (comment.is_approved) await load();
    } catch (e2) {
      setMsg(e2.message);
    }
  };

  const submitReply = async (e, parentId) => {
    e.preventDefault();
    try {
      const comment = await blogApi.addComment({
        post: post.id,
        body: replyBody,
        parent: parentId,
      });
      setReplyBody("");
      setReplyTo(null);
      setMsg(comment.is_approved ? "Reply posted." : "Reply submitted for review.");
      if (comment.is_approved) await load();
    } catch (e2) {
      setMsg(e2.message);
    }
  };

  return (
    <article className="article">
      {post.series ? (
        <aside className="series-nav">
          <p className="eyebrow">Series</p>
          <h3>
            <Link to={`/series/${post.series.slug}`}>{post.series.title}</Link>
          </h3>
          <p className="meta">Part {post.series.position}</p>
        </aside>
      ) : null}

      <header>
        <div className="cats">
          {(post.categories || []).map((c) => (
            <Link key={c.id} to={`/?category=${c.slug}`}>
              {c.name}
            </Link>
          ))}
        </div>
        <h1>{post.title}</h1>
        <p className="lede">{post.excerpt}</p>
        <p className="meta">
          <Link to={`/author/${post.author.username}`}>{post.author.username}</Link>
          {" · "}
          {new Date(post.published_at).toLocaleDateString()} · {post.reading_time} min ·{" "}
          {post.view_count} views
        </p>
        {isAuth && !isAuthor ? (
          <button type="button" className="btn ghost" onClick={follow}>
            Follow {post.author.username}
          </button>
        ) : null}
        {isAuthor ? (
          <p>
            <Link className="btn ghost" to={`/write/${post.slug}`}>
              Edit
            </Link>
          </p>
        ) : null}
      </header>

      {post.cover_image ? <img className="cover" src={post.cover_image} alt="" /> : null}
      <Markdown source={post.content} />

      <div className="tag-cloud">
        {(post.tags || []).map((t) => (
          <span key={t.id}>#{t.name}</span>
        ))}
      </div>

      <div className="actions">
        {isAuth ? (
          <>
            <button type="button" onClick={toggleLike}>
              {post.is_liked ? "Unlike" : "Like"} · {post.likes_count ?? 0}
            </button>
            <button type="button" onClick={toggleBookmark}>
              {post.is_bookmarked ? "Saved" : "Save"}
            </button>
          </>
        ) : (
          <p className="meta">
            <Link to="/login">Log in</Link> to like or comment.
          </p>
        )}
      </div>

      <Share url={absoluteUrl} title={post.title} />
      {msg ? <p className="flash">{msg}</p> : null}

      {(post.related || []).length ? (
        <section className="related">
          <h2>Related</h2>
          <ul>
            {post.related.map((r) => (
              <li key={r.id}>
                <Link to={`/post/${r.slug}`}>{r.title}</Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="comments" id="comments">
        <h2>Comments</h2>
        {(post.comments || []).map((c) => (
          <div className="comment" key={c.id}>
            <strong>{c.author?.username}</strong>
            <time> {new Date(c.created_at).toLocaleString()}</time>
            <p>{c.body}</p>
            {(c.replies || []).map((r) => (
              <div className="comment reply" key={r.id}>
                <strong>{r.author?.username}</strong>
                <time> {new Date(r.created_at).toLocaleString()}</time>
                <p>{r.body}</p>
              </div>
            ))}
            {isAuth && post.allow_comments ? (
              replyTo === c.id ? (
                <form className="reply-form" onSubmit={(e) => submitReply(e, c.id)}>
                  <textarea
                    rows={2}
                    value={replyBody}
                    onChange={(e) => setReplyBody(e.target.value)}
                    placeholder={`Reply to ${c.author?.username}…`}
                    required
                    autoFocus
                  />
                  <div className="inline-forms">
                    <button className="btn" type="submit">
                      Reply
                    </button>
                    <button
                      type="button"
                      className="btn ghost"
                      onClick={() => {
                        setReplyTo(null);
                        setReplyBody("");
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              ) : (
                <button type="button" className="btn ghost" onClick={() => setReplyTo(c.id)}>
                  Reply
                </button>
              )
            ) : null}
          </div>
        ))}
        {!post.comments?.length ? <p className="empty">Be the first to comment.</p> : null}
        {isAuth && post.allow_comments ? (
          <form className="comment-form" onSubmit={submitComment}>
            <textarea
              rows={3}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Write a comment…"
              required
            />
            <button className="btn" type="submit">
              Post comment
            </button>
          </form>
        ) : null}
      </section>
    </article>
  );
}
