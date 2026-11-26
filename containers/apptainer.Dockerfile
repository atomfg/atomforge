# Apptainer in a container, for converting a Docker image to a SIF on a machine
# without Apptainer (e.g. a Mac with colima). Built for the machine's own
# platform: Go programs such as Apptainer crash under Rosetta's amd64
# emulation. The SIF's architecture comes from the binaries in the image, not
# from the machine that builds it, so an arm64 Apptainer makes an amd64 SIF
# from an amd64 image. Used by `just build-sif`.
FROM ubuntu:24.04
RUN apt-get update \
    && apt-get install --yes --no-install-recommends software-properties-common \
    && add-apt-repository --yes ppa:apptainer/ppa \
    && apt-get install --yes --no-install-recommends apptainer \
    && rm -rf /var/lib/apt/lists/*
