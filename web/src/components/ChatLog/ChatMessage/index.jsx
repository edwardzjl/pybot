import "./index.css";

import { useState } from "react";

import Avatar from "@mui/material/Avatar";
import Tooltip from "@mui/material/Tooltip";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";

import { getFirstLetters, stringToColor } from "commons";
import TextMessage from "./TextMessage";
import FileMessage from "./FileMessage";



const Message = ({ content, type }) => {
  switch (type) {
    case "file":
      return <FileMessage filename={content.filename} />;
    case "text":
    case "stream":
      return <TextMessage text={content} />;
    default:
      return null;
  }
};

/**
 *
 * @param {object} props
 * @param {object} props.message
 * @param {string} props.message.from
 * @param {string} props.message.content
 * @returns
 */
const ChatMessage = (props) => {
  const [copyTooltipTitle, setCopyTooltipTitle] = useState("copy content");

  const handleMouseIn = () => {
    setCopyTooltipTitle("copy content");
  };

  const onCopyClick = () => {
    navigator.clipboard.writeText(props.message.content);
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
    <div className={`chat-message ${botMessage(props.message) && "AI"}`}>
      <div
        className="chat-message-center"
        onMouseEnter={handleMouseIn}
      >
        <Avatar
          className="chat-message-avatar"
          // Cannot handle string to color in css
          sx={{
            bgcolor: stringToColor(props.message.from),
          }}
        >
          {botMessage(props.message)
            ? "AI"
            : getFirstLetters(props.message.from)}
        </Avatar>
        <Message content={props.message.content} type={props.message.type} />
        {botMessage(props.message) && (
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
