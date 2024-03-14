import MarkdownContent from "./MarkdownContent";

const ActionMessage = ({ className, message }) => {

    return (
        <div className={className}>
            <MarkdownContent text={message.content} />
            {message.additional_kwargs?.action &&
                <MarkdownContent
                    text={`\`\`\`${message.additional_kwargs.action.tool}\n${message.additional_kwargs.action.tool_input}\n\`\`\``}
                />
            }
            {/* TODO: I simply render observation as a markdown console snippet for now */}
            {message.additional_kwargs?.observation &&
                <MarkdownContent
                    title='result'
                    text={`\`\`\`console\n${message.additional_kwargs.observation}\n\`\`\``}
                />
            }
        </div>
    )
}
export default ActionMessage;
