import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import remarkGfm from "remark-gfm";
import { darcula } from "react-syntax-highlighter/dist/esm/styles/prism";

const TextMessage = ({ className, text }) => {
    return (
        <ReactMarkdown
            className={className}
            children={text}
            remarkPlugins={[remarkGfm]}
            components={{
                code({ node, inline, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || "");
                    return !inline && match ? (
                        <SyntaxHighlighter
                            {...props}
                            children={String(children).replace(/\n$/, "")}
                            style={darcula}
                            language={match[1]}
                            PreTag="div"
                        />
                    ) : (
                        <code {...props} className={className}>
                            {children}
                        </code>
                    );
                },
            }}
        />
    )
}
export default TextMessage;
