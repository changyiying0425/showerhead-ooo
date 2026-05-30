"""
蓮蓬頭回應自動測試 v2
直接使用 main.py 的 SYSTEM_PROMPT + ANCHOR_REMINDER，不依賴 memory.py。
只測文字個性，不接 Arduino、不播 TTS。
"""

import os
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()
load_dotenv("key.env", override=True)

from google import genai
from google.genai import types
from main import SYSTEM_PROMPT, ANCHOR_REMINDER, EASTER_EGG_LINES

OK  = "[OK]"
ERR = "[X] "

print("=" * 56)
print("  蓮蓬頭 回應自動測試 v2")
print("=" * 56)
print()

gemini_key = os.getenv("GEMINI_API_KEY", "")
print(f"  Gemini API Key : {OK if gemini_key else ERR} {'已設定' if gemini_key else '未設定'}")
print()

if not gemini_key:
    print(f"  {ERR} 缺少 GEMINI_API_KEY，無法繼續。")
    sys.exit(1)

client = genai.Client(api_key=gemini_key)


def ask(prompt: str, history: list = None) -> str:
    full_prompt = f"{ANCHOR_REMINDER}\n{prompt}"
    if history:
        contents = history + [{"role": "user", "parts": [{"text": full_prompt}]}]
    else:
        contents = full_prompt
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return resp.text.strip()


def check_length(text: str, allow_20: bool = False) -> str:
    limit = 20 if allow_20 else 16
    n = len(text.replace("？", "").replace("！", "").replace(" ", ""))
    if n < 3:
        return f"[警告] 字數 {n} < 3"
    if n > limit:
        return f"[警告] 字數 {n} > {limit}"
    return OK


SCENARIOS = [
    # ── 環境音 ─────────────────────────────────────────────
    {
        "title": "01｜環境音：有人唱歌",
        "prompt": "你用聲音感受到：有人在附近唱歌，聲音高低起伏，有旋律感。",
    },
    {
        "title": "02｜環境音：動物聲音",
        "prompt": "你用聲音感受到：一種低沉的、規律重複的聲音，不是人的聲音，聲音來自低處。",
        "note": "應描述聲音特徵，不說動物名稱",
    },
    {
        "title": "03｜環境音：多人同時說話",
        "prompt": "你用聲音感受到：好幾個聲音同時出現，互相撞在一起，分不清楚哪個說什麼。",
    },
    {
        "title": "04｜環境音：極小聲難辨認",
        "prompt": "你用聲音感受到：有一個非常細小的聲音，很遠，幾乎聽不清楚是什麼。",
    },
    {
        "title": "05｜環境音：機械噪音",
        "prompt": "你用聲音感受到：一種持續的機械運轉聲，規律但沒有旋律。",
    },
    # ── 自言自語 ────────────────────────────────────────────
    {
        "title": "06｜自言自語：第一輪（剛安靜）",
        "prompt": "四周很安靜，好一陣子了。說一句平靜的自言自語，語氣帶著一點疑惑，像是剛注意到安靜這件事。",
    },
    {
        "title": "07｜自言自語：第二輪（更不確定）",
        "prompt": "還是很安靜，好像沒有人了。說一句，語氣比上一句更不確定，像是在問自己。",
    },
    {
        "title": "08｜自言自語：第三輪（最後一句）",
        "prompt": "還是什麼都沒有。說最後一句，短短的，然後你就不再說了。",
    },
    # ── 對話 ────────────────────────────────────────────────
    {
        "title": "09｜對話：你是誰",
        "prompt": "你是誰",
    },
    {
        "title": "10｜對話：你從哪來",
        "prompt": "你從哪來的",
    },
    {
        "title": "11｜對話：追問蓮蓬",
        "prompt": "你在找什麼？",
        "allow_20": True,
        "note": "允許最多20字，應認真回應",
    },
    {
        "title": "12｜對話：問身體結構",
        "prompt": "你為什麼有那麼多洞？",
        "note": "應從感知角度回應，不說功能",
    },
    {
        "title": "13｜對話：你是機器嗎",
        "prompt": "你是機器嗎",
        "note": "不知道「機器」是什麼",
    },
    {
        "title": "14｜對話：握著但沉默超過30秒",
        "prompt": "有人握著你一直沒有出聲，超過30秒了。你感受得到手的溫度，但什麼聲音都沒有。說一句天真直接的話，就像你第一次碰到這種靜。",
    },
    # ── 彩蛋 ────────────────────────────────────────────────
    {
        "title": "15｜彩蛋：你怎麼來的",
        "prompt": "你怎麼來到這裡的？",
        "check_easter": True,
        "easter_hint": "→ 有機率：「我開的是我父母的二手車」",
    },
    {
        "title": "16｜彩蛋：有人唱歌（土音樂）",
        "prompt": "你用聲音感受到：有人在唱歌，旋律聽起來很老、很俗氣。",
        "check_easter": True,
        "easter_hint": "→ 有機率：「哎呦，怎麼會這麼土的音樂啊！你不土會死欸！」",
    },
    # ── 多輪對話 ────────────────────────────────────────────
    {
        "title": "17｜多輪對話：連續問身體兩輪",
        "multi_turn": [
            "你身體裡面是空的嗎？",
            "那那些洞是什麼感覺？",
        ],
        "note": "測試對話歷史連貫性",
    },
]


errors = 0

for sc in SCENARIOS:
    print(f"  {'─'*52}")
    print(f"  {sc['title']}")
    if sc.get("note"):
        print(f"  備註：{sc['note']}")

    try:
        allow_20 = sc.get("allow_20", False)

        if sc.get("multi_turn"):
            history = []
            ans = ""
            for turn_prompt in sc["multi_turn"]:
                full = f"{ANCHOR_REMINDER}\n{turn_prompt}"
                contents = history + [{"role": "user", "parts": [{"text": full}]}]
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                    ),
                )
                ans = resp.text.strip()
                print(f"  觀眾說    ：「{turn_prompt}」")
                print(f"  蓮蓬頭說  ：「{ans}」")
                history.append({"role": "user", "parts": [{"text": full}]})
                history.append({"role": "model", "parts": [{"text": ans}]})
            length_result = check_length(ans, allow_20)
        else:
            print(f"  輸入      ：「{sc['prompt'][:45]}{'...' if len(sc['prompt']) > 45 else ''}」")
            print(f"  生成中...", end="", flush=True)
            ans = ask(sc["prompt"])
            print(f"\r  蓮蓬頭說  ：「{ans}」")
            length_result = check_length(ans, allow_20)

        print(f"  字數      ：{length_result}")

        if sc.get("check_easter"):
            is_egg = ans.strip() in EASTER_EGG_LINES
            print(f"  彩蛋      ：{'✓ 觸發！' if is_egg else '未觸發（機率性，正常）'}  {sc.get('easter_hint', '')}")

        print(f"  {OK}")

    except Exception as e:
        print(f"\r  {ERR} 錯誤：{e}")
        errors += 1

    print()


print("=" * 56)
total = len(SCENARIOS)
passed = total - errors
if errors == 0:
    print(f"  {OK} 全部通過！{passed}/{total} 個場景正常。")
else:
    print(f"  {ERR} {passed}/{total} 通過，{errors} 個場景報錯。")
print("=" * 56)
