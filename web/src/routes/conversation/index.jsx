import "./index.css";

import { useContext, useEffect } from "react";
import { useLoaderData, redirect } from "react-router-dom";

import ChatboxHeader from "components/ChatboxHeader";
import FileUploader from "components/FileUploader";

import { MessageContext } from "contexts/message";
import { UserContext } from "contexts/user";
import { WebsocketContext } from "contexts/websocket";

import ChatLog from "./ChatLog";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";


export async function loader({ params }) {
    const resp = await fetch(`/api/conversations/${params.convId}`, {});
    if (!resp.ok) {
        return redirect("/");
    }
    const conversation = await resp.json();
    return { conversation };
}

/**
 * Upload files to conversation
 * @param {string} conversationId
 * @param {string} files
 */
const uploadFiles = async (conversationId, files) => {
    const formData = new FormData();
    files.forEach(file => {
        formData.append("files", file);
    });
    return fetch(`/api/conversations/${conversationId}/files`, {
        method: "POST",
        body: formData,
    });
};


const Conversation = () => {
    const { conversation } = useLoaderData();
    const { username } = useContext(UserContext);
    const [ready, send] = useContext(WebsocketContext);
    const { messages, dispatch } = useContext(MessageContext);

    useEffect(() => {
        if (conversation?.messages) {
            dispatch({
                type: "replaceAll",
                messages: conversation.messages,
            });
            const initMsg = sessionStorage.getItem(`init-msg:${conversation.id}`);
            if (initMsg) {
                const message = JSON.parse(initMsg);
                dispatch({
                    type: "added",
                    message: message,
                });
                if (ready) {
                    // TODO: should I wait until ready?
                    send(JSON.stringify({ additional_kwargs: { require_summarization: true }, ...message }));
                }
                sessionStorage.removeItem(`init-msg:${conversation.id}`);
            }
            const initFiles = sessionStorage.getItem(`init-files:${conversation.id}`);
            if (initFiles) {
                const files = JSON.parse(initFiles);
                files.forEach((file) => {
                    const msg = {
                        id: crypto.randomUUID(),
                        conversation: conversation.id,
                        from: username,
                        content: file,
                        type: "file"
                    }
                    dispatch({
                        type: "added",
                        id: conversation.id,
                        message: msg,
                    });
                    if (ready) {
                        // TODO: should I wait until ready?
                        send(JSON.stringify({ additional_kwargs: { require_summarization: true }, ...msg }));
                    }
                });
                sessionStorage.removeItem(`init-files:${conversation.id}`);
            }
        }
    }, [conversation]);

    const handleDrop = async (files) => {
        // TODO: add file size limit
        const response = await uploadFiles(conversation.id, files);
        if (response.ok) {
            const _files = await response.json();
            _files.forEach((file) => {
                const msg = {
                    id: crypto.randomUUID(),
                    conversation: conversation.id,
                    from: username,
                    content: file,
                    type: "file"
                }
                send(JSON.stringify(msg));
                dispatch({
                    type: "added",
                    id: conversation.id,
                    message: msg,
                });
            });
        } else {
            console.error(response);
        }
    };

    return (
        <>
            <ChatboxHeader />
            <FileUploader className="uploader" onFilesDrop={handleDrop}>
                <ChatLog className="chat-log">
                    {conversation && messages?.map((message, index) => (
                        <ChatMessage key={index} convId={conversation.id} idx={index} message={message} />
                    ))}
                </ChatLog>
            </FileUploader>
            <div className="input-bottom">
                <ChatInput conv={conversation} />
                <div className="footer">Pybot can make mistakes. Consider checking important information.</div>
            </div>
        </>
    );
}

export default Conversation;
