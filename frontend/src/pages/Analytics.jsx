import { useEffect, useMemo, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { blogApi } from "../api/blog";
import { useAuth } from "../context/AuthContext";

export default function Analytics() {
  const { isAuth, loading: authLoading } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sortKey, setSortKey] = useState("view_count");
  const [sortDir, setSortDir] = useState("desc");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedBar, setSelectedBar] = useState(null);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await blogApi.analytics();
      setData(res);
    } catch (err) {
      setError(err.message || "Could not load author analytics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuth) {
      fetchAnalytics();
    }
  }, [isAuth]);

  const sortedPosts = useMemo(() => {
    if (!data?.posts_breakdown) return [];
    let list = [...data.posts_breakdown];
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      list = list.filter((p) => p.title.toLowerCase().includes(term));
    }
    list.sort((a, b) => {
      let valA = a[sortKey];
      let valB = b[sortKey];
      if (typeof valA === "string") {
        return sortDir === "asc"
          ? valA.localeCompare(valB)
          : valB.localeCompare(valA);
      }
      valA = Number(valA) || 0;
      valB = Number(valB) || 0;
      return sortDir === "asc" ? valA - valB : valB - valA;
    });
    return list;
  }, [data, sortKey, sortDir, searchTerm]);

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  if (authLoading) return <p className="empty">Authenticating…</p>;
  if (!isAuth) return <Navigate to="/login" replace />;

  const totals = data?.totals || {};
  const topPosts = data?.top_posts || [];
  const categories = data?.category_distribution || [];
  const monthlyTrends = data?.monthly_trends || [];
  const recentActivity = data?.recent_activity || [];

  const formatReadTime = (minutes) => {
    if (!minutes || minutes <= 0) return "0 min";
    if (minutes < 60) return `${minutes} min`;
    const hrs = Math.floor(minutes / 60);
    const remainingMins = minutes % 60;
    return remainingMins > 0 ? `${hrs}h ${remainingMins}m` : `${hrs} hrs`;
  };

  const maxTopPostViews = Math.max(...topPosts.map((p) => p.view_count || 0), 1);
  const maxMonthlyViews = Math.max(...monthlyTrends.map((m) => m.views || 0), 1);

  return (
    <div className="analytics-page">
      <section className="hero compact">
        <div className="analytics-header-row">
          <div>
            <span className="eyebrow">Studio Intelligence</span>
            <h1>Author Analytics</h1>
            <p className="lede">
              Readership metrics, engagement resonance, and audience trends for your work.
            </p>
          </div>
          <div className="analytics-actions">
            <button
              type="button"
              className="btn ghost"
              onClick={fetchAnalytics}
              disabled={loading}
              title="Refresh statistics"
            >
              {loading ? "Refreshing…" : "↻ Refresh"}
            </button>
            <Link className="btn ghost" to="/studio">
              Studio
            </Link>
            <Link className="btn" to="/write">
              + New Post
            </Link>
          </div>
        </div>
      </section>

      {error ? <p className="flash error-flash">{error}</p> : null}

      {/* KPI Overview Cards */}
      <section className="analytics-kpi-grid">
        <div className="kpi-card">
          <div className="kpi-icon">👁️</div>
          <div className="kpi-content">
            <span className="kpi-label">Total Views</span>
            <div className="kpi-value">{totals.views?.toLocaleString() || 0}</div>
            <span className="kpi-subtext">Across {totals.published_posts || 0} published stories</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon">⏳</div>
          <div className="kpi-content">
            <span className="kpi-label">Read Time Delivered</span>
            <div className="kpi-value">{formatReadTime(totals.total_read_time_minutes)}</div>
            <span className="kpi-subtext">Avg {totals.avg_reading_time || 0} min per read</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon">❤️</div>
          <div className="kpi-content">
            <span className="kpi-label">Total Likes</span>
            <div className="kpi-value">{totals.likes?.toLocaleString() || 0}</div>
            <span className="kpi-subtext">Reader appreciations</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon">🔖</div>
          <div className="kpi-content">
            <span className="kpi-label">Bookmarks</span>
            <div className="kpi-value">{totals.bookmarks?.toLocaleString() || 0}</div>
            <span className="kpi-subtext">Saved to reader libraries</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon">💬</div>
          <div className="kpi-content">
            <span className="kpi-label">Discussions</span>
            <div className="kpi-value">{totals.comments?.toLocaleString() || 0}</div>
            <span className="kpi-subtext">Approved comments</span>
          </div>
        </div>

        <div className="kpi-card highlight">
          <div className="kpi-icon">👥</div>
          <div className="kpi-content">
            <span className="kpi-label">Followers</span>
            <div className="kpi-value">{totals.followers?.toLocaleString() || 0}</div>
            <span className="kpi-subtext">
              Resonance Rate: <strong>{totals.engagement_rate || 0}%</strong>
            </span>
          </div>
        </div>
      </section>

      {/* Visual Charts Section */}
      <div className="analytics-charts-grid">
        {/* Top Posts Performance Chart */}
        <section className="analytics-panel chart-panel">
          <div className="panel-header">
            <div>
              <h3>Top Performing Stories</h3>
              <p className="panel-sub">Comparing article reach and total reader interactions</p>
            </div>
            <span className="badge">{topPosts.length} Leading</span>
          </div>

          {topPosts.length === 0 ? (
            <p className="empty">Publish stories to populate performance comparisons.</p>
          ) : (
            <div className="bar-chart-container">
              {topPosts.map((post, idx) => {
                const viewPct = Math.round((post.view_count / maxTopPostViews) * 100);
                const interactions =
                  (post.likes_count || 0) +
                  (post.bookmarks_count || 0) +
                  (post.comments_count || 0);

                return (
                  <div
                    key={post.id}
                    className={`chart-bar-row ${selectedBar === post.id ? "selected" : ""}`}
                    onClick={() => setSelectedBar(selectedBar === post.id ? null : post.id)}
                  >
                    <div className="bar-meta">
                      <span className="bar-rank">#{idx + 1}</span>
                      <Link to={`/post/${post.slug}`} className="bar-title" title={post.title}>
                        {post.title}
                      </Link>
                      <span className="bar-stat-label">
                        <strong>{post.view_count}</strong> views · {interactions} reactions
                      </span>
                    </div>

                    <div className="bar-track">
                      <div
                        className="bar-fill-views"
                        style={{ width: `${Math.max(viewPct, 4)}%` }}
                        title={`${post.view_count} views`}
                      />
                    </div>

                    {selectedBar === post.id && (
                      <div className="bar-detail-popover">
                        <span>❤️ {post.likes_count} likes</span>
                        <span>🔖 {post.bookmarks_count} saves</span>
                        <span>💬 {post.comments_count} comments</span>
                        <span>⚡ {post.engagement_rate}% engagement</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Category Readership Distribution */}
        <section className="analytics-panel">
          <div className="panel-header">
            <div>
              <h3>Topics & Categories</h3>
              <p className="panel-sub">Where your readership spends their time</p>
            </div>
          </div>

          {categories.length === 0 ? (
            <p className="empty">Tag your posts with categories to see genre analytics.</p>
          ) : (
            <div className="categories-analytics">
              {/* Proportional Segment Bar */}
              <div className="multi-progress-bar">
                {categories.map((cat) => (
                  <div
                    key={cat.id}
                    className="progress-segment"
                    style={{
                      width: `${Math.max(cat.percentage, 2)}%`,
                      backgroundColor: cat.color || "var(--gold)",
                    }}
                    title={`${cat.name}: ${cat.percentage}% of views (${cat.total_views} views)`}
                  />
                ))}
              </div>

              <ul className="category-stat-list">
                {categories.map((cat) => (
                  <li key={cat.id} className="category-stat-item">
                    <span
                      className="category-color-dot"
                      style={{ backgroundColor: cat.color || "var(--gold)" }}
                    />
                    <span className="category-stat-name">{cat.name}</span>
                    <span className="category-stat-posts">{cat.posts_count} articles</span>
                    <span className="category-stat-views">
                      <strong>{cat.total_views}</strong> views ({cat.percentage}%)
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </div>

      {/* Monthly Trends & Recent Reader Interactions */}
      <div className="analytics-charts-grid secondary">
        {/* Monthly Activity / Velocity */}
        <section className="analytics-panel">
          <div className="panel-header">
            <div>
              <h3>Publishing Velocity & Views</h3>
              <p className="panel-sub">Recent 6-month monthly traffic profile</p>
            </div>
          </div>

          <div className="monthly-chart-wrap">
            {monthlyTrends.map((m) => {
              const heightPct =
                maxMonthlyViews > 0 ? Math.round((m.views / maxMonthlyViews) * 100) : 0;
              return (
                <div key={m.label} className="monthly-col">
                  <div className="monthly-bar-track">
                    <div
                      className="monthly-bar-fill"
                      style={{ height: `${Math.max(heightPct, 6)}%` }}
                      title={`${m.month_name}: ${m.views} views, ${m.posts_count} posts`}
                    >
                      <span className="monthly-val">{m.views}</span>
                    </div>
                  </div>
                  <span className="monthly-label">{m.month_name.split(" ")[0]}</span>
                  <span className="monthly-sub">{m.posts_count} posts</span>
                </div>
              );
            })}
          </div>
        </section>

        {/* Recent Reader Engagement Activity Feed */}
        <section className="analytics-panel">
          <div className="panel-header">
            <div>
              <h3>Recent Reader Activity</h3>
              <p className="panel-sub">Real-time interactions on your published essays</p>
            </div>
          </div>

          {recentActivity.length === 0 ? (
            <p className="empty">No reader interactions recorded yet.</p>
          ) : (
            <ul className="recent-activity-list">
              {recentActivity.map((act) => {
                const timeStr = act.created_at
                  ? new Date(act.created_at).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                    })
                  : "";

                let icon = "⚡";
                if (act.verb === "liked") icon = "❤️";
                else if (act.verb === "commented") icon = "💬";
                else if (act.verb === "followed") icon = "👥";
                else if (act.verb === "comment_approved") icon = "✓";

                return (
                  <li key={act.id} className="activity-item">
                    <span className="activity-icon">{icon}</span>
                    <div className="activity-details">
                      <p>
                        <strong>{act.actor_username}</strong> {act.verb}{" "}
                        {act.post_title && act.post_slug ? (
                          <Link to={`/post/${act.post_slug}`}>{act.post_title}</Link>
                        ) : null}
                      </p>
                      <time>{timeStr}</time>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </div>

      {/* Catalog Performance Breakdown Table */}
      <section className="analytics-panel full-width">
        <div className="panel-header table-header">
          <div>
            <h3>All Stories Performance</h3>
            <p className="panel-sub">
              Detailed statistics and engagement breakdown across your full catalogue
            </p>
          </div>
          <div className="table-search-box">
            <input
              type="search"
              placeholder="Filter by title…"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>

        <div className="table-responsive">
          <table className="table analytics-table">
            <thead>
              <tr>
                <th onClick={() => handleSort("title")} className="sortable">
                  Article Title {sortKey === "title" ? (sortDir === "asc" ? "▲" : "▼") : ""}
                </th>
                <th onClick={() => handleSort("status")} className="sortable">
                  Status {sortKey === "status" ? (sortDir === "asc" ? "▲" : "▼") : ""}
                </th>
                <th onClick={() => handleSort("view_count")} className="sortable numeric">
                  Views {sortKey === "view_count" ? (sortDir === "asc" ? "▲" : "▼") : ""}
                </th>
                <th onClick={() => handleSort("likes_count")} className="sortable numeric">
                  Likes {sortKey === "likes_count" ? (sortDir === "asc" ? "▲" : "▼") : ""}
                </th>
                <th onClick={() => handleSort("bookmarks_count")} className="sortable numeric">
                  Saves {sortKey === "bookmarks_count" ? (sortDir === "asc" ? "▲" : "▼") : ""}
                </th>
                <th onClick={() => handleSort("comments_count")} className="sortable numeric">
                  Comments {sortKey === "comments_count" ? (sortDir === "asc" ? "▲" : "▼") : ""}
                </th>
                <th onClick={() => handleSort("reading_time")} className="sortable numeric">
                  Read Time {sortKey === "reading_time" ? (sortDir === "asc" ? "▲" : "▼") : ""}
                </th>
                <th onClick={() => handleSort("engagement_rate")} className="sortable numeric">
                  Engagement {sortKey === "engagement_rate" ? (sortDir === "asc" ? "▲" : "▼") : ""}
                </th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedPosts.map((post) => (
                <tr key={post.id}>
                  <td>
                    <Link to={`/post/${post.slug}`} className="table-post-link">
                      {post.title}
                    </Link>
                  </td>
                  <td>
                    <span className={`status-pill ${post.status}`}>{post.status}</span>
                  </td>
                  <td className="numeric font-mono"><strong>{post.view_count}</strong></td>
                  <td className="numeric font-mono">{post.likes_count}</td>
                  <td className="numeric font-mono">{post.bookmarks_count}</td>
                  <td className="numeric font-mono">{post.comments_count}</td>
                  <td className="numeric font-mono">{post.reading_time}m</td>
                  <td className="numeric font-mono">
                    <span
                      className={`rate-badge ${
                        post.engagement_rate > 10 ? "high" : post.engagement_rate > 3 ? "medium" : "normal"
                      }`}
                    >
                      {post.engagement_rate}%
                    </span>
                  </td>
                  <td>
                    <Link to={`/write/${post.slug}`} className="btn-table-edit">
                      Edit
                    </Link>
                  </td>
                </tr>
              ))}
              {sortedPosts.length === 0 && (
                <tr>
                  <td colSpan={9} className="empty">
                    {searchTerm ? "No matching posts found." : "No posts in catalog."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
