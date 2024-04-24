import { useContext, useEffect, useState } from "react";

import Markdown from "react-markdown";
import SyntaxHighlighter from "react-syntax-highlighter";
import remarkGfm from "remark-gfm";
import { darcula, googlecode } from "react-syntax-highlighter/dist/esm/styles/hljs";
import Tooltip from "@mui/material/Tooltip";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";

import { ThemeContext } from "contexts/theme";

const MarkdownContent = ({ title, text }) => {
    const { theme } = useContext(ThemeContext);
    const [markdownTheme, setMarkdownTheme] = useState(darcula);
    const [copyTooltipTitle, setCopyTooltipTitle] = useState("copy content");

    useEffect(() => {
        switch (theme) {
            case "dark":
                setMarkdownTheme(darcula);
                break;
            case "light":
                setMarkdownTheme(googlecode);
                break;
            default: {
                if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
                    setMarkdownTheme(darcula);
                } else {
                    setMarkdownTheme(googlecode);
                }
            }
        }
    }, [theme]);

    const onCopyClick = (content) => {
        navigator.clipboard.writeText(content);
        setCopyTooltipTitle("copied!");
        setTimeout(() => {
            setCopyTooltipTitle("copy content");
        }, "3000");
    };

    return (
        <Markdown
            remarkPlugins={[remarkGfm]}
            components={{
                code({ inline, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || "");
                    return !inline && match ? (
                        <div>
                            <div className="message-code-title">
                                <span>{title || match[1]}</span>
                                <Tooltip title={copyTooltipTitle}>
                                    <ContentCopyIcon onClick={() => onCopyClick(children)} />
                                </Tooltip>
                            </div>
                            <SyntaxHighlighter
                                {...props}
                                style={markdownTheme}
                                language={match[1]}
                                PreTag="div"
                            >
                                {/* remove the last line separator, is it necessary? */}
                                {String(children).replace(/\n$/, "")}
                            </SyntaxHighlighter>
                        </div>
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
};

export default MarkdownContent;
