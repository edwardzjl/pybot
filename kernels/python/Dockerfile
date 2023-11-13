FROM elyra/kernel-py:3.2.2

USER root

RUN pip install --no-cache-dir \
  pandas==2.1.3 \
  scikit-learn==1.3.2 \
  seaborn==0.13.0

USER $NB_UID
