import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const { register, isAuth } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    password2: "",
    first_name: "",
    last_name: "",
  });
  const [err, setErr] = useState("");

  if (isAuth) return <Navigate to="/" replace />;

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      await register(form);
      navigate("/");
    } catch (e2) {
      const d = e2.data;
      setErr(
        (typeof d === "object" && d && Object.values(d).flat().join(" ")) ||
          e2.message ||
          "Registration failed",
      );
    }
  };

  return (
    <section className="hero compact">
      <h1>Join Ledger</h1>
      <form className="stack" onSubmit={onSubmit}>
        <label>Username</label>
        <input value={form.username} onChange={set("username")} required />
        <label>Email</label>
        <input type="email" value={form.email} onChange={set("email")} required />
        <label>First name</label>
        <input value={form.first_name} onChange={set("first_name")} />
        <label>Password</label>
        <input type="password" value={form.password} onChange={set("password")} required />
        <label>Confirm password</label>
        <input type="password" value={form.password2} onChange={set("password2")} required />
        {err ? <p className="empty">{err}</p> : null}
        <button className="btn" type="submit">
          Create account
        </button>
      </form>
      <p className="meta">
        Already here? <Link to="/login">Log in</Link>
      </p>
    </section>
  );
}
