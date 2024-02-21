import "./index.css";

import { useContext } from "react";
import { useNavigate, useNavigation } from "react-router-dom";

import ChatboxHeader from "components/ChatboxHeader";
import FileUploader from "components/FileUploader";

import { ConversationContext } from "contexts/conversation";
import { DEFAULT_CONV_TITLE } from "commons";

import ChatInput from "./ChatInput";

const createConv = async () => {
    return await fetch("/api/conversations", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ title: DEFAULT_CONV_TITLE }),
    }).then((res) => res.json());
};

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
    const { dispatch } = useContext(ConversationContext);
    const navigate = useNavigate();
    const navigation = useNavigation();

    const handleDrop = async (files) => {
        // TODO: add file size limit
        const conversation = await createConv();
        const response = await uploadFiles(conversation.id, files);
        if (response.ok) {
            const _files = await response.json();
            sessionStorage.setItem(`init-files:${conversation.id}`, JSON.stringify(_files));
            dispatch({ type: "added", conv: conversation });
            navigate(`/conversations/${conversation.id}`);
        } else {
            console.error(response);
        }
    };

    return (
        // TODO: this loading state will render the delete dialog
        <FileUploader className={`chatbox ${navigation.state === "loading" ? "loading" : ""}`} onFilesDrop={handleDrop}>
            <ChatboxHeader />
            {/* TODO: add some examples here */}
            <div className="input-bottom">
                <ChatInput />
                <div className="footer">Pybot can make mistakes. Consider checking important information.</div>
            </div>
        </FileUploader>
    );
}

export default Conversation;
