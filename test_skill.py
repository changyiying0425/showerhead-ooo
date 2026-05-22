# -*- coding: utf-8 -*-
"""測試新 Skill 文件的 Gemini 回應品質"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv('key.env', override=True)

ANCHOR = (
    "（強制規則：回應必須在3到16個中文字之間，超過16字就重新生成更短的版本。"
    "句尾不加句號。"
    "若對方說英文，只能回「I'm fine, thank you. And you？」"
    "或「My English is not very good.」或「Thank you very much.」不得使用其他英文。"
    "不重複上一句句型。）"
)

with open('skill.md', encoding='utf-8') as f:
    raw = f.read()
    start = raw.find('## SYSTEM PROMPT') + len('## SYSTEM PROMPT')
    PROMPT = raw[start:].strip()

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY', ''))

tests = [
    ('唱歌',     '你現在感受到：有人在唱歌，普通，中等音調'),
    ('哭聲',     '你現在感受到：有人在哭，很大聲，低沉'),
    ('你是誰',   '你是誰？'),
    ('快樂嗎',   '你快樂嗎？'),
    ('名字',     '你有沒有名字？'),
    ('安靜',     '四周很安靜，好一陣子了。說一句自言自語。'),
    ('藝術品',   '你是藝術品嗎？'),
    ('英文1',    'What is your name?'),
    ('英文2',    'Hello, can you speak English?'),
    ('取名字',   '我想幫你取名字叫小水滴'),
    ('蓮蓬',     '你有看過蓮蓬嗎？'),
]

print('=' * 55)
for label, t in tests:
    msg = f'{ANCHOR}\n{t}'
    try:
        resp = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=msg,
            config=types.GenerateContentConfig(system_instruction=PROMPT),
        )
        ans = resp.text.strip()
        length = len(ans)
        flag = ' ⚠️ 超字' if length > 16 else (' ⚠️ 過短' if length < 3 else ' ✅')
        print(f'[{label}]')
        print(f'  問：{t}')
        print(f'  答：{ans}  [{length}字]{flag}')
        print('-' * 40)
    except Exception as e:
        print(f'錯誤：{e}')
