#!/bin/sh

VERSION="3.2.3"
OUTPUT="jupyter-enterprise-gateway.yaml"
NAMESPACE="jupyter"

# --output-dir has some pattern
helm template enterprise-gateway \
  https://github.com/jupyter-server/enterprise_gateway/releases/download/v$VERSION/jupyter_enterprise_gateway_helm-$VERSION.tar.gz \
  --namespace $NAMESPACE \
  > $OUTPUT
