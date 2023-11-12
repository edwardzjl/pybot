# Jupyter Enterprise Gateway

- github: <https://github.com/jupyter-server/enterprise_gateway>
- deploy: <https://jupyter-enterprise-gateway.readthedocs.io/en/latest/operators/deploy-kubernetes.html>
- usage: <https://jupyter-enterprise-gateway.readthedocs.io/en/latest/developers/rest-api.html>

## Culling idle kernels

> See <https://jupyter-enterprise-gateway.readthedocs.io/en/latest/operators/config-culling.html>

Corresponding enterprise-gateway deployment env:

```yaml
# Source: enterprise-gateway/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: enterprise-gateway
spec:
  template:
    spec:
      containers:
      - name: enterprise-gateway
        env:
        - name: EG_CULL_IDLE_TIMEOUT
          value: !!str 3600
        - name: EG_CULL_CONNECTED
          value: "False"
        ...
```
