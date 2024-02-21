import { useState } from "react";


/**
 *
 * <https://claritydev.net/blog/react-typescript-drag-drop-file-upload-guide>
 * <https://claritydev.net/blog/react-hook-form-multipart-form-data-file-uploads>
 */
const FileUploader = ({ children, className, onFilesDrop }) => {
    const [, setIsOver] = useState(false);

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
        onFilesDrop(droppedFiles);
    };

    return (
        <div id="file-uploader"
            className={className}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
        >
            {children}
        </div>
    );
}

export default FileUploader;
