"""Moteurs audio -> MIDI. Chaque fonction : (chemin_audio, chemin_midi_sortie) -> None."""
import subprocess
import tempfile
import threading
from pathlib import Path

import numpy as np
import soundfile as sf

_lock = threading.Lock()          # un seul calcul à la fois (modèles non thread-safe)
_bytedance_model = None


def to_wav(src: str, sr: int, dst: str) -> None:
    """Convertit n'importe quel audio en WAV mono au sample rate demandé."""
    subprocess.run(
        ["ffmpeg", "-y", "-i", src, "-ac", "1", "-ar", str(sr), dst],
        check=True, capture_output=True,
    )


def _load_bytedance():
    global _bytedance_model
    if _bytedance_model is None:
        import torch
        from piano_transcription_inference import PianoTranscription

        device = "cuda" if torch.cuda.is_available() else "cpu"

        # Les torch récents (>= 2.6) chargent en weights_only=True par défaut.
        # Le checkpoint officiel ByteDance (Zenodo) est de confiance : on désactive
        # cette restriction uniquement le temps du chargement, si nécessaire.
        orig_load = torch.load
        torch.load = lambda *a, **k: orig_load(*a, **{**k, "weights_only": False})
        try:
            _bytedance_model = PianoTranscription(device=device, checkpoint_path=None)
        finally:
            torch.load = orig_load
    return _bytedance_model


def transcribe_bytedance(audio_path: str, midi_path: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        wav = str(Path(tmp) / "in16k.wav")
        to_wav(audio_path, 16000, wav)             # le modèle attend du 16 kHz
        audio, _ = sf.read(wav, dtype="float32")   # (n_samples,)
        with _lock:
            _load_bytedance().transcribe(audio, midi_path)


def transcribe_basic_pitch(audio_path: str, midi_path: str) -> None:
    from basic_pitch.inference import predict

    with tempfile.TemporaryDirectory() as tmp:
        wav = str(Path(tmp) / "in.wav")
        to_wav(audio_path, 44100, wav)
        with _lock:
            _, midi_data, _ = predict(wav)         # midi_data : objet pretty_midi
        midi_data.write(midi_path)


ENGINES = {
    "bytedance": transcribe_bytedance,
    "basic_pitch": transcribe_basic_pitch,
}