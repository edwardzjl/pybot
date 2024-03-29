import "./index.css";

import { useContext, useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { UserContext } from "contexts/user";
import { ConversationContext } from "contexts/conversation";
import { WebsocketContext } from "contexts/websocket";
import { DEFAULT_CONV_TITLE } from "commons";


/**
 *
 */
const ChatInput = () => {
  const { username } = useContext(UserContext);
  const [ready,] = useContext(WebsocketContext);
  const { dispatch } = useContext(ConversationContext);
  const navigate = useNavigate();
  const [input, setInput] = useState("");
  const inputRef = useRef(null);

  /**
   * Adjusting height of textarea.
   * Ref: <https://blog.muvon.io/frontend/creating-textarea-with-dynamic-height-react>
   */
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "0px";
      const { scrollHeight } = inputRef.current;
      inputRef.current.style.height = `${scrollHeight}px`
    }
  }, [inputRef, input]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const conversation = await fetch("/api/conversations", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ title: DEFAULT_CONV_TITLE }),
    }).then((res) => res.json());
    const message = {
      id: crypto.randomUUID(),
      conversation: conversation.id,
      from: username,
      content: input,
      type: "text"
    };
    sessionStorage.setItem(`init-msg:${conversation.id}`, JSON.stringify(message));
    dispatch({ type: "added", conv: conversation });
    navigate(`/conversations/${conversation.id}`);
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
        id="input-text"
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
