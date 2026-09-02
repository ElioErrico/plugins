# Video Analyzer - Docker How To Use

Questa guida descrive **solo** come usare il progetto con Docker.

## 1. How To Install

### Requisiti

Ti serve solo:

- Docker Desktop installato
- il file [config/config.json](file:///c:/Users/elio.errico/Desktop/Python/video-analyzer/config/config.json) configurato correttamente

FFmpeg **non va installato sul PC host** se usi Docker:

- nel container e' gia' incluso
- viene installato dentro l'immagine Docker
- quindi si', anche FFmpeg e' gia' "dockerizzato" insieme al servizio

### Configurazione minima

Nel file [config/config.json](file:///c:/Users/elio.errico/Desktop/Python/video-analyzer/config/config.json) imposta almeno:

```json
{
  "clients": {
    "default": "openai_api",
    "openai_api": {
      "api_key": "YOUR_OPENAI_API_KEY",
      "model": "gpt-4o",
      "api_url": "https://api.openai.com/v1"
    }
  }
}
```

### Avvio

Dalla root del progetto:

```bat
docker compose up --build
```

L'API sara' disponibile su:

```text
http://127.0.0.1:8000
```

### Verifica

```bat
curl http://127.0.0.1:8000/health
```

Risposta attesa:

```json
{"status":"ok"}
```

## 2. How To Use

### Configurazione usata dalle API

Le API possono funzionare in due modi:

1. usando direttamente i valori presenti in `config/config.json`
2. ricevendo override nella richiesta HTTP

Quindi si', puoi inviare **piu' configurazioni** per job diversi.

Esempi di campi che puoi passare nella request:

- `client`
- `api_key`
- `api_url`
- `model`
- `keep_frames`
- `prompt`
- `whisper_model`
- `max_frames`
- `temperature`

### Caricare un video e creare un job

Versione minima: usa la configurazione gia' presente in `config/config.json`.

```bat
curl -X POST http://127.0.0.1:8000/api/jobs ^
  -F "video=@C:\Users\elio.errico\Desktop\Python\video-analyzer\video_to_analyze.mp4"
```

La risposta contiene un `job_id`.

Versione con override espliciti: usa una configurazione specifica solo per quel job.

```bat
curl -X POST http://127.0.0.1:8000/api/jobs ^
  -F "video=@C:\Users\elio.errico\Desktop\Python\video-analyzer\video_to_analyze.mp4" ^
  -F "client=openai_api" ^
  -F "api_url=https://api.openai.com/v1" ^
  -F "model=gpt-4o" ^
  -F "keep_frames=true" ^
  -F "max_frames=1"
```

### Controllare lo stato del job

```bat
curl http://127.0.0.1:8000/api/jobs/JOB_ID
```

Stati possibili:

- `queued`
- `running`
- `completed`
- `failed`

### Ottenere il risultato JSON

```bat
curl http://127.0.0.1:8000/api/jobs/JOB_ID/result
```

### Ottenere la lista delle immagini

```bat
curl http://127.0.0.1:8000/api/jobs/JOB_ID/frames
```

### Scaricare tutto in uno zip

```bat
curl -L http://127.0.0.1:8000/api/jobs/JOB_ID/download --output result.zip
```

Lo zip contiene:

- `analysis.json`
- `job.json`
- `run.log`
- `frames/*`

### Eseguire upload + analisi in una sola chiamata

```bat
curl -X POST http://127.0.0.1:8000/api/analyze ^
  -F "video=@C:\Users\elio.errico\Desktop\Python\video-analyzer\video_to_analyze.mp4"
```

Anche qui puoi passare override nella stessa richiesta:

```bat
curl -X POST http://127.0.0.1:8000/api/analyze ^
  -F "video=@C:\Users\elio.errico\Desktop\Python\video-analyzer\video_to_analyze.mp4" ^
  -F "client=openai_api" ^
  -F "api_url=https://api.openai.com/v1" ^
  -F "model=gpt-4o" ^
  -F "keep_frames=true"
```

### Fermare il servizio

```bat
docker compose down
```
