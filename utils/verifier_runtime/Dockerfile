FROM debian:bookworm-slim

ARG SWEBENCH_VERSION=4.0.3

COPY . /opt/lego-verifier

RUN test -x /opt/lego-verifier/python311/bin/python3 \
    && test -r /opt/lego-verifier/parser_offline_v2.py \
    && /opt/lego-verifier/python311/bin/python3 -c \
       'import datasets, fastcore, swebench; print("verified runtime imports OK")'

LABEL org.opencontainers.image.title="Lego-RL SWE-bench verifier runtime" \
      org.opencontainers.image.description="Portable offline SWE-bench verifier" \
      org.opencontainers.image.version="${SWEBENCH_VERSION}"

CMD ["/bin/sh"]
