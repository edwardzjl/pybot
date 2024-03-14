# Pybot

A simple, multi-user, multi-conversation, web-based pybot.

## Features

### Multi User

Pybot incorporates OpenID Connect for user identification. It relies on an external OAuth Client [oidc-authservice](https://github.com/arrikto/oidc-authservice) to handle authentication and set a trusted `userid` Header to the downstream services. Alternatively, [oauth2-proxy](https://github.com/oauth2-proxy/oauth2-proxy), which is more actively maintained, can be used in place of `oidc-authservice`.

### Multi Conversation

Pybot supports multiple conversations. Each conversation is identified by a unique `conversationId`. Conversations consists of a sequence of `messages` as well as metadata such as `title`, `updatedAt`. Message persistance is handled by [langchain](https://github.com/langchain-ai/langchain)'s `RedisChatMessageHistory` module, which leverages Redis for storing chat history. Metadata persistance is handled separately by [redis-om](https://github.com/redis/redis-om-python), an object mapping library for Redis from Redis Labs. This separation of message content and metadata storage provides modularity and flexibility in the pybot's underlying persistence architecture.

### Streaming

Pybot supports streaming LLM outputs to the user in real-time. Streaming messages are delivered via [WebSockets](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API), which enables bidirectional, full-duplex communication channels between the server and client.

On the LLM side, Pybot uses [Text Generation Inference (TGI)](https://github.com/huggingface/text-generation-inference), an open source library from HuggingFace, to host large language models for text generation. TGI provides out-of-the-box support for continuous batching, streaming inference, and other useful features for deploying production-ready LLMs.
Using TGI eliminates the need to build complex serving infrastructure from scratch. Its continuous batching allows the pybot to achieve high throughput by batching requests. Streaming inference enables the pybot to return partial results instantly rather than waiting for the full output.

## Architecture

## Deployment

See [deployment instructions](./manifests/README.md)

## Configuration

Key | Default Value | Description
---|---|---
LOG_LEVEL | `INFO` | log level
REDIS_OM_URL | `redis://localhost:6379` | Redis url to persist messages and metadata
LLM__URL | `http://localhost:8080` | LLM service url
LLM__CREDS | `EMPTY` | LLM service credentials
LLM__MODEL | `cognitivecomputations/dolphincoder-starcoder2-15b` | LLM model name
LLM__EOS_TOKEN | `<\|im_end\|>` | End of sentence token
JUPYTER__GATEWAY_URL | `http://localhost:8888` | URL of the Jupyter Enterprise Gateway.
JUPYTER__KERNEL_NAMESPACE | `None` | Namespace to start the kernel in. If not set, a new namespace will be created in form of `${KERNEL_USERNAME}-${UUID}.`
JUPYTER__SHARED_VOLUME_MOUNT_PATH | `/mnt/shared` | Path to mount the shared volume in the kernel container.
JUPYTER__SHARED_VOLUME_NFS_SERVER | `localhost` | NFS server to mount the shared volume from.
JUPYTER__SHARED_VOLUME_NFS_PATH | `/data/pybot/shared` | Path to the shared volume on the NFS server.
USER_ID_HEADER | `X-Forwarded-User` | Header to use for user identification.
