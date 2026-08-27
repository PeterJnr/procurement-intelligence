import { ArrowUp, LoaderCircle } from "lucide-react";
import { useEffect, useRef } from "react";

interface Props {
  value: string;
  loading: boolean;
  suggestions: string[];
  onChange: (value: string) => void;
  onSubmit: () => void;
}

export function Composer({ value, loading, suggestions, onChange, onSubmit }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    ref.current.style.height = "0px";
    ref.current.style.height = `${Math.min(ref.current.scrollHeight, 160)}px`;
  }, [value]);

  return (
    <div className="composer-wrap">
      {!loading && suggestions.length > 0 && (
        <div className="prompt-suggestions" aria-label="Suggested prompts">
          <span>Try asking</span>
          <div>
            {suggestions.map((suggestion) => (
              <button key={suggestion} type="button" onClick={() => onChange(suggestion)}>{suggestion}</button>
            ))}
          </div>
        </div>
      )}
      <div className="composer">
        <textarea
          ref={ref}
          value={value}
          rows={1}
          maxLength={4000}
          placeholder="Ask about a quote or type a procurement request…"
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); onSubmit(); }
          }}
        />
        <button aria-label="Send message" disabled={loading || !value.trim()} onClick={onSubmit}>
          {loading ? <LoaderCircle className="spin" size={19} /> : <ArrowUp size={20} />}
        </button>
      </div>
      <small>Procura AI uses market evidence and may ask for missing details. Verify critical decisions.</small>
    </div>
  );
}
