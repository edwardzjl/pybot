import "./index.css";

import { useState, useEffect, useRef, useContext } from "react";
import FormControl from '@mui/material/FormControl';
import Input from '@mui/material/Input';
import Tooltip from "@mui/material/Tooltip";
import { ClickAwayListener } from "@mui/base/ClickAwayListener";

import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import DriveFileRenameOutlineIcon from "@mui/icons-material/DriveFileRenameOutline";
import CheckOutlinedIcon from "@mui/icons-material/CheckOutlined";
import CloseOutlinedIcon from "@mui/icons-material/CloseOutlined";

import { ConversationContext, conversationsReducer } from "contexts/conversation";
import { SnackbarContext } from "contexts/snackbar";
import {
  createConversation,
  deleteConversation,
  getConversation,
  updateConversation,
} from "requests";

/**
 *
 * @param {Object} chat
 * @param {string} chat.id
 * @param {string} chat.title
 * @param {boolean} chat.active whether this chat is active
 * @returns
 */
const ChatTab = ({ chat }) => {
  const [conversations, dispatch] = useContext(ConversationContext);
  const [, setSnackbar] = useContext(SnackbarContext);

  const [title, setTitle] = useState(chat?.title);
  useEffect(() => {
    setTitle(chat?.title);
  }, [chat?.title]);
  const titleRef = useRef(null);

  const [titleReadOnly, setTitleReadOnly] = useState(true);

  const [operationConfirm, setOperationConfirm] = useState(
    /** @type {[{onConfirm: boolean, operation: string}]} */ {
      onConfirm: false,
    }
  );

  const handleTitleChange = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setTitle(() => e.target.value);
  };

  const selectChat = async (e, chat) => {
    e.preventDefault();
    e.stopPropagation();
    if (chat.active) {
      return;
    }
    const detailedConv = await getConversation(chat.id);
    dispatch({
      type: "selected",
      data: detailedConv,
    });
  };

  const deleteChat = async (chatId) => {
    deleteConversation(chatId)
      .then(() => {
        const deleteAction = {
          type: "deleted",
          id: chatId,
        };
        const nextState = conversationsReducer(conversations, deleteAction);
        if (!nextState.length) {
          createConversation().then((data) => {
            dispatch(deleteAction);
            dispatch({
              type: "added",
              conversation: data,
            });
          });
        } else {
          // there's still conversations left, check if we are deleting the active one
          const toDelete = conversations.find((c) => c.id === chatId);
          if (toDelete.active) {
            // switch to the first conversation
            // select before delete makes the page more smooth
            getConversation(nextState[0].id)
              .then((data) => {
                dispatch({
                  type: "selected",
                  data: data,
                });
              });
          }
          dispatch(deleteAction);
        }
        setSnackbar({
          open: true,
          severity: "success",
          message: "Chat deleted",
        });
      })
      .catch((err) => {
        console.error("error deleting chat", err);
        setSnackbar({
          open: true,
          severity: "error",
          message: "Delete chat failed",
        });
      });
  };

  const renameChat = async (id, title) => {
    setTitleReadOnly(true);
    updateConversation(id, title).then((res) => {
      if (res.ok) {
        setSnackbar({
          open: true,
          severity: "success",
          message: "Update chat success",
        });
      } else {
        console.error("error updating chat");
        setSnackbar({
          open: true,
          severity: "error",
          message: "Update chat failed",
        });
      }
    });
  };

  const onUpdateClick = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    titleRef.current.focus();
    setOperationConfirm({ onConfirm: true, operation: "rename" });
    setTitleReadOnly(false);
  };

  const onDeleteClick = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setOperationConfirm({ onConfirm: true, operation: "delete" });
  };

  const onConfirm = async (e, chatId) => {
    e.preventDefault();
    e.stopPropagation();
    if (operationConfirm.operation === "delete") {
      deleteChat(chatId);
    } else if (operationConfirm.operation === "rename") {
      renameChat(chatId, title);
    }
    setOperationConfirm({ onConfirm: false });
  };

  const onCancel = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setOperationConfirm({ onConfirm: false });
  };

  return (
    <div
      className={`sidemenu-button ${chat.active && "selected"}`}
      onClick={(e) => selectChat(e, chat)}
    >
      <Tooltip title={title}>
        <FormControl
          id="chat-title"
          variant="standard"
        >
          <Input
            id="chat-title"
            // TODO: className not working, there's a MuiFormControl-root that will override className
            className="chat-title"
            disableUnderline
            inputProps={{
              style: {
                width: 160,
                height: 10,
                color: "white",
                overflow: "hidden",
                textOverflow: "ellipsis",
              },
            }}
            readOnly={titleReadOnly}
            inputRef={titleRef}
            value={title}
            onChange={(e) => handleTitleChange(e)}
          />
        </FormControl>
      </Tooltip>

      <div className="sidemenu-button-operations">
        {/* Operations */}
        {!operationConfirm?.onConfirm && (
          <div>
            <DriveFileRenameOutlineIcon onClick={(e) => onUpdateClick(e)} />
            <DeleteOutlineIcon onClick={(e) => onDeleteClick(e)} />
          </div>
        )}
        {/* Confirmations */}
        {operationConfirm?.onConfirm && (
          <ClickAwayListener onClickAway={onCancel}>
            <div>
              <CheckOutlinedIcon onClick={(e) => onConfirm(e, chat.id)} />
              <CloseOutlinedIcon onClick={(e) => onCancel(e)} />
            </div>
          </ClickAwayListener>
        )}
      </div>
    </div>
  );
};

export default ChatTab;
