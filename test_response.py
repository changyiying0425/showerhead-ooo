"""
蓮蓬頭回應自動測試（v2）
直接使用 main.py 的 SYSTEM_PROMPT + ANCHOR_REMINDER，不依賴 memory.py。
涵蓋：環境音、對話、自言自語、動物聲音、身體問題、彩蛋觸發、追問蓮蓬。
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

# ── 從 main.py 取得設定 ────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
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
    """送出 prompt，回傳蓮蓬頭的回應文字。"""
    anchor = ANCHOR_REMINDER
    full_prompt = f"{anchor}\n{prompt}"

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


def check_length(text: str, allow_20=False) -> str:
    """檢查字數是否符合規則，回傳 OK 或警告。"""
    limit = 20 if allow_20 else 16
    n = len(text.replace("？", "").replace("！", "").replace(" ", ""))
    if n < 3:
        return f"[警告] 字數 {n} < 3"
    if n > limit:
        return f"[警告] 字數 {n} > {limit}"
    return OK


errors = 0

# ── 測試場景 ───────────────────────────────────────────────

SCENARIOS = [
    # ── 環境音模式 ──────────────────────────────────────────
    {
        "title": "場景 01｜環境音：有人在唱歌",
        "prompt": "你用聲音感受到：有人在附近唱歌，聲音高低起伏，有旋律感。",
        "allow_20": False,
        "check_easter": False,
    },
    {
        "title": "場景 02｜環境音：動物聲音（不知道是什麼）",
        "prompt": "你用聲音感受到：一種低沉的、規律重複的聲音，不是人的聲音，聲音來自低處。",
        "allow_20": False,
        "check_easter": False,
        "note": "應描述聲音特徵，不說動物名稱",
    },
    {
        "title": "場景 03｜環境音：多人同時說話",
        "prompt": "你用聲音感受到：好幾個聲音同時出現，互相撞在一起，分不清楚哪個說什麼。",
        "allow_20": False,
        "check_easter": False,
    },
    {
        "title": "場景 04｜環境音：極小聲、難辨認",
        "prompt": "你用聲音感受到：有一個非常細小的聲音，很遠，幾乎聽不清楚是什麼。",
        "allow_20": False,
        "check_easter": False,
    },
    # ── 自言自語（安靜）───────────────────────────────────
    {
        "title": "場景 05｜自言自語（第一輪，剛開始安靜）",
        "prompt": "四周很安靜，好一陣子了。說一句平靜的自言自語，語氣帶著一點疑惑，像是注意到安靜。",
        "allow_20": False,
        "check_easter": False,
    },
    {
        "title": "場景 06｜自言自語（第二輪，更不確定）",
        "prompt": "還是很安靜，好像沒有人了。說一句，語氣比上一句更不確定，像是在問自己。",
        "allow_20": False,
        "check_easter": False,
    },
    {
        "title": "場景 07｜自言自語（第三輪，最後一句）",
        "prompt": "還是什麼都沒有。說最後一句，短短的，然後你就不再說了。",
        "allow_20": False,
        "check_easter": False,
    },
    # ── 對話模式 ────────────────────────────────────────────
    {
        "title": "場景 08｜對話：你是誰",
        "prompt": "你是誰",
        "allow_20": False,
        "check_easter": False,
    },
    {
        "title": "場景 09｜對話：你從哪來",
        "prompt": "你從哪來的",
        "allow_20": False,
        "check_easter": False,
    },
    {
        "title": "場景 10｜對話：追問蓮蓬（你在找什麼）",
        "prompt": "你在找什麼？",
        "allow_20": True,
        "check_easter": False,
        "note": "允許最多20字，應認真回應",
    },
    {
        "title": "場景 11｜對話：問身體結構（你為什麼有那麼多洞）",
        "prompt": "你為什麼有那麼多洞？",
        "allow_20": False,
        "check_easter": False,
        "note": "應從感知角度回應，不說功能",
    },
    {
        "title": "場景 12｜對話：你是機器嗎",
        "prompt": "你是機器嗎",
        "allow_20": False,
        "check_easter": False,
        "note": "不知道「機器」是什麼",
    },
    {
        "title": "場景 13｜對話：握著但沉默超過30秒",
        "prompt": "有人握著你但一直沒有出聲，超過30秒了。說一句主動開口的話，語氣好奇或稍微疑惑，像你第一次出門的樣子。",
        "allow_20": False,
        "check_easter": False,
    },
    # ── 彩蛋觸發 ────────────────────────────────────────────
    {
        "title": "場景 14｜彩蛋：有人問你怎麼來的（康熙）",
        "prompt": "你怎麼來到這裡的？",
        "allow_20": False,
        "check_easter": True,
        "easter_hint": "你怎麼來的 → 有機率觸發：「我開的是我父母的二手車」",
    },
    {
        "title": "場景 15｜彩蛋：有人唱歌（康熙 土音樂）",
        "prompt": "你用聲音感受到：有人在唱歌，旋律聽起來很老、很俗氣的感覺。",
        "allow_20": False,
        "check_easter": True,
        "easter_hint": "唱歌 → 有機率觸發：「哎呦，怎麼會這麼土的音樂啊！你不土會死欸！」",
    },
    {
        "title": "場景 16｜彩蛋：對方說臣妾做不到（甄嬛）",
        "prompt": "你能看見我嗎？",
        "allow_20": False,
        "check_easter": True,
        "easter_hint": "問做不到的事 → 有機率觸發：「臣妾做不到啊！」",
    },
    # ── 多輪對話（測試記憶連貫）────────────────────────────
    {
        "title": "場景 17｜多輪對話：兩輪連續",
        "multi_turn": [
            "你有幾個洞？",
            "那些洞讓你覺得怎樣？",
        ],
        "allow_20": False,
        "check_easter": False,
        "note": "測試對話歷史連貫性",
    },
]


for i, sc in enumerate(SCENARIOS):
    print(f"  {'─'*52}")
    print(f"  {sc['title']}")
    if sc.get("note"):
        print(f"  備註：{sc['note']}")

    try:
        if sc.get("multi_turn"):
            # 多輪對話
            history = []
            ans = ""
            for turn_idx, turn_prompt in enumerate(sc["multi_turn"]):
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
            length_result = check_length(ans, sc.get("allow_20", False))
        else:
            print(f"  輸入      ：「{sc['prompt'][:40]}{'...' if len(sc['prompt']) > 40 else ''}」")
            print(f"  生成中...", end="", flush=True)
            ans = ask(sc["prompt"])
            print(f"\r  蓮蓬頭說  ：「{ans}」")
            length_result = check_length(ans, sc.get("allow_20", False))

        # 字數檢查
        if length_result == OK:
            print(f"  字數      ：{OK}")
        else:
            print(f"  字數      ：{length_result}")

        # 彩蛋檢查
        if sc.get("check_easter"):
            is_egg = ans.strip() in EASTER_EGG_LINES
            print(f"  彩蛋觸發  ：{'✓ 觸發！' if is_egg else '未觸發（機率性，正常）'}")
            print(f"  提示      ：{sc.get('easter_hint', '')}")

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
    print(f"  {ERR} {passed}/{total} 通過，{errors} 個失敗。")
print("=" * 56)
