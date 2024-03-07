import TextMessage from "./TextMessage";

const ActionMessage = ({ className, thought, action }) => {

    return (
        <>
            <TextMessage className={className} text={thought} />
            {action && <TextMessage className={className} text={`\`\`\`${action.tool}\n${action.tool_input}\n\`\`\``} />}
        </>
    )
}
export default ActionMessage;
