import MarkdownContent from "./MarkdownContent";


const TextMessage = ({ className, text }) => {
    return (
        <div className={className}>
            <MarkdownContent text={text} />
        </div>
    )
}
export default TextMessage;
