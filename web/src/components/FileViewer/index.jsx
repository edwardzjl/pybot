import "./index.css";

import { useEffect, useState } from "react";
import { FileIcon, defaultStyles } from "react-file-icon";

import { getExtension } from "commons";
import { getFiles, uploadFiles } from "requests";

/**
 * <https://claritydev.net/blog/react-typescript-drag-drop-file-upload-guide>
 * <https://claritydev.net/blog/react-hook-form-multipart-form-data-file-uploads>
 */
const FileView = ({ chatId, onUpload }) => {
    const [isOver, setIsOver] = useState(false);
    const [files, setFiles] = useState([]);

    // initialization
    useEffect(() => {
        const initialization = async (chatId) => {
            const myFiles = await getFiles(chatId);
            setFiles(myFiles);
        };
        if (chatId !== undefined) {
            initialization(chatId);
        }

        return () => { };
    }, [chatId]);

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
        const response = await uploadFiles(chatId, droppedFiles);
        if (response.ok) {
            const _files = await response.json();
            onUpload(chatId, _files);
            setFiles([...files, ..._files]);
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
                        <div key={file.filename}>
                            <div className="icon">
                                <FileIcon extension={extension} {...defaultStyles[extension]} />
                            </div>
                            <div className="filename">{file.filename}</div>
                        </div>
                    )
                })}
            </div>
        </div>
    );
}

export default FileView;
