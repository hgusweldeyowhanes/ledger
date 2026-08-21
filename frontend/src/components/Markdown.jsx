import { marked } from "marked";

marked.setOptions({ breaks: true, gfm: true });

export default function Markdown({ source }) {
  const html = marked.parse(source || "");
  return <div className="prose" dangerouslySetInnerHTML={{ __html: html }} />;
}
