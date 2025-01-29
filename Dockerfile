FROM mambaorg/micromamba:2.0.5
WORKDIR /app

COPY --chown=$MAMBA_USER:$MAMBA_USER ./ /app
COPY --chown=$MAMBA_USER:$MAMBA_USER env-docker.yml /tmp/env.yaml
RUN micromamba install -y -n base -f /tmp/env.yaml && \
    micromamba clean --all --yes



