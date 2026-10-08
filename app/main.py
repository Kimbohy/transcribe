import re
import shutil
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

from . import engine

MAX_BYTES = 300 * 1024 * 1024
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    engine.load()          # le premier chargement peut télécharger ~165 Mo
    yield


app = FastAPI(title="Gospel · audio vers MIDI", lifespan=lifespan)


@app.get("/api/info")
def info():
    return {"engine": "ByteDance Piano Transcription", "device": engine.device()}


@app.post("/api/transcribe")
def transcribe(file: UploadFile = File(...)):
    tmp = Path(tempfile.mkdtemp(prefix="gospel_"))

    def cleanup():
        shutil.rmtree(tmp, ignore_errors=True)

    try:
        suffix = re.sub(r"[^A-Za-z0-9.]", "", Path(file.filename or "").suffix)[:10] or ".audio"
        src = tmp / f"input{suffix}"
        size = 0
        with open(src, "wb") as out_file:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise HTTPException(413, "Fichier trop volumineux (300 Mo maximum)")
                out_file.write(chunk)

        midi = tmp / "result.mid"
        stats = engine.transcribe(str(src), str(midi))
    except HTTPException:
        cleanup()
        raise
    except engine.AudioDecodeError as e:
        cleanup()
        raise HTTPException(400, str(e))
    except Exception as e:
        cleanup()
        raise HTTPException(500, f"Échec de la transcription : {e}")

    return FileResponse(
        midi,
        media_type="audio/midi",
        filename="result.mid",
        headers={"X-Notes": str(stats["notes"]), "X-Duration": str(stats["duration"])},
        background=BackgroundTask(cleanup),
    )


# Toujours en dernier : sert l'interface (static/index.html) à la racine.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")