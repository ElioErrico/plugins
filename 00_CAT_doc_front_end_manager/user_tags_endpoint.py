from cat.mad_hatter.decorators import endpoint
from fastapi import HTTPException
import json
import os
from pydantic import BaseModel
from typing import List

# Modifica cruciale: percorso alternativo per i file statici
try:
    # Prova a recuperare il percorso dalla root del progetto (Docker)
    root_dir = os.environ.get("CCAT_ROOT", os.getcwd())
    static_dir = os.path.join(root_dir, "cat/static/")
    
    # Crea i percorsi assoluti
    user_status_path = os.path.join(static_dir, "user_status.json")
    tags_path = os.path.join(static_dir, "tags.json")

except Exception as e:
    print(f"Errore nel calcolo dei percorsi: {str(e)}")
    raise

# Define a Pydantic model for the tags list
class TagsList(BaseModel):
    tags: List[str]

# Endpoint per user_status.json
@endpoint.get("/user-status")
def get_user_status():
    try:
        with open(user_status_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File user_status.json non trovato")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@endpoint.post("/user-status")
def update_user_status(new_user_status: dict):
    try:
        with open(user_status_path, "w") as f:
            json.dump(new_user_status, f, indent=4)
        return {"status": "success", "message": "tags.json aggiornato con successo"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint per tags.json
@endpoint.get("/tags")
def get_tags():
    try:
        with open(tags_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File tags.json non trovato")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"JSON non valido: {str(e)}")

@endpoint.post("/tags")
def update_tags(tags_data: TagsList):
    try:
        with open(tags_path, "w") as f:
            # Save the entire tags object instead of just the list
            json.dump({"tags": tags_data.tags}, f, indent=4)
        return {"status": "success", "message": "tags.json aggiornato con successo"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

