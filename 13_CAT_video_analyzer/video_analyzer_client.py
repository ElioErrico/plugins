import json
from pathlib import Path

import httpx
from fastapi import HTTPException


ALLOWED_SUFFIXES = {".mp4"}


def build_payload(payload_map: dict) -> dict:
    payload = {}
    for key, value in payload_map.items():
        if value in (None, ""):
            continue
        if isinstance(value, bool):
            payload[key] = str(value).lower()
            continue
        payload[key] = value
    return payload


def validate_video_filename(filename: str):
    suffix = Path(filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="Sono ammessi solo file .mp4")


def _build_backend_url(backend_base_url: str, path: str) -> str:
    return f"{(backend_base_url or '').rstrip('/')}{path}"


def _raise_backend_error(e: httpx.HTTPStatusError):
    detail = e.response.text or str(e)
    raise HTTPException(status_code=e.response.status_code, detail=detail)


def _parse_json_response(response: httpx.Response, invalid_json_message: str) -> dict:
    try:
        return response.json()
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=502, detail=f"{invalid_json_message}: {e}")


def create_video_job(
    file_bytes: bytes,
    filename: str,
    backend_base_url: str,
    content_type: str = "video/mp4",
    payload: dict | None = None,
    timeout: float = 300.0,
):
    validate_video_filename(filename)
    create_job_url = _build_backend_url(backend_base_url, "/api/jobs")

    try:
        response = httpx.post(
            create_job_url,
            files={"video": (filename, file_bytes, content_type or "video/mp4")},
            data=payload or {},
            timeout=timeout,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        _raise_backend_error(e)
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Errore di comunicazione col backend video analyzer: {e}",
        )

    return _parse_json_response(response, "Risposta JSON non valida dal backend")


def get_video_job_status(
    job_id: str,
    backend_base_url: str,
    timeout: float = 30.0,
):
    status_url = _build_backend_url(backend_base_url, f"/api/jobs/{job_id}")

    try:
        response = httpx.get(status_url, timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        _raise_backend_error(e)
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Errore di comunicazione col backend video analyzer: {e}",
        )

    return _parse_json_response(response, "Risposta JSON non valida dal backend")


def get_video_job_result(
    job_id: str,
    backend_base_url: str,
    timeout: float = 60.0,
):
    result_url = _build_backend_url(backend_base_url, f"/api/jobs/{job_id}/result")

    try:
        response = httpx.get(result_url, timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        _raise_backend_error(e)
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Errore di comunicazione col backend video analyzer: {e}",
        )

    return _parse_json_response(response, "Risposta JSON non valida dal backend")


def delete_video_job(
    job_id: str,
    backend_base_url: str,
    timeout: float = 30.0,
):
    delete_url = _build_backend_url(backend_base_url, f"/api/jobs/{job_id}")

    try:
        response = httpx.delete(delete_url, timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        _raise_backend_error(e)
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Errore di comunicazione col backend video analyzer: {e}",
        )


def analyze_video_bytes(
    file_bytes: bytes,
    filename: str,
    backend_base_url: str,
    content_type: str = "video/mp4",
    payload: dict | None = None,
    timeout: float = 300.0,
):
    validate_video_filename(filename)
    analyze_url = _build_backend_url(backend_base_url, "/api/analyze")

    try:
        response = httpx.post(
            analyze_url,
            files={"video": (filename, file_bytes, content_type or "video/mp4")},
            data=payload or {},
            timeout=timeout,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        _raise_backend_error(e)
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Errore di comunicazione col backend video analyzer: {e}",
        )

    result = _parse_json_response(response, "Risposta JSON non valida dal backend")

    return result, json.dumps(result, ensure_ascii=False, indent=2)
