import { useState } from "react";

export default function Share({ url, title }) {
  const [copied, setCopied] = useState(false);
  const encoded = encodeURIComponent(url);
  const text = encodeURIComponent(title || "");

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      window.prompt("Copy link", url);
    }
  };

  return (
    <div className="share">
      <p className="eyebrow">Share</p>
      <div className="share-actions">
        <button type="button" className="btn ghost" onClick={copy}>
          {copied ? "Copied" : "Copy link"}
        </button>
        <a
          className="btn ghost"
          target="_blank"
          rel="noreferrer"
          href={`https://twitter.com/intent/tweet?url=${encoded}&text=${text}`}
        >
          X
        </a>
        <a
          className="btn ghost"
          target="_blank"
          rel="noreferrer"
          href={`https://www.linkedin.com/sharing/share-offsite/?url=${encoded}`}
        >
          LinkedIn
        </a>
      </div>
    </div>
  );
}
