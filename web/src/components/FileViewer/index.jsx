import "./index.css";

import { useEffect, useState } from "react";
import { FileIcon, defaultStyles } from "react-file-icon";

import { getExtension } from "commons";
import { getFiles, uploadFiles } from "requests";

/**
 * <https://claritydev.net/blog/react-typescript-drag-drop-file-upload-guide>
 * <https://claritydev.net/blog/react-hook-form-multipart-form-data-file-uploads>
 */
const FileView = (props) => {
    const [isOver, setIsOver] = useState(false);
    const [files, setFiles] = useState([]);

    // initialization
    useEffect(() => {
        const initialization = async (chatId) => {
            const myFiles = await getFiles(chatId);
            setFiles(myFiles);
        };
        if (props.chatId) {
            initialization(props.chatId);
        }

        return () => { };
    }, [props.chatId]);

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
        const response = await uploadFiles(props.chatId, droppedFiles);
        if (response.ok) {
            const _files = await response.json();
            props.onUpload(props.chatId, _files);
        } else {
            console.error(response);
        }
    };

    return (
        <div
            className="file-view"
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
        >
            Drag and drop some files here
            <div className="files">
                {files.map((file) => {
                    const extension = getExtension(file.filename);
                    return (
                        <div>
                            <div key={file.filename} className="icon">
                                <FileIcon extension={extension} {...defaultStyles[extension]} />
                            </div>
                            <div>{file.filename}</div>
                        </div>
                    )
                })}
            </div>
        </div>
    );
}

export default FileView;
