import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login, isAuth } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");

  if (isAuth) return <Navigate to="/" replace />;

  const onSubmit = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      await login(username, password);
      navigate("/");
    } catch (e2) {
      setErr(e2.data?.detail || e2.message || "Login failed");
    }
  };

  return (
    <section className="hero compact">
      <h1>Log in</h1>
      <form className="stack" onSubmit={onSubmit}>
        <label>Username</label>
        <input value={username} onChange={(e) => setUsername(e.target.value)} required />
        <label>Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {err ? <p className="empty">{err}</p> : null}
        <button className="btn" type="submit">
          Enter Ledger
        </button>
      </form>
      <p className="meta">
        No account? <Link to="/register">Join</Link>
      </p>
    </section>
  );
}
