import { api } from "./client";

export const blogApi = {
  posts: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return api(`/api/posts/${q ? `?${q}` : ""}`, { auth: false });
  },
  post: (slug) => api(`/api/posts/${slug}/`, { auth: true }),
  createPost: (body) => api("/api/posts/", { method: "POST", body }),
  updatePost: (slug, body) => api(`/api/posts/${slug}/`, { method: "PATCH", body }),
  uploadCover: (slug, file) => {
    const fd = new FormData();
    fd.append("cover_image", file);
    return api(`/api/posts/${slug}/`, { method: "PATCH", formData: fd });
  },
  publish: (slug) => api(`/api/posts/${slug}/publish/`, { method: "POST" }),
  like: (slug) => api(`/api/posts/${slug}/like/`, { method: "POST" }),
  bookmark: (slug) => api(`/api/posts/${slug}/bookmark/`, { method: "POST" }),
  mine: () => api("/api/posts/mine/"),
  saved: () => api("/api/posts/saved/"),
  followingFeed: () => api("/api/feed/following/"),
  trending: () => api("/api/posts/trending/", { auth: false }),
  popular: () => api("/api/posts/popular/", { auth: false }),
  categories: () => api("/api/categories/", { auth: false }),
  seriesList: () => api("/api/series/", { auth: false }),
  series: (slug) => api(`/api/series/${slug}/`, { auth: false }),
  createSeries: (body) => api("/api/series/", { method: "POST", body }),
  follow: (username) => api(`/api/authors/${username}/follow/`, { method: "POST" }),
  comments: (postId) => api(`/api/comments/?post=${postId}`, { auth: false }),
  addComment: (body) => api("/api/comments/", { method: "POST", body }),
  pendingComments: () => api("/api/comments/pending/"),
  approveComment: (id) => api(`/api/comments/${id}/approve/`, { method: "POST" }),
  rejectComment: (id) => api(`/api/comments/${id}/reject/`, { method: "POST" }),
  notifications: () => api("/api/notifications/"),
  markNotificationsRead: () => api("/api/notifications/mark_read/", { method: "POST" }),
  newsletter: (email) =>
    api("/api/newsletter/subscribe/", { method: "POST", body: { email }, auth: false }),
  newsletterConfirm: (token) =>
    api(`/api/newsletter/confirm/${token}/`, { method: "POST", auth: false }),
  newsletterUnsubscribe: (token) =>
    api(`/api/newsletter/unsubscribe/${token}/`, { method: "POST", auth: false }),
  me: () => api("/api/me/"),
  register: (body) => api("/api/register/", { method: "POST", body, auth: false }),
  login: (body) => api("/api/token/", { method: "POST", body, auth: false }),
};
