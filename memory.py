"""
蓮蓬頭記憶系統
儲存每次聽到的聲音及回應，讓蓮蓬頭能做比較。
"""

import json
import os
from datetime import datetime

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memories.json")
MAX_CONTEXT = 5  # 帶進 Gemini 的最近記憶筆數


def load_memories() -> list[dict]:
    if not os.path.exists(MEMORY_FILE):
        return []
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("memories", [])


def save_memory(context: str, sound_desc: str, response: str):
    memories = load_memories()
    memories.append({
        "id": len(memories) + 1,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "context": context,
        "sound_desc": sound_desc,
        "response": response,
    })
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump({"memories": memories}, f, ensure_ascii=False, indent=2)


def build_memory_context() -> str:
    memories = load_memories()
    if not memories:
        return ""
    recent = memories[-MAX_CONTEXT:]
    lines = ["你聽過這些聲音，這是你的記憶："]
    for m in recent:
        lines.append(f"- 在{m['context']}：{m['sound_desc']}，你說：「{m['response']}」")
    return "\n".join(lines)
