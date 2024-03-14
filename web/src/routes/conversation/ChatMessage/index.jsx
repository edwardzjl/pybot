import "./index.css";

import { useContext, useState } from "react";

import Avatar from "@mui/material/Avatar";
import Tooltip from "@mui/material/Tooltip";

import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import ThumbUpIcon from '@mui/icons-material/ThumbUp';
import ThumbUpOutlined from "@mui/icons-material/ThumbUpOutlined";
import ThumbDownIcon from '@mui/icons-material/ThumbDown';
import ThumbDownOutlined from "@mui/icons-material/ThumbDownOutlined";

import { getFirstLetters, stringToColor } from "commons";
import { MessageContext } from "contexts/message";
import { UserContext } from "contexts/user";
import TextMessage from "./TextMessage";
import FileMessage from "./FileMessage";
import ActionMessage from "./ActionMessage";


const Message = ({ className, message }) => {
  switch (message.type) {
    case "file":
      return <FileMessage className={className} message={message} />;
    case "text":
      return <TextMessage className={className} text={message.content} />;
    case "action":
      return <ActionMessage className={className} message={message} />;
    default:
      console.debug("Unknown message type: ", message.type);
      return null;
  }
};

/**
 * @param {string} convId
 * @param {integer} idx
 * @param {object} message
 * @param {string} message.from
 * @param {string} message.content
 * @returns
 */
const ChatMessage = ({ convId, idx, message }) => {
  const { username } = useContext(UserContext);
  const { dispatch } = useContext(MessageContext);
  const [copyTooltipTitle, setCopyTooltipTitle] = useState("copy content");
  const [thumbUpTooltipTitle, setThumbUpTooltipTitle] = useState("good answer");
  const [thumbDownTooltipTitle, setThumbDownTooltipTitle] = useState("bad answer");

  const onCopyClick = (content) => {
    navigator.clipboard.writeText(content);
    setCopyTooltipTitle("copied!");
    setTimeout(() => {
      setCopyTooltipTitle("copy content");
    }, "3000");
  };
  const onThumbUpClick = () => {
    fetch(`/api/conversations/${convId}/messages/${idx}/thumbup`, {
      method: "PUT",
    }).then(() => {
      setThumbUpTooltipTitle("thanks!");
      dispatch({
        type: "feedback",
        id: convId,
        idx: idx,
        feedback: "thumbup",
      });
    });
  };
  const onThumbDownClick = () => {
    fetch(`/api/conversations/${convId}/messages/${idx}/thumbdown`, {
      method: "PUT",
    }).then(() => {
      setThumbDownTooltipTitle("thanks!");
      dispatch({
        type: "feedback",
        id: convId,
        idx: idx,
        feedback: "thumbdown",
      });
    });
  };

  /**
   * Checks whether a message is sent by me.
   * @param {*} message
   */
  const myMessage = (message) => {
    const msgFrom = message.from.toLowerCase();
    return msgFrom === username;
  };

  return (
    <div className={`message-container ${myMessage(message) && "mine"}`}>
      <div className="message-title">
        <Avatar
          className="message-title-avatar"
          // Cannot handle string to color in css
          sx={{
            bgcolor: stringToColor(message.from),
          }}
        >
          {myMessage(message) ? getFirstLetters(message.from) : "AI"}
        </Avatar>
        <div className="message-title-name">{myMessage(message) ? "You" : "AI"}</div>
      </div>
      <div className="message-body">
        <Message className="message-content" message={message} />
        {!myMessage(message) && (
          <div className="message-feedbacks">
            <Tooltip title={copyTooltipTitle}>
              <ContentCopyIcon className="message-feedback" onClick={() => onCopyClick(message.content)} />
            </Tooltip>
            {message.feedback === "thumbdown" ? undefined : message.feedback === "thumbup" ? <ThumbUpIcon className="message-feedback" /> :
              <Tooltip title={thumbUpTooltipTitle}>
                <ThumbUpOutlined className="message-feedback" onClick={onThumbUpClick} />
              </Tooltip>
            }
            {message.feedback === "thumbup" ? undefined : message.feedback === "thumbdown" ? <ThumbDownIcon className="message-feedback" /> :
              <Tooltip title={thumbDownTooltipTitle}>
                <ThumbDownOutlined className="message-feedback" onClick={onThumbDownClick} />
              </Tooltip>
            }
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
