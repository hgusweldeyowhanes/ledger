import { useEffect, useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { blogApi } from "../api/blog";
import { useAuth } from "../context/AuthContext";

const empty = {
  title: "",
  excerpt: "",
  content: "",
  status: "draft",
  featured: false,
  allow_comments: true,
  tag_names: "",
  series_id: "",
  series_position: 1,
};

export default function Write() {
  const { slug } = useParams();
  const { isAuth, loading, user } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(empty);
  const [seriesList, setSeriesList] = useState([]);
  const [coverFile, setCoverFile] = useState(null);
  const [coverPreview, setCoverPreview] = useState("");
  const [err, setErr] = useState("");
  const [saving, setSaving] = useState(false);
  const editing = Boolean(slug);

  useEffect(() => {
    if (!isAuth) return;
    blogApi
      .seriesList()
      .then((d) => {
        const all = d.results || d || [];
        setSeriesList(
          all.filter((s) => s.author?.username === user?.username || s.author?.id === user?.id),
        );
      })
      .catch(() => {});
    if (slug) {
      blogApi
        .post(slug)
        .then((p) => {
          setForm({
            title: p.title,
            excerpt: p.excerpt || "",
            content: p.content || "",
            status: p.status,
            featured: p.featured,
            allow_comments: p.allow_comments,
            tag_names: (p.tags || []).map((t) => t.name).join(", "),
            series_id: p.series?.id || "",
            series_position: p.series?.position || 1,
          });
          if (p.cover_image) setCoverPreview(p.cover_image);
        })
        .catch((e) => setErr(e.message));
    }
  }, [isAuth, slug, user]);

  if (loading) return <p className="empty">Loading…</p>;
  if (!isAuth) return <Navigate to="/login" replace />;

  const set = (k, cast) => (e) => {
    const v = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [k]: cast ? cast(v) : v }));
  };

  const onCover = (e) => {
    const file = e.target.files?.[0];
    setCoverFile(file || null);
    if (file) setCoverPreview(URL.createObjectURL(file));
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setErr("");
    setSaving(true);
    const payload = {
      title: form.title,
      excerpt: form.excerpt,
      content: form.content,
      status: form.status,
      featured: form.featured,
      allow_comments: form.allow_comments,
      tag_names: form.tag_names
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
    };
    if (form.series_id) {
      payload.series_id = Number(form.series_id);
      payload.series_position = Number(form.series_position) || 1;
    } else if (editing) {
      payload.series_id = null;
    }
    try {
      let saved = editing
        ? await blogApi.updatePost(slug, payload)
        : await blogApi.createPost(payload);
      if (coverFile) {
        saved = await blogApi.uploadCover(saved.slug, coverFile);
      }
      if (form.status === "published" && saved.status !== "published") {
        saved = await blogApi.publish(saved.slug);
      }
      navigate(saved.status === "published" ? `/post/${saved.slug}` : "/studio");
    } catch (e2) {
      setErr(e2.message || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const mineSeries = seriesList.filter(Boolean);

  return (
    <>
      <section className="hero compact">
        <h1>{editing ? "Edit post" : "New essay"}</h1>
      </section>
      <form className="stack" onSubmit={onSubmit}>
        <label>Title</label>
        <input value={form.title} onChange={set("title")} required />
        <label>Excerpt</label>
        <textarea rows={2} value={form.excerpt} onChange={set("excerpt")} />
        <label>Cover image</label>
        <input type="file" accept="image/*" onChange={onCover} />
        {coverPreview ? (
          <img className="cover-preview" src={coverPreview} alt="Cover preview" />
        ) : null}
        <label>Content (Markdown)</label>
        <textarea rows={16} value={form.content} onChange={set("content")} required />
        <label>Tags (comma-separated)</label>
        <input value={form.tag_names} onChange={set("tag_names")} placeholder="django, ethiopia" />
        <label>Status</label>
        <select value={form.status} onChange={set("status")}>
          <option value="draft">Draft</option>
          <option value="published">Published</option>
          <option value="archived">Archived</option>
        </select>
        <label>Series</label>
        <select value={form.series_id} onChange={set("series_id")}>
          <option value="">No series</option>
          {mineSeries.map((s) => (
            <option key={s.id} value={s.id}>
              {s.title}
            </option>
          ))}
        </select>
        <label>Series position</label>
        <input
          type="number"
          min={1}
          value={form.series_position}
          onChange={set("series_position", Number)}
        />
        <label>
          <input type="checkbox" checked={form.featured} onChange={set("featured")} /> Featured
        </label>
        <label>
          <input type="checkbox" checked={form.allow_comments} onChange={set("allow_comments")} />{" "}
          Allow comments
        </label>
        {err ? <p className="empty">{err}</p> : null}
        <button className="btn" type="submit" disabled={saving}>
          {saving ? "Saving…" : "Save"}
        </button>
      </form>
    </>
  );
}
