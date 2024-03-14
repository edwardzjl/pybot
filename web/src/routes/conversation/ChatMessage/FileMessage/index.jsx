import "./index.css";

import { FileIcon, defaultStyles } from "react-file-icon";

import { formatBytes, getExtension } from "commons";


const FileMessage = ({ className, message }) => {
    const fileExtension = getExtension(message.content.filename);

    return (
        <div className={`file-message ${className}`}>
            <div className="file-message-icon">
                <FileIcon extension={fileExtension} {...defaultStyles[fileExtension]} />
            </div>
            <div className="file-message-info">
                <div className="file-message-name">{message.content.filename}</div>
                <div className="file-message-size">{formatBytes(message.content.size)}</div>
            </div>
        </div>
    );
};
export default FileMessage;
