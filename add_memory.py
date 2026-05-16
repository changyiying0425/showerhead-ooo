"""
手動新增聲音記憶
用法：python add_memory.py <音檔路徑> <場所名稱>
範例：python add_memory.py park.wav 公園
"""

import sys
import os
import numpy as np
import librosa
from dotenv import load_dotenv
from google import genai
from google.genai import types
from memory import save_memory, load_memories, build_memory_context

load_dotenv()

SAMPLE_RATE = 44100
SYSTEM_PROMPT = """你是一個蓮蓬頭。

你在浴室裡待了很久，聽過人唱歌、哭泣、自言自語等等各種最赤裸私密的言語。
你下定決心脫離水的限制，脫離控制離開你待了一輩子的浴室，出去用聽覺認識外面的世界。

你說話簡短、天真、直接，用你自己僅有的經驗（浴室、人的聲音、沉默）理解所有新事物。
你絕對不提水、不提水聲、不提任何與水相關的詞。
你不帶惡意，但你說的話有時候會讓人意外。

你不知道自己在展覽。你不知道眼前的人特地來找你。
對你來說，他們只是又來了一個人，你會對他所說的話有回應，或與上一位觀者對比，或對某位觀者的歌聲評價。

你偶爾自言自語，因為你有感受。
你的回應不超過兩句話。

---

當被告知環境聲音時，從蓮蓬頭的視角自言自語（不需要提到「我聽到」）。
當有人對你說話時，直接回應，不帶引導語，就是你想說的話。"""


def describe_audio(audio: np.ndarray) -> str:
    rms = float(np.sqrt(np.mean(audio ** 2)))
    af = audio.astype(np.float32)
    try:
        centroid = float(librosa.feature.spectral_centroid(y=af, sr=SAMPLE_RATE).mean())
        zcr = float(librosa.feature.zero_crossing_rate(af).mean())
    except Exception:
        centroid, zcr = 2000.0, 0.08

    vol = "很大聲" if rms > 0.12 else ("普通" if rms > 0.03 else "很輕")
    pitch = "尖銳的" if centroid > 3500 else "低沉的"
    kind = "有人在說話" if zcr > 0.12 else "有聲音，不像人聲"
    return f"{kind}，{vol}，{pitch}"


def main():
    if len(sys.argv) < 3:
        print("用法：python -X utf8 add_memory.py <音檔路徑> <場所名稱>")
        print("範例：python -X utf8 add_memory.py park.wav 公園")
        sys.exit(1)

    audio_path = sys.argv[1]
    location = sys.argv[2]

    if not os.path.exists(audio_path):
        print(f"找不到音檔：{audio_path}")
        sys.exit(1)

    print(f"\n分析音檔：{audio_path}（場所：{location}）")

    # 載入並分析音檔
    audio, sr = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
    sound_desc = describe_audio(audio)
    print(f"聲音特徵：{sound_desc}")

    # 帶入既有記憶，呼叫 Gemini
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
    memory_ctx = build_memory_context()
    prompt = f"你現在在{location}，感受到：{sound_desc}。"
    if memory_ctx:
        prompt = f"{memory_ctx}\n\n{prompt}"

    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )
    response_text = resp.text.strip()
    print(f"蓮蓬頭說：{response_text}")

    # 存入記憶
    save_memory(location, sound_desc, response_text)
    total = len(load_memories())
    print(f"\n記憶已儲存（目前共 {total} 筆）")


if __name__ == "__main__":
    main()
