import html

from fastapi import File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from cat.auth.permissions import AuthPermission, AuthResource, check_permissions
from cat.mad_hatter.decorators import endpoint

from .result_cleaner import clean_result_payload, clean_result_string
from .session_store import get_session, update_session
from .video_analyzer_client import (
    analyze_video_bytes,
    build_payload,
    create_video_job,
    delete_video_job,
    get_video_job_result,
    get_video_job_status,
)


PLUGIN_ID = "13_CAT_video_analyzer"


def _load_plugin_settings(cat):
    return cat.mad_hatter.plugins[PLUGIN_ID].load_settings()


def _build_backend_payload(settings: dict) -> dict:
    return build_payload(
        {
            "client": settings.get("client"),
            "api_key": settings.get("api_key"),
            "api_url": settings.get("api_url"),
            "model": settings.get("model"),
            "keep_frames": settings.get("keep_frames"),
        }
    )


def _tail_logs(logs, max_lines: int = 8) -> list[str]:
    if not isinstance(logs, list):
        return []
    return [str(line) for line in logs[-max_lines:]]


def _serialize_job_status(job: dict) -> dict:
    return {
        "job_id": job.get("job_id"),
        "status": job.get("status"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "logs": _tail_logs(job.get("logs")),
        "error": job.get("error"),
    }


def _cleanup_backend_job(settings: dict, job_id: str | None) -> str | None:
    if not job_id:
        return None

    try:
        delete_video_job(job_id=job_id, backend_base_url=settings.get("backend_base_url", ""))
    except HTTPException as e:
        if getattr(e, "status_code", None) == 404:
            return None
        return str(e.detail)
    except Exception as e:
        return str(e)

    return None


@endpoint.get(
    "/upload",
    prefix="/video-analyzer",
    tags=["Video Analyzer"],
    response_class=HTMLResponse,
)
def video_analyzer_upload_page(
    session_id: str | None = None,
    cat=check_permissions(AuthResource.UPLOAD, AuthPermission.WRITE),
):
    settings = _load_plugin_settings(cat)
    tool_name = settings.get("tool_name", "video_analyzer")
    session_value = html.escape(session_id or "", quote=True)

    return f"""
<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>Video Analyzer Upload</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #111827; color: #f3f4f6; }}
    .box {{ max-width: 900px; margin: 0 auto; background: #1f2937; padding: 24px; border-radius: 12px; }}
    h1 {{ margin-top: 0; }}
    label {{ display: block; margin-top: 14px; font-weight: 600; }}
    input, button {{ width: 100%; box-sizing: border-box; margin-top: 6px; padding: 10px; border-radius: 8px; border: 1px solid #374151; }}
    input {{ background: #111827; color: #f9fafb; }}
    button {{ background: #2563eb; color: white; cursor: pointer; font-weight: 600; }}
    .secondary-button {{ background: #374151; }}
    .button-row {{ display: flex; gap: 12px; margin-top: 12px; }}
    .button-row button {{ margin-top: 0; }}
    button:disabled {{ opacity: 0.7; cursor: wait; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #0b1220; padding: 16px; border-radius: 8px; border: 1px solid #374151; }}
    .muted {{ color: #9ca3af; }}
  </style>
</head>
<body>
  <div class="box">
    <h1>Video Analyzer Upload</h1>
    <p class="muted">Tool name: <strong>{tool_name}</strong></p>
    <p class="muted">Questa pagina carica un file <code>.mp4</code> direttamente al backend video analyzer senza passare dal RabbitHole.</p>

    <form id="upload-form">
      <input id="session_id" name="session_id" type="hidden" value="{session_value}" />

      <label for="file">Video MP4</label>
      <input id="file" name="file" type="file" accept=".mp4,video/mp4" required />

      <div class="button-row">
        <button id="submit-btn" type="submit">Carica e analizza</button>
        <button id="cancel-btn" class="secondary-button" type="button">Interrompi attesa</button>
      </div>
    </form>

    <label for="job-status-logs">Avanzamento analisi</label>
    <div id="job-status-text" class="muted">In attesa di upload...</div>
    <pre id="job-status-logs">Nessun log disponibile.</pre>

    <label for="result">Risultato JSON</label>
    <pre id="result">In attesa di upload...</pre>
  </div>

  <script>
    const form = document.getElementById("upload-form");
    const result = document.getElementById("result");
    const button = document.getElementById("submit-btn");
    const cancelButton = document.getElementById("cancel-btn");
    const sessionId = document.getElementById("session_id");
    const jobStatusText = document.getElementById("job-status-text");
    const jobStatusLogs = document.getElementById("job-status-logs");
    let currentRequest = null;
    let activeJobId = null;
    let pollingTimer = null;

    function renderResponse(raw, preferResult = false) {{
      try {{
        const parsed = JSON.parse(raw);
        const output = preferResult && parsed && typeof parsed === "object" && parsed.result !== undefined
          ? parsed.result
          : parsed;
        result.textContent = JSON.stringify(output, null, 2);
      }} catch (_err) {{
        result.textContent = raw;
      }}
    }}

    function setJobStatus(status, logs = []) {{
      jobStatusText.textContent = status || "In attesa di upload...";
      jobStatusLogs.textContent = logs.length ? logs.join("\\n") : "Nessun log disponibile.";
    }}

    function stopPolling() {{
      if (pollingTimer) {{
        clearInterval(pollingTimer);
        pollingTimer = null;
      }}
    }}

    function unlockUi() {{
      currentRequest = null;
      button.disabled = false;
      cancelButton.disabled = false;
    }}

    async function fetchCompletedResult() {{
      const params = new URLSearchParams({{ job_id: activeJobId }});
      if (sessionId.value) {{
        params.set("session_id", sessionId.value);
      }}

      const response = await fetch(`/video-analyzer/job-result?${{params.toString()}}`);
      const raw = await response.text();
      renderResponse(raw);
      unlockUi();
    }}

    async function pollJobStatus() {{
      if (!activeJobId) {{
        return;
      }}

      const params = new URLSearchParams({{ job_id: activeJobId }});
      if (sessionId.value) {{
        params.set("session_id", sessionId.value);
      }}

      try {{
        const response = await fetch(`/video-analyzer/job-status?${{params.toString()}}`);
        const data = await response.json();
        const status = data.status || "running";
        const logs = Array.isArray(data.logs) ? data.logs : [];
        setJobStatus(`Stato: ${{status}}`, logs);

        if (status === "completed") {{
          stopPolling();
          await fetchCompletedResult();
          setJobStatus("Stato: completed", logs);
          return;
        }}

        if (status === "failed" || status === "cancelled") {{
          stopPolling();
          result.textContent = data.error || "Analisi non completata.";
          unlockUi();
        }}
      }} catch (err) {{
        stopPolling();
        result.textContent = "Errore nel polling stato: " + err;
        setJobStatus("Errore durante il controllo dello stato.");
        unlockUi();
      }}
    }}

    form.addEventListener("submit", async (event) => {{
      event.preventDefault();
      stopPolling();
      activeJobId = null;
      button.disabled = true;
      cancelButton.disabled = true;
      result.textContent = "Invio job al backend...";
      setJobStatus("Creazione job...", []);

      try {{
        const formData = new FormData(form);
        const response = await fetch("/video-analyzer/start", {{
          method: "POST",
          body: formData
        }});

        const raw = await response.text();
        const data = JSON.parse(raw);
        activeJobId = data.job_id;
        if (data.session_id && !sessionId.value) {{
          sessionId.value = data.session_id;
        }}

        setJobStatus(`Stato: ${{data.status || "queued"}}`, Array.isArray(data.logs) ? data.logs : []);
        result.textContent = `Job creato: ${{activeJobId}}`;
        pollingTimer = setInterval(pollJobStatus, 2000);
        await pollJobStatus();
      }} catch (err) {{
        result.textContent = "Errore: " + err;
        setJobStatus("Creazione job fallita.");
        unlockUi();
      }}
    }});

    cancelButton.addEventListener("click", async () => {{
      stopPolling();

      if (!sessionId.value) {{
        result.textContent = "Nessuna sessione attiva da interrompere.";
        setJobStatus("Nessuna sessione attiva.");
        button.disabled = false;
        cancelButton.disabled = false;
        return;
      }}

      cancelButton.disabled = true;
      button.disabled = true;
      result.textContent = "Interruzione attesa in corso...";
      setJobStatus("Interruzione attesa in corso...");

      try {{
        const formData = new FormData();
        formData.append("session_id", sessionId.value);

        const response = await fetch("/video-analyzer/cancel", {{
          method: "POST",
          body: formData
        }});

        const raw = await response.text();
        renderResponse(raw);
        activeJobId = null;
        setJobStatus("Attesa interrotta.");
      }} catch (err) {{
        result.textContent = "Errore: " + err;
      }} finally {{
        unlockUi();
      }}
    }});
  </script>
</body>
</html>
"""


@endpoint.post("/cancel", prefix="/video-analyzer", tags=["Video Analyzer"])
def cancel_video_analysis(
    session_id: str | None = Form(default=None),
    cat=check_permissions(AuthResource.UPLOAD, AuthPermission.WRITE),
):
    if not session_id:
        return {"status": "error", "message": "session_id mancante"}

    session = get_session(session_id)
    if session is None:
        return {"status": "error", "message": "Sessione non trovata", "session_id": session_id}

    update_session(
        session_id,
        status="cancelled",
        error="Caricamento video analyzer interrotto dall'utente.",
        result=None,
    )

    return {
        "status": "cancelled",
        "message": "Attesa interrotta con successo.",
        "session_id": session_id,
    }


@endpoint.post("/start", prefix="/video-analyzer", tags=["Video Analyzer"])
def start_video_analysis(
    file: UploadFile = File(...),
    session_id: str | None = Form(default=None),
    cat=check_permissions(AuthResource.UPLOAD, AuthPermission.WRITE),
):
    settings = _load_plugin_settings(cat)
    session = get_session(session_id) if session_id else None

    if session_id and session and session.get("status") == "cancelled":
        return {
            "session_id": session_id,
            "status": "cancelled",
            "logs": [],
            "error": "Caricamento video analyzer interrotto.",
        }

    file_bytes = file.file.read()
    job = create_video_job(
        file_bytes=file_bytes,
        filename=file.filename,
        backend_base_url=settings.get("backend_base_url", ""),
        content_type=file.content_type or "video/mp4",
        payload=_build_backend_payload(settings),
    )
    job_id = job.get("job_id")
    if not job_id:
        raise HTTPException(status_code=502, detail="job_id mancante nella risposta del backend")

    serialized = _serialize_job_status(job)
    if session_id:
        update_session(
            session_id,
            status=serialized.get("status") or "queued",
            job_id=job_id,
            result=None,
            error=None,
        )

    return {
        "session_id": session_id,
        **serialized,
    }


@endpoint.get("/job-status", prefix="/video-analyzer", tags=["Video Analyzer"])
def video_analysis_job_status(
    job_id: str,
    session_id: str | None = None,
    cat=check_permissions(AuthResource.UPLOAD, AuthPermission.WRITE),
):
    settings = _load_plugin_settings(cat)
    job = get_video_job_status(job_id=job_id, backend_base_url=settings.get("backend_base_url", ""))
    serialized = _serialize_job_status(job)
    cleanup_error = None

    if serialized.get("status") == "failed":
        cleanup_error = _cleanup_backend_job(settings, job_id)

    if session_id:
        updates = {
            "status": serialized.get("status"),
            "job_id": job_id,
        }
        if serialized.get("status") == "failed":
            updates["error"] = serialized.get("error") or "\n".join(serialized.get("logs") or [])
            updates["job_id"] = None
            if cleanup_error:
                updates["cleanup_error"] = cleanup_error
        update_session(session_id, **updates)

    return serialized


@endpoint.get("/job-result", prefix="/video-analyzer", tags=["Video Analyzer"])
def video_analysis_job_result(
    job_id: str,
    session_id: str | None = None,
    cat=check_permissions(AuthResource.UPLOAD, AuthPermission.WRITE),
):
    settings = _load_plugin_settings(cat)
    result = get_video_job_result(job_id=job_id, backend_base_url=settings.get("backend_base_url", ""))
    payload_with_job_id = {"job_id": job_id, "result": result}
    cleaned_result = clean_result_payload(payload_with_job_id)
    cleaned_result_as_string = clean_result_string(payload_with_job_id)

    if session_id:
        update_session(
            session_id,
            status="completed",
            job_id=job_id,
            result=cleaned_result_as_string,
            error=None,
        )

    return cleaned_result

@endpoint.post("/analyze", prefix="/video-analyzer", tags=["Video Analyzer"])
def analyze_video(
    file: UploadFile = File(...),
    session_id: str | None = Form(default=None),
    cat=check_permissions(AuthResource.UPLOAD, AuthPermission.WRITE),
):
    settings = _load_plugin_settings(cat)
    session = get_session(session_id) if session_id else None

    if session_id and session and session.get("status") == "cancelled":
        return {
            "tool_name": settings.get("tool_name", "video_analyzer"),
            "filename": file.filename,
            "session_id": session_id,
            "result": None,
            "result_as_string": "Caricamento video analyzer interrotto.",
        }

    try:
        file_bytes = file.file.read()
        result, _ = analyze_video_bytes(
            file_bytes=file_bytes,
            filename=file.filename,
            backend_base_url=settings.get("backend_base_url", ""),
            content_type=file.content_type or "video/mp4",
            payload=_build_backend_payload(settings),
        )
    except Exception as e:
        if session_id:
            update_session(session_id, status="failed", error=str(e), result=None)
        raise

    cleaned_result = clean_result_payload(payload_with_job_id)
    cleaned_result_as_string = clean_result_string(payload_with_job_id)

    if session_id:
        update_session(session_id, status="completed", result=cleaned_result_as_string, error=None)
    else:
        cat.send_ws_message(cleaned_result_as_string, "chat")

    return {
        "tool_name": settings.get("tool_name", "video_analyzer"),
        "filename": file.filename,
        "session_id": session_id,
        "result": cleaned_result,
        "result_as_string": cleaned_result_as_string,
    }
