import { useContext, useState } from "react";

import { uploadFiles } from "requests";
import { ConversationContext } from "contexts/conversation";
import { UserContext } from "contexts/user";
import { WebsocketContext } from "contexts/websocket";

/**
 * <https://claritydev.net/blog/react-typescript-drag-drop-file-upload-guide>
 * <https://claritydev.net/blog/react-hook-form-multipart-form-data-file-uploads>
 */
const FileUploader = ({ children }) => {
    const { username } = useContext(UserContext);
    const { currentConv, dispatch } = useContext(ConversationContext);
    const [, send] = useContext(WebsocketContext);
    const [, setIsOver] = useState(false);
    const [files, setFiles] = useState([]);

    // Define the event handlers
    const handleDragOver = (event) => {
        event.preventDefault();
        setIsOver(true);
    };

    const handleDragLeave = (event) => {
        event.preventDefault();
        setIsOver(false);
    };

    const handleDrop = async (event) => {
        console.log("handleDrop")
        event.preventDefault();
        setIsOver(false);
        const droppedFiles = Array.from(event.dataTransfer.files);
        const response = await uploadFiles(currentConv.id, droppedFiles);
        if (response.ok) {
            const _files = await response.json();
            _files.forEach((file) => {
                const msg = {
                    id: crypto.randomUUID(),
                    conversation: currentConv.id,
                    from: username,
                    content: file,
                    type: "file"
                }
                send(JSON.stringify(msg));
                console.log("sent", msg)
                dispatch({
                    type: "messageAdded",
                    id: currentConv.id,
                    message: msg,
                });
            });
            setFiles([...files, ..._files]);
        } else {
            console.error(response);
        }
    };

    return (
        <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
        >
            {children}
        </div>
    );
}

export default FileUploader;
