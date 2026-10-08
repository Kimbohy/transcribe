(() => {
  "use strict";

  const MAX_BYTES = 300 * 1024 * 1024;

  const $ = (id) => document.getElementById(id);
  const card = $("card");
  const drop = $("drop");
  const input = $("file");
  const fileName = $("file-name");
  const fileSize = $("file-size");
  const player = $("player");
  const goBtn = $("go");
  const resetBtn = $("reset");
  const status = $("status");
  const stats = $("result-stats");
  const download = $("download");
  const foot = $("foot");

  let file = null;
  let audioUrl = null;
  let midiUrl = null;
  let timer = null;

  const setState = (s) => {
    card.dataset.state = s;
  };

  const setStatus = (text, kind = "") => {
    status.textContent = text;
    status.className = kind;
  };

  const formatSize = (bytes) =>
    bytes >= 1048576
      ? (bytes / 1048576).toFixed(1) + " Mo"
      : Math.max(1, Math.round(bytes / 1024)) + " Ko";

  const formatTime = (sec) => {
    const m = Math.floor(sec / 60);
    const s = Math.round(sec % 60);
    return m ? `${m} min ${String(s).padStart(2, "0")} s` : `${s} s`;
  };

  const revoke = () => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    if (midiUrl) URL.revokeObjectURL(midiUrl);
    audioUrl = midiUrl = null;
  };

  const reset = () => {
    clearInterval(timer);
    revoke();
    file = null;
    input.value = "";
    player.removeAttribute("src");
    player.load();
    setStatus("");
    setState("idle");
  };

  const pick = (f) => {
    if (!f) return;
    if (f.size > MAX_BYTES) {
      reset();
      setStatus("Fichier trop volumineux (300 Mo maximum).", "error");
      return;
    }
    revoke();
    file = f;
    fileName.textContent = f.name;
    fileSize.textContent = formatSize(f.size);
    audioUrl = URL.createObjectURL(f);
    player.src = audioUrl;
    setStatus("");
    setState("ready");
  };

  const transcribe = async () => {
    if (!file) return;
    setState("working");
    goBtn.disabled = true;

    const t0 = Date.now();
    const tick = () =>
      setStatus(
        `Transcription en cours… ${formatTime((Date.now() - t0) / 1000)}`,
        "busy",
      );
    tick();
    timer = setInterval(tick, 1000);

    try {
      const body = new FormData();
      body.append("file", file);
      const res = await fetch("/api/transcribe", { method: "POST", body });

      if (!res.ok) {
        let message = "La transcription a échoué.";
        try {
          message = (await res.json()).detail || message;
        } catch (_) {}
        throw new Error(message);
      }

      const blob = await res.blob();
      if (midiUrl) URL.revokeObjectURL(midiUrl);
      midiUrl = URL.createObjectURL(blob);

      const base = file.name.replace(/\.[^.]+$/, "") || "transcription";
      download.href = midiUrl;
      download.download = base + ".mid";

      const notes = Number(res.headers.get("X-Notes"));
      const duration = Number(res.headers.get("X-Duration"));
      stats.textContent = notes
        ? `${notes.toLocaleString("fr-FR")} notes · ${formatTime(duration)} d'audio · traité en ${formatTime((Date.now() - t0) / 1000)}`
        : "Aucune note détectée.";

      setStatus("");
      setState("done");
    } catch (err) {
      setStatus(err.message || "Erreur réseau.", "error");
      setState("error");
    } finally {
      clearInterval(timer);
      goBtn.disabled = false;
    }
  };

  // Sélection du fichier : clic, clavier, glisser-déposer
  drop.addEventListener("click", () => input.click());
  drop.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      input.click();
    }
  });
  input.addEventListener("change", () => pick(input.files[0]));

  ["dragenter", "dragover"].forEach((ev) =>
    drop.addEventListener(ev, (e) => {
      e.preventDefault();
      drop.classList.add("over");
    }),
  );
  ["dragleave", "drop"].forEach((ev) =>
    drop.addEventListener(ev, (e) => {
      e.preventDefault();
      drop.classList.remove("over");
    }),
  );
  drop.addEventListener("drop", (e) => pick(e.dataTransfer.files[0]));

  // Évite que le navigateur ouvre le fichier s'il est lâché à côté de la zone
  window.addEventListener("dragover", (e) => e.preventDefault());
  window.addEventListener("drop", (e) => e.preventDefault());

  goBtn.addEventListener("click", transcribe);
  resetBtn.addEventListener("click", reset);

  // Pied de page : indique CPU / GPU
  fetch("/api/info")
    .then((r) => r.json())
    .then((i) => {
      const dev = i.device === "cuda" ? "GPU" : i.device === "cpu" ? "CPU" : "";
      foot.textContent = `Piano solo · ${i.engine}${dev ? " · " + dev : ""}`;
    })
    .catch(() => {});
})();
