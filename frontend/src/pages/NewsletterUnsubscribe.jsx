import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { blogApi } from "../api/blog";

export default function NewsletterUnsubscribe() {
  const { token } = useParams();
  const [status, setStatus] = useState("working");
  const [detail, setDetail] = useState("");

  useEffect(() => {
    blogApi
      .newsletterUnsubscribe(token)
      .then((d) => {
        setStatus("ok");
        setDetail(d.email || "Unsubscribed.");
      })
      .catch((e) => {
        setStatus("err");
        setDetail(e.message || "Invalid link.");
      });
  }, [token]);

  return (
    <section className="hero compact">
      <h1>Unsubscribe</h1>
      {status === "working" ? <p className="lede">Updating…</p> : null}
      {status === "ok" ? <p className="lede">Unsubscribed {detail}.</p> : null}
      {status === "err" ? <p className="empty">{detail}</p> : null}
      <p>
        <Link className="btn" to="/">
          Home
        </Link>
      </p>
    </section>
  );
}
