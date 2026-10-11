import ReactMarkdown from "react-markdown";

interface Props {
  title: string;
  explanation: string | null;
}

export default function ExplanationCard({ title, explanation }: Props) {
  if (!explanation) return null;
  return (
    <div className="card">
      <h2>{title}</h2>
      <div className="markdown">
        <ReactMarkdown>{explanation}</ReactMarkdown>
      </div>
    </div>
  );
}
