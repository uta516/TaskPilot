import type { RelaxSuggestion } from "../types";

interface Props {
  issues: string[];
  suggestions: RelaxSuggestion[];
}

export default function RelaxSuggestions({ issues, suggestions }: Props) {
  return (
    <div className="card warn-card">
      <h2>スケジュールを収めることができませんでした</h2>
      {issues.length > 0 && (
        <ul className="issue-list">
          {issues.map((issue, i) => (
            <li key={i}>{issue}</li>
          ))}
        </ul>
      )}
      {suggestions.length > 0 && (
        <>
          <h3>緩和の提案</h3>
          <ul className="suggestion-list">
            {suggestions.map((s, i) => (
              <li key={i} className="suggestion-item">
                {s.description}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
