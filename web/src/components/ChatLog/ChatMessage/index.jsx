import "./index.css";

import { useState } from "react";

import Avatar from "@mui/material/Avatar";
import Tooltip from "@mui/material/Tooltip";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";

import { getFirstLetters, stringToColor } from "commons";
import TextMessage from "./TextMessage";
import FileMessage from "./FileMessage";


const Message = ({ className, content, type }) => {
  switch (type) {
    case "file":
      return <FileMessage className={className} filename={content.filename} size={content.size} />;
    case "text":
      return <TextMessage className={className} text={content} />;
    default:
      return null;
  }
};

/**
 *
 * @param {object} message
 * @param {string} message.from
 * @param {string} message.content
 * @returns
 */
const ChatMessage = ({ message }) => {
  const [copyTooltipTitle, setCopyTooltipTitle] = useState("copy content");

  const onCopyClick = () => {
    navigator.clipboard.writeText(message.content);
    setCopyTooltipTitle("copied!");
  };

  /**
   * Checks whether a message is sent by bot.
   * @param {*} message
   */
  const botMessage = (message) => {
    const msgFrom = message.from.toLowerCase();
    return msgFrom === "ai" || msgFrom === "assistant";
  };

  return (
    <div className={`chat-message ${botMessage(message) && "AI"}`}>
      <div
        className="chat-message-center"
        onMouseEnter={() => setCopyTooltipTitle("copy content")}
      >
        <Avatar
          className="chat-message-avatar"
          // Cannot handle string to color in css
          sx={{
            bgcolor: stringToColor(message.from),
          }}
        >
          {botMessage(message)
            ? "AI"
            : getFirstLetters(message.from)}
        </Avatar>
        <Message className="chat-message-content" content={message.content} type={message.type} />
        {botMessage(message) && (
          <Tooltip title={copyTooltipTitle}>
            <ContentCopyIcon
              className="chat-message-content-copy"
              onClick={onCopyClick}
            />
          </Tooltip>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
