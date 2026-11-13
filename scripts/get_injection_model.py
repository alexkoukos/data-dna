"""Download the prompt-injection classifier (about 740 MB) into the models volume.

  make injection-model

Runs inside the brain image so the file lands in the `models` volume the brain reads.
"""

from huggingface_hub import snapshot_download

snapshot_download(
    "protectai/deberta-v3-base-prompt-injection-v2",
    local_dir="/models/injection",
    allow_patterns=["onnx/*"],
)
print("Done. The brain loads it within 30 seconds, no restart needed.")
