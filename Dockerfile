FROM node:lts-alpine as frontend-builder

ARG PUBLIC_URL=

WORKDIR /build
COPY web/package.json web/yarn.lock ./
RUN yarn
COPY web/ ./
RUN yarn build


FROM python:3.11-slim as backend-builder
RUN pip install pipenv

COPY api/Pipfile api/Pipfile.lock ./
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy


FROM python:3.11-slim as app

WORKDIR /app

COPY --from=backend-builder /.venv ./.venv
ENV PATH="/app/.venv/bin:$PATH"
COPY api/ .
COPY --from=frontend-builder /build/build ./static

RUN adduser --system --no-create-home --group pybot \
  && chown -R pybot:pybot /app
USER pybot:pybot

ENTRYPOINT [ "python", "-m", "uvicorn", "pybot.main:app" ]
CMD [ "--host", "0.0.0.0", "--port", "8000" ]
