# llm.py
# Cliente mínimo para un modelo abierto corriendo en Ollama (por defecto qwen2.5:7b, en la laptop).
# Pide salidas estructuradas: se le pasa un JSON Schema y Ollama obliga al modelo a respetarlo.
import json
import os

import requests

OLLAMA = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODELO = os.getenv("OLLAMA_MODELO", "qwen2.5:7b")


def preguntar(sistema: str, usuario: str, esquema: dict, contexto: int = 4096, temperatura: float = 0.0) -> dict:
    r = requests.post(f"{OLLAMA}/api/chat", timeout=600, json={
        "model": MODELO,
        "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}],
        "format": esquema,
        "stream": False,
        # qwen3 "piensa" en voz alta antes de responder (3 a 5 veces más lento); para leer proyectos no hace falta
        **({"think": False} if MODELO.startswith("qwen3") else {}),
        "options": {"temperature": temperatura, "num_ctx": contexto},
    })
    r.raise_for_status()
    return json.loads(r.json()["message"]["content"])
