import "./index.css";

import { useContext, useState } from "react";
import { useParams } from 'react-router-dom';

import { uploadFiles } from "requests";
import { UserContext } from "contexts/user";
import { MessageContext } from "contexts/message";
import { WebsocketContext } from "contexts/websocket";

/**
 * <https://claritydev.net/blog/react-typescript-drag-drop-file-upload-guide>
 * <https://claritydev.net/blog/react-hook-form-multipart-form-data-file-uploads>
 */
const FileUploader = ({ children }) => {
    const { convId } = useParams();
    const { username } = useContext(UserContext);
    const { dispatch } = useContext(MessageContext);
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
        event.preventDefault();
        setIsOver(false);
        const droppedFiles = Array.from(event.dataTransfer.files);
        const response = await uploadFiles(convId, droppedFiles);
        if (response.ok) {
            const _files = await response.json();
            _files.forEach((file) => {
                const msg = {
                    id: crypto.randomUUID(),
                    conversation: convId,
                    from: username,
                    content: file,
                    type: "file"
                }
                send(JSON.stringify(msg));
                dispatch({
                    type: "added",
                    id: convId,
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
            className="file-uploader"
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
        >
            {children}
        </div>
    );
}

export default FileUploader;
