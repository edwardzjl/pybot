import "./index.css";

import MarkdownContent from "../MarkdownContent";

const ActionMessage = ({ className, message }) => {

    return (
        <div className={className}>
            <MarkdownContent text={message.content} />
            {message.additional_kwargs &&
                <details className="action-details">
                    <summary>{message.additional_kwargs?.observation === undefined ? "working..." : "finished"}</summary>
                    {message.additional_kwargs?.action &&
                        <MarkdownContent
                            text={`\`\`\`${message.additional_kwargs.action.tool}\n${message.additional_kwargs.action.tool_input}\n\`\`\``}
                        />
                    }
                    {/* TODO: I simply render observation as a markdown console snippet for now */}
                    {message.additional_kwargs?.observation &&
                        <MarkdownContent
                            title="result"
                            text={`\`\`\`pycon\n${message.additional_kwargs.observation}\n\`\`\``}
                        />
                    }
                </details>
            }
        </div>
    )
}
export default ActionMessage;
