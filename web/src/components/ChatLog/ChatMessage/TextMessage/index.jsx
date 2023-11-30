import Markdown from "react-markdown";
import SyntaxHighlighter from "react-syntax-highlighter";
import remarkGfm from "remark-gfm";
import { darcula } from "react-syntax-highlighter/dist/esm/styles/prism";

const TextMessage = ({ className, text }) => {
    return (
        <Markdown
            className={className}
            remarkPlugins={[remarkGfm]}
            components={{
                code({ inline, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || "");
                    return !inline && match ? (
                        <SyntaxHighlighter
                            {...props}
                            style={darcula}
                            language={match[1]}
                            PreTag="div"
                        >
                            {/* remove the last line separator, is it necessary? */}
                            {String(children).replace(/\n$/, "")}
                        </SyntaxHighlighter>
                    ) : (
                        <code {...props} className={className}>
                            {children}
                        </code>
                    );
                },
            }}
        >
            {text}
        </Markdown>
    )
}
export default TextMessage;
