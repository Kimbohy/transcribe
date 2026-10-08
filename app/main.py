import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from .engines import ENGINES

app = FastAPI(title="Gospel transcribe")


@app.post("/transcribe")
def transcribe(file: UploadFile = File(...), engine: str = "bytedance"):
    if engine not in ENGINES:
        raise HTTPException(400, f"engine doit être parmi {list(ENGINES)}")

    tmp = Path(tempfile.mkdtemp())
    src = tmp / (Path(file.filename or "audio").name or "audio")
    with open(src, "wb") as f:
        shutil.copyfileobj(file.file, f)

    out = tmp / "result.mid"
    try:
        ENGINES[engine](str(src), str(out))
    except Exception as e:
        shutil.rmtree(tmp, ignore_errors=True)
        raise HTTPException(500, f"Échec de la transcription : {e}")

    download_name = f"{src.stem}_{engine}.mid"
    return FileResponse(
        out, media_type="audio/midi", filename=download_name,
        background=BackgroundTask(shutil.rmtree, tmp, ignore_errors=True),
    )