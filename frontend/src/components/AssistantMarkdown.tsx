import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props { content: string; }

function normalizeMarkdown(content: string) {
  // Some chat models place table rows on one line as `| ... | | ... |`.
  return content.replace(/\|\s+\|/g, "|\n|");
}

export function AssistantMarkdown({ content }: Props) {
  return (
    <div className="markdown-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        components={{
          a: ({ children, ...props }) => <a {...props} target="_blank" rel="noreferrer">{children}</a>,
          table: ({ children }) => <div className="table-scroll"><table>{children}</table></div>,
        }}
      >
        {normalizeMarkdown(content)}
      </ReactMarkdown>
    </div>
  );
}
