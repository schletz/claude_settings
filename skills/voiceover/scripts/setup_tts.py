"""Check the F5-TTS install and fetch the German checkpoint into the work directory.

F5-TTS is a flow-matching model, not an autoregressive one, so it does not collapse
into the repetition loops that sink autoregressive TTS on short utterances. It also
learns pronunciation from text: there is no phonemiser to fight and no respelling
layer to maintain.

Usage:
    python setup_tts.py <workdir>
    python setup_tts.py <workdir> --repo aihpi/F5-TTS-German \
        --file F5TTS_Base/model_420000.safetensors
"""

import argparse
import os
import shutil
import sys

# hvoss-techfak trained 4.2M steps on Common Voice 19 plus an internal corpus and
# ships a single checkpoint file, which makes it the least fiddly default. Both
# known German checkpoints are CC-BY-NC-4.0 — fine privately, not for publishing.
DEFAULT_REPO = "hvoss-techfak/F5-TTS-German"
DEFAULT_CKPT = "model_f5tts_german.safetensors"
DEFAULT_VOCAB = "vocab.txt"

INSTALL_HINT = """\
F5-TTS fehlt oder ist unvollstaendig installiert.

Installiere es OHNE Abhaengigkeiten, sonst ueberschreibt pip dein CUDA-torch mit
einer Version ohne Kernel fuer deine GPU:

    python -m pip install --no-deps f5-tts
    python -m pip install --no-deps torchaudio torchcodec
    python -m pip install cached_path vocos x-transformers torchdiffeq ema-pytorch \\
        jieba pypinyin librosa pydub tomli hydra-core accelerate unidecode rjieba \\
        transformers_stream_generator

gradio verlangt f5-tts nur fuer seine Weboberflaeche - weglassen.
torchaudio hinkt auf PyPI regelmaessig eine Version hinter torch her; mit
--no-deps laedt es trotzdem, und torchcodec macht daraus wieder einen
funktionierenden Audio-Loader.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workdir")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--file", default=DEFAULT_CKPT)
    parser.add_argument("--vocab", default=DEFAULT_VOCAB)
    args = parser.parse_args()

    try:
        import torch
        from f5_tts.api import F5TTS  # noqa: F401
    except ImportError as exc:
        sys.exit(f"{INSTALL_HINT}\nFehlend: {exc.name}")

    print(f"Python     : {sys.executable}")
    print(f"torch      : {torch.__version__}")
    if torch.cuda.is_available():
        print(f"GPU        : {torch.cuda.get_device_name(0)}")
    else:
        print("GPU        : keine - F5-TTS laeuft auf der CPU rund 20x langsamer")

    from huggingface_hub import hf_hub_download

    os.makedirs(args.workdir, exist_ok=True)
    for name in (args.file, args.vocab):
        target = os.path.join(args.workdir, os.path.basename(name))
        if os.path.exists(target):
            print(f"vorhanden  : {target}")
            continue
        cached = hf_hub_download(args.repo, name)
        shutil.copy(cached, target)
        size = os.path.getsize(target) / 1024 / 1024
        print(f"geladen    : {target} ({size:.0f} MB)")

    print(f"\nCheckpoint : {args.repo}")
    print("Lizenz     : CC-BY-NC-4.0 - privat nutzbar, nicht fuer Veroeffentlichung.")
    print("\nNaechster Schritt: Referenzstimmen schneiden (diarize.py).")


if __name__ == "__main__":
    main()
