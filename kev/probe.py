"""Prueba rápida de Kev-4B: manda frases a /v1/systemone e imprime la decisión.

Requiere el servidor arrancado:
  llama-server -m <Kev-4B-Q4_K_M.gguf> --host 127.0.0.1 --port 8080 -c 2048 -np 1
Uso: python3 kev/probe.py ["frase" ...]
"""
import json
import sys
import time
import urllib.request

URL = "http://127.0.0.1:8080/v1/systemone"
THRESHOLD = 0.6  # ponytail: umbral fijo, calibrar con el conjunto de prueba

ACTION_CRITERIA = {
    # Plantilla: cuándo aplica + ejemplos literales, y al final las exclusiones.
    "turn_left": "The player tells the driver to turn left right now, even insistently "
                 "(e.g. 'turn left', 'go left', 'left here', 'left now!', 'left, left, left!'). "
                 "Not when the player says NOT to turn left, and not when the turn is for later ('after the cones').",
    "turn_right": "The player tells the driver to turn right right now, even insistently "
                  "(e.g. 'turn right', 'go right', 'right here', 'right now!', 'right, right, right!'). "
                  "Not when the player says NOT to turn right, and not when the turn is for later ('after the cones').",
    # TODO(human): opción de rechazo (negaciones, ambigüedad, órdenes no soportadas)
}

QUESTIONS = {
    "action": {
        "type": "choice",
        "instructions": "The player is a passenger telling the driver what to do. "
                        "Which single driving action does the player ask for right now?",
        "criteria": ACTION_CRITERIA,
    },
}

PHRASES = [
    "turn left", "slow down a little", "don't turn right", "stop the car now",
    "brake hard", "keep going straight", "thanks, that was great",
    "no, not left, the other way", "uh what", "turn after the cones",
]


def decide(phrase):
    body = json.dumps({"state": f"Player says: {phrase}", "questions": QUESTIONS}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
    t = time.perf_counter()
    with urllib.request.urlopen(req, timeout=5) as r:
        ans = json.load(r)["answers"]["action"]
    return ans, (time.perf_counter() - t) * 1000


if __name__ == "__main__":
    for phrase in sys.argv[1:] or PHRASES:
        ans, ms = decide(phrase)
        top = sorted(ans["probabilities"].items(), key=lambda kv: -kv[1])[:3]
        action = ans["choice"] if ans["confidence"] >= THRESHOLD else "REJECTED"
        print(f"{phrase:32} {action:16} conf={ans['confidence']:.2f} {ms:4.0f}ms  "
              + " ".join(f"{k}={v:.2f}" for k, v in top))
