import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { blogApi } from "../api/blog";

export default function NewsletterConfirm() {
  const { token } = useParams();
  const [status, setStatus] = useState("working");
  const [detail, setDetail] = useState("");

  useEffect(() => {
    blogApi
      .newsletterConfirm(token)
      .then((d) => {
        setStatus("ok");
        setDetail(d.email || "You’re subscribed.");
      })
      .catch((e) => {
        setStatus("err");
        setDetail(e.message || "Invalid or expired link.");
      });
  }, [token]);

  return (
    <section className="hero compact">
      <h1>Newsletter</h1>
      {status === "working" ? <p className="lede">Confirming…</p> : null}
      {status === "ok" ? (
        <p className="lede">Confirmed for {detail}. Welcome to Ledger.</p>
      ) : null}
      {status === "err" ? <p className="empty">{detail}</p> : null}
      <p>
        <Link className="btn" to="/">
          Home
        </Link>
      </p>
    </section>
  );
}
