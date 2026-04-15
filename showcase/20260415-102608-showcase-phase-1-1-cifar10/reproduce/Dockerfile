FROM maars-sandbox:latest
USER root
COPY artifacts/ /workspace/artifacts/
COPY reproduce/run.sh /workspace/run.sh
RUN chmod +x /workspace/run.sh && chown -R sandbox:sandbox /workspace
USER sandbox
WORKDIR /workspace
CMD ["bash", "run.sh"]
