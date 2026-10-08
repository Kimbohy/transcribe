# Piano · audio vers MIDI

Piano solo uniquement, moteur **ByteDance High-resolution Piano Transcription**.
Interface web minimale (HTML / CSS / JS pur) servie par FastAPI : tu déposes un audio, tu télécharges le `.mid`.

```
transcribe/
├── app/
│   ├── engine.py      # ffmpeg -> 16 kHz mono -> ByteDance -> MIDI
│   └── main.py        # API (/api/transcribe, /api/info) + sert static/
├── static/
│   ├── index.html
│   ├── style.css      # thème clair/sombre automatique
│   └── app.js
└── requirements.txt
```

## Installation (Debian 13)

```bash
# 1. Système
sudo apt update && sudo apt install -y ffmpeg libsndfile1 wget curl

# 2. Python 3.11 isolé avec uv
curl -LsSf https://astral.sh/uv/install.sh | sh     # puis ouvre un nouveau terminal
cd transcribe
uv venv --python 3.11 && source .venv/bin/activate

# 3. PyTorch (UNE des deux lignes)
uv pip install torch --index-url https://download.pytorch.org/whl/cpu   # sans GPU NVIDIA
# uv pip install torch                                                  # avec GPU NVIDIA

# 4. Dépendances
uv pip install -r requirements.txt
uv pip install --no-deps piano_transcription_inference

# 5. (Si pas déjà fait) checkpoint ~165 Mo, une seule fois
mkdir -p ~/piano_transcription_inference_data
wget -O ~/piano_transcription_inference_data/note_F1=0.9677_pedal_F1=0.9186.pth \
  "https://zenodo.org/record/4034264/files/CRNN_note_F1%3D0.9677_pedal_F1%3D0.9186.pth?download=1"
```

## Lancer

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Ouvre <http://127.0.0.1:8000>. Le modèle se charge au démarrage (quelques secondes) ; le pied de page indique CPU ou GPU.

Sans interface : `curl -F "file=@morceau.mp3" http://127.0.0.1:8000/api/transcribe -o morceau.mid`

## Notes

- Formats acceptés : tout ce que lit `ffmpeg` (mp3, wav, m4a, flac, ogg, webm…). Limite : 300 Mo.
- Un seul calcul à la fois (verrou) ; les autres requêtes attendent leur tour.
- Sur CPU, la durée de traitement dépasse celle de l'audio : la page affiche un chronomètre.
- Si le chargement du checkpoint échoue avec une erreur `weights_only`, c'est déjà géré dans `engine.py`.
- Le paquet `piano_transcription_inference` n'est pas utilisé pour charger l'audio (son `load_audio` est incompatible avec librosa récent) : `ffmpeg` s'en charge.
