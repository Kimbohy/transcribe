"""Moteur de transcription : ByteDance High-resolution Piano Transcription (piano solo)."""
import subprocess
import tempfile
import threading
from pathlib import Path

import soundfile as sf

SAMPLE_RATE = 16000          # fréquence attendue par le modèle
_lock = threading.Lock()     # un seul calcul à la fois
_model = None
_device = None


class AudioDecodeError(Exception):
    """Le fichier fourni n'est pas un audio lisible."""


def device() -> str:
    return _device or "non chargé"


def load() -> None:
    """Charge le modèle (et télécharge le checkpoint au premier lancement)."""
    global _model, _device
    if _model is not None:
        return
    import torch
    from piano_transcription_inference import PianoTranscription

    _device = "cuda" if torch.cuda.is_available() else "cpu"

    # torch >= 2.6 charge en weights_only=True par défaut. Le checkpoint officiel
    # (Zenodo) est de confiance : on lève cette restriction le temps du chargement.
    original = torch.load
    torch.load = lambda *a, **k: original(*a, **{**k, "weights_only": False})
    try:
        _model = PianoTranscription(device=_device, checkpoint_path=None)
    finally:
        torch.load = original


def _to_wav(src: str, dst: str) -> None:
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", src, "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), dst],
            check=True, capture_output=True,
        )
    except FileNotFoundError as e:
        raise RuntimeError("ffmpeg n'est pas installé (sudo apt install ffmpeg)") from e
    except subprocess.CalledProcessError as e:
        raise AudioDecodeError("Fichier audio illisible") from e


def transcribe(audio_path: str, midi_path: str) -> dict:
    """Audio quelconque -> fichier MIDI. Retourne {'notes': int, 'duration': float}."""
    with tempfile.TemporaryDirectory() as tmp:
        wav = str(Path(tmp) / "input.wav")
        _to_wav(audio_path, wav)
        audio, _ = sf.read(wav, dtype="float32")
        if audio.size == 0:
            raise AudioDecodeError("Fichier audio vide")
        with _lock:
            load()
            result = _model.transcribe(audio, midi_path)

    events = result["est_note_events"]
    return {
        "notes": len(events),
        "duration": round(audio.size / SAMPLE_RATE, 1),
    }