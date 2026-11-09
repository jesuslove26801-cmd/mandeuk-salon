# -*- coding: utf-8 -*-
"""만득이네 동요 만들기 — APIMart 수노(노래, 가사 있음).

    python make_song.py          # 만들기
    python make_song.py <task_id>  # 끊긴 작업 이어받기
"""
import os, sys, time, urllib.request
sys.path.insert(0, r"D:\apimart")
from muse import UA, call

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "song")
os.makedirs(OUT, exist_ok=True)

TITLE = "만득이네 가는 날"

LYRICS = """[Verse]
만득이네 가는 날 우리 강아지 신났어요
또각또각 발톱 깎고 보글보글 거품 목욕

[Chorus]
싹둑싹둑 예쁘게 새 옷 입은 것처럼
동글동글 귀여운 우리 아이 최고예요

[Verse]
무섭지 않아 괜찮아 천천히 해 줄게요
한 번에 한 아이만 우리 아이만 봐 줄게요

[Chorus]
싹둑싹둑 예쁘게 새 옷 입은 것처럼
만득이네 만득이네 평리동 미용실
"""

STYLE = ("cute Korean nursery rhyme for kindergarten, bright and playful children's song, "
         "soft ukulele, glockenspiel, light hand claps, gentle sweet female voice, "
         "warm and friendly, simple singable melody, 100 bpm, C major")

NEG = "rock, EDM, heavy drums, distortion, dark, sad, male rap, aggressive"


def save(data, tag=""):
    n = 0
    for i, item in enumerate(data["result"]["music"]):
        p = os.path.join(OUT, f"만득이네_동요{tag}{'' if i == 0 else '_' + str(i + 1)}.wav")
        req = urllib.request.Request(item["audio_url"], headers={"User-Agent": UA})
        open(p, "wb").write(urllib.request.urlopen(req, timeout=240).read())
        print("저장:", p, item.get("duration"), "초")
        n += 1
    return n


def wait(tid):
    print("작업 번호:", tid)
    end = time.time() + 900
    while time.time() < end:
        data = call("GET", f"/music/tasks/{tid}")["data"]
        st = data.get("status")
        print("  ", st, flush=True)
        if st == "completed":
            return save(data)
        if st == "failed":
            print("실패:", (data.get("error") or {}).get("message")); return 0
        time.sleep(8)
    print("시간 초과. 이어받기:  python make_song.py", tid)
    return 0


if len(sys.argv) > 1:
    wait(sys.argv[1]); sys.exit()

res = call("POST", "/music/generations", {
    "model": "suno", "version": "v6", "custom": True, "instrumental": False,
    "title": TITLE, "prompt": LYRICS, "style": STYLE,
    "negative_tags": NEG, "duration": 180, "audio_format": "wav",
})
wait(res["data"][0]["task_id"])
