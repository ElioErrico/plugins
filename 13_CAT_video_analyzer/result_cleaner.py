import json


def clean_result_payload(result):
    try:
        payload = json.loads(result) if isinstance(result, str) else result
    except json.JSONDecodeError:
        return result

    if not isinstance(payload, dict):
        return result

    source = payload.get("result") if isinstance(payload.get("result"), dict) else payload
    analysis = source.get("analysis") if isinstance(source.get("analysis"), dict) else {}
    transcript = analysis.get("transcript")
    cleaned = {}
    cleaned_analysis = {}

    job_id = payload.get("job_id") or source.get("job_id")
    if job_id:
        cleaned["job_id"] = job_id

    if analysis.get("frame_analyses") is not None:
        cleaned_analysis["frame_analyses"] = analysis["frame_analyses"]

    if isinstance(transcript, dict) and transcript.get("text"):
        cleaned_analysis["transcript"] = transcript["text"]
    elif isinstance(transcript, str) and transcript:
        cleaned_analysis["transcript"] = transcript

    if analysis.get("video_description") is not None:
        cleaned_analysis["video_description"] = analysis["video_description"]

    cleaned["analysis"] = cleaned_analysis
    return cleaned


def clean_result_string(result):
    cleaned = clean_result_payload(result)
    if isinstance(cleaned, str):
        return cleaned
    return json.dumps(cleaned, ensure_ascii=False, indent=2)
