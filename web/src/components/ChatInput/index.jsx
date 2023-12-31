import "./index.css";

import { useContext, useState, useRef, useEffect } from "react";

import { ConversationContext } from "contexts/conversation";
import { UserContext } from "contexts/user";
import { WebsocketContext } from "contexts/websocket";
import { DEFAULT_CONV_TITLE } from "commons";

/**
 *
 */
const ChatInput = () => {
  const { username } = useContext(UserContext);
  const { conversations, currentConv, dispatch } = useContext(ConversationContext);
  const [ready, send] = useContext(WebsocketContext);

  const [input, setInput] = useState("");
  const inputRef = useRef(null);

  /**
   * Focus on input when chatId changes.
   */
  useEffect(() => {
    if (currentConv?.id) {
      inputRef.current.focus();
    }
  }, [currentConv?.id]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!ready) {
      return;
    }
    const message = { id: crypto.randomUUID(), from: username, content: input, type: "text" };
    const payload = {
      conversation: currentConv.id,
      ...message,
    };
    if (currentConv.title === DEFAULT_CONV_TITLE && currentConv.messages.length === 0) {
      payload.additional_kwargs = { require_summarization: true }
    }
    send(JSON.stringify(payload));
    setInput("");
    // append user input to chatlog
    dispatch({
      type: "messageAdded",
      id: currentConv.id,
      message: message,
    });
    // if current chat is not the first in the list, move it to the first when send message.
    if (conversations[0].id !== currentConv.id) {
      dispatch({
        type: "moveToFirst",
        id: currentConv.id,
      });
    }
  };

  const handleKeyDown = async (e) => {
    // TODO: this will trigger in Chinese IME on OSX
    if (e.key === "Enter") {
      if (e.ctrlKey || e.shiftKey || e.altKey) {
        // won't trigger submit here, but only shift key will add a new line
        return true;
      }
      e.preventDefault();
      await handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="input-container">
      <textarea
        className="input-text"
        ref={inputRef}
        autoFocus
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown} />
      <button disabled={!ready} className="input-submit-button" type="submit">
        Send
      </button>
    </form>
  );
};

export default ChatInput;
