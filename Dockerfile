FROM python:3.12-slim

ARG PIPER_VOICE_REV=8aaa3c9839d2b669cb57a94e1ec92ae0928897e8
ARG PIPER_MODEL_SHA256=9df1c43c61149ef9b39e618e2b861fbe41e1fcea9390b2dac62e8761573ea4f1
ARG PIPER_VOICE=de_DE-thorsten-high

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIPER_VOICE_PATH=/opt/piper/de_DE-thorsten-high.onnx

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates curl libespeak-ng1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install . \
    && pip install piper-tts==1.6.0 \
    && python -m spacy download de_core_news_md

# The revision, digest and model-card fetch are all explicit so a changed voice
# artifact cannot silently enter the runtime image.
RUN mkdir -p /opt/piper /usr/share/doc/flashcard \
    && voice_url="https://huggingface.co/rhasspy/piper-voices/resolve/${PIPER_VOICE_REV}/de/de_DE/thorsten/high" \
    && curl --fail --location --silent --show-error "${voice_url}/${PIPER_VOICE}.onnx" \
       --output "${PIPER_VOICE_PATH}" \
    && echo "${PIPER_MODEL_SHA256}  ${PIPER_VOICE_PATH}" | sha256sum --check --status \
    && curl --fail --location --silent --show-error "${voice_url}/${PIPER_VOICE}.onnx.json" \
       --output "${PIPER_VOICE_PATH}.json" \
    && curl --fail --location --silent --show-error "${voice_url}/MODEL_CARD" \
       --output /usr/share/doc/flashcard/THORSTEN-MODEL-CARD \
    && grep --fixed-strings --quiet 'License: CC0' /usr/share/doc/flashcard/THORSTEN-MODEL-CARD \
    && printf '%s\n' \
       'Piper engine: GPL-3.0-or-later (https://github.com/rhasspy/piper)' \
       'Piper voices repository metadata: MIT (https://huggingface.co/rhasspy/piper-voices)' \
       'Thorsten-Voice dataset/model card: CC0 (pinned MODEL_CARD above)' \
       "Voice: ${PIPER_VOICE}; source revision: ${PIPER_VOICE_REV}" \
       "Model SHA-256: ${PIPER_MODEL_SHA256}" \
       > /usr/share/doc/flashcard/PIPER-NOTICES \
    && piper --help >/dev/null

# Bounded build smoke: no cache/database/media is baked beyond the selected
# pinned voice, and no LLM SDK is installed in this runtime dependency graph.
RUN printf 'Guten Tag.' | piper --model "${PIPER_VOICE_PATH}" --output_file /tmp/piper-smoke.wav \
    && test -s /tmp/piper-smoke.wav \
    && rm /tmp/piper-smoke.wav \
    && ! pip freeze | grep -E '^(anthropic|openai|google-genai)=='

CMD ["python", "-c", "import spacy; spacy.load('de_core_news_md'); print('flashcard runtime ready')"]
