# Self-contained dev/CI image for dynamics.
#
# dynamics is a *consumer* of EigenScript: it runs .eigs programs against the
# runtime. This image builds EigenScript at a pinned tag and puts it on PATH,
# so the tag below IS the version pin — bump EIGS_REF to move the runtime.
#
# Since the orbit-lab window (fleet UI ladder rung 1, dynamics#20) the image
# builds the *gfx* variant (a strict superset of headless — it runs the
# headless suite fine) and ships SDL2 + Xvfb, so the UI oracle
# (tests/test_orbit_oracle.sh) can open the real window in CI. SDL2 is
# dlopen'd at runtime, so building gfx needs no -dev headers — only libsdl2
# to *run* it. The gfx binary resolves its stdlib relative to itself, so the
# source tree stays at /opt/eigenscript with src/ on PATH (the Tidepool
# devcontainer pattern).
#
# The mouse + render-decode oracle (tests/test_orbit_mouse.sh) additionally
# needs xdotool to drive real input, xwd to grab the window (it ships in
# x11-apps, NOT x11-utils) and PIL to decode the grab. Each is a hard
# dependency: the harness exits 2 = SKIP when one is missing, and CI treats
# a skip as a failure so the oracle can never be silently dropped.
#
# The same image backs Codespaces AND CI (.github/workflows/test.yml runs the
# suite inside it via devcontainers/ci), so "green in my Codespace" and "green
# in CI" can't drift. Building from source (rather than FROM a published
# runtime image) keeps this working for a private repo with no cross-repo
# package-pull credentials.
FROM debian:stable-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        git \
        libsdl2-2.0-0 \
        python3 \
        python3-pil \
        x11-apps \
        xauth \
        xdotool \
        xvfb \
 && rm -rf /var/lib/apt/lists/*

# Full EigenScript source at the pinned tag; build the gfx variant (the
# binary hard-links to src/eigenscript, which finds lib/ next to it).
ARG EIGS_REF=v0.34.0
RUN git clone --depth 1 --branch "${EIGS_REF}" \
        https://github.com/InauguralSystems/EigenScript.git /opt/eigenscript \
 && make -C /opt/eigenscript gfx CC=gcc

ENV PATH="/opt/eigenscript/src:${PATH}"
WORKDIR /workspaces/dynamics
