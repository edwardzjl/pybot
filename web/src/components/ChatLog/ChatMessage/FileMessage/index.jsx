import "./index.css";

import { FileIcon, defaultStyles } from "react-file-icon";

import { formatBytes, getExtension } from "commons";


const FileMessage = ({ className, filename, size }) => {
    const fileExtension = getExtension(filename);

    return (
        <div className={`file-message ${className}`}>
            <div className="file-message-icon">
                <FileIcon extension={fileExtension} {...defaultStyles[fileExtension]} />
            </div>
            <div className="file-message-info">
                <div className="file-message-name">{filename}</div>
                <div className="file-message-size">{formatBytes(size)}</div>
            </div>
        </div>
    );
};
export default FileMessage;
