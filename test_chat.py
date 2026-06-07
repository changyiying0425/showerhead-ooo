"""
蓮蓬頭 互動文字測試
直接打字跟蓮蓬頭對話，不接 Arduino、不播 TTS、不需要硬體。
用來快速測試 system prompt 改動後的語氣、字數、多元性、模板收斂等問題。

用法：
    python test_chat.py

指令：
    /reset   清除對話記憶（模擬 HANG，重新開始一輪）
    /quit    離開
"""

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv("key.env", override=True)

import main

print("=" * 56)
print("  蓮蓬頭 互動文字測試（純文字，無 TTS / 無硬體）")
print("  指令：/reset 清除對話記憶　/quit 離開")
print("=" * 56)
print()

while True:
    try:
        user_input = input("你：").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        break

    if not user_input:
        continue
    if user_input in ("/quit", "/exit"):
        break
    if user_input == "/reset":
        main.conversation_history.clear()
        main.easter_egg_count = 0
        print("（已清除對話記憶，模擬掛回重置）\n")
        continue

    reply = main.ask_gemini(user_input, use_history=True)
    if reply is None:
        print("（Gemini 沒有回應，可能是 API 問題）\n")
        continue

    # 模擬 respond() 內的 anti-repeat / 彩蛋追蹤狀態更新
    main.recent_responses.append(reply)
    if len(main.recent_responses) > main.MAX_RECENT:
        main.recent_responses.pop(0)
    if main._is_easter_egg(reply):
        main.easter_egg_count += 1
        print(f"[彩蛋觸發 {main.easter_egg_count}/1]")

    print(f"蓮蓬頭：{reply}　（{len(reply)}字）\n")
