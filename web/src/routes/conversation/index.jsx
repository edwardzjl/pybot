import "./index.css";

import ChatboxHeader from "components/ChatboxHeader";
import FileUploader from "components/FileUploader";

import ChatLog from "./ChatLog";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";


const Conversation = ({ currentConv }) => {
    return (
        <>
            <ChatboxHeader />
            <FileUploader>
                <ChatLog className="chat-log">
                    {currentConv && currentConv.messages && currentConv.messages.map((message, index) => (
                        <ChatMessage key={index} convId={currentConv.id} idx={index} message={message} />
                    ))}
                </ChatLog>
            </FileUploader>
            <div className="input-bottom">
                <ChatInput />
                <div className="footer">Pybot can make mistakes. Consider checking important information.</div>
            </div>
        </>
    );
}

export default Conversation;
