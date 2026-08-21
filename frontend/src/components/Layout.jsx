import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { blogApi } from "../api/blog";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

export default function Layout() {
  const { user, isAuth, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [email, setEmail] = useState("");
  const [flash, setFlash] = useState("");

  const onSearch = (e) => {
    e.preventDefault();
    navigate(q.trim() ? `/search?q=${encodeURIComponent(q.trim())}` : "/");
  };

  const onNewsletter = async (e) => {
    e.preventDefault();
    try {
      await blogApi.newsletter(email);
      setFlash("Check your email to confirm the subscription.");
      setEmail("");
    } catch (err) {
      setFlash(err.message || "Could not subscribe.");
    }
  };

  return (
    <>
      <header className="site-header">
        <Link className="logo" to="/">
          Ledger
        </Link>
        <nav className="nav">
          <NavLink to="/series">Series</NavLink>
          {isAuth ? <NavLink to="/following">Following</NavLink> : null}
        </nav>
        <form className="search" onSubmit={onSearch}>
          <input
            type="search"
            placeholder="Search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </form>
        <div className="auth">
          <button type="button" className="theme-toggle" onClick={toggle}>
            {theme === "light" ? "Dark" : "Light"}
          </button>
          {isAuth ? (
            <>
              <NavLink to="/notifications">Alerts</NavLink>
              <NavLink to="/write">Write</NavLink>
              <NavLink to="/studio">Studio</NavLink>
              <button type="button" className="theme-toggle" onClick={logout}>
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login">Log in</NavLink>
              <Link className="btn" to="/register">
                Join
              </Link>
            </>
          )}
        </div>
      </header>

      {flash ? (
        <div className="flash">
          <p>{flash}</p>
        </div>
      ) : null}

      <main>
        <Outlet context={{ user }} />
      </main>

      <footer className="site-footer">
        <div className="footer-grid">
          <p>
            Ledger · essays for people who ship.
            {user ? ` Signed in as ${user.username}.` : null}
          </p>
          <form className="newsletter" onSubmit={onNewsletter}>
            <label htmlFor="nl-email">Newsletter</label>
            <input
              id="nl-email"
              type="email"
              required
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <button className="btn" type="submit">
              Subscribe
            </button>
          </form>
        </div>
      </footer>
    </>
  );
}
