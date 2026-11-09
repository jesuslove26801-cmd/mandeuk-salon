# -*- coding: utf-8 -*-
"""
만득이네 - 아이들 사진 책갈피 넘김 영상

사용법:
    python make_video.py photos            # 기본 4:5 (1080x1350)
    python make_video.py photos --vertical # 세로 9:16 (1080x1920), 릴스용

photos 폴더에 jpg/png 를 넣으면 파일 이름 순서대로 넘어갑니다.
프레임을 한 장씩 그리지 않고, 사진 수만큼만 카드를 만든 뒤
ffmpeg xfade 로 이어 붙입니다 (GPU 인코딩).
"""
import os, sys, glob, subprocess, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── 설정 ──────────────────────────────────────────
HOLD      = float(os.environ.get("HOLD", 3.0))   # 사진 한 장 머무는 시간(초)
TURN      = float(os.environ.get("TURN", 0.6))   # 넘어가는 시간(초)
MUSIC     = os.environ.get("MUSIC", "")          # 얹을 노래 파일
FPS       = 30
BG        = (247, 250, 248)     # 연한 민트 크림
CARD      = (255, 255, 255)
ACCENT    = (83, 208, 190)      # 로고 민트 #53d0be
ACCENT_D  = (42, 157, 139)
INK       = (36, 49, 46)
SUB       = (125, 140, 136)
NOTCH     = 46      # 책갈피 홈 깊이(px)
FONT_B    = r"C:\Windows\Fonts\malgunbd.ttf"
FONT_R    = r"C:\Windows\Fonts\malgun.ttf"


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def check_bg(W, H):
    """크림 바탕 + 아주 옅은 체크 무늬 (링크 페이지와 같은 톤)"""
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im, "RGBA")
    step = int(W / 24)
    for x in range(0, W, step):
        d.line([(x, 0), (x, H)], fill=ACCENT + (16,), width=2)
    for y in range(0, H, step):
        d.line([(0, y), (W, y)], fill=ACCENT + (16,), width=2)
    return im


def cover(img, w, h):
    """비율 유지하며 가운데를 채워 자르기 (사진 변형 없음)"""
    sw, sh = img.size
    s = max(w / sw, h / sh)
    nw, nh = int(math.ceil(sw * s)), int(math.ceil(sh * s))
    img = img.resize((nw, nh), Image.LANCZOS)
    return img.crop(((nw - w) // 2, (nh - h) // 2, (nw - w) // 2 + w, (nh - h) // 2 + h))


def bookmark_mask(w, h, r=40, notch=NOTCH):
    """아래쪽이 V자로 파인 책갈피 모양 마스크"""
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
    # 아래 V 홈 파내기
    d.polygon([(w // 2, h - notch), (w, h), (w, h + 10), (0, h + 10), (0, h)], fill=0)
    d.polygon([(0, h - 1), (w // 2, h - notch), (w, h - 1), (w, h), (0, h)], fill=0)
    # 다시 책갈피 모양으로: 아래 모서리 두 곳은 남기고 가운데만 파기
    m2 = Image.new("L", (w, h), 0)
    d2 = ImageDraw.Draw(m2)
    d2.rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
    d2.polygon([(0, h), (w // 2, h - notch), (w, h), (w, h), (0, h)], fill=0)
    return m2


def paw(d, cx, cy, s, color):
    """발바닥 그리기 (s = 크기 기준값)"""
    d.ellipse([cx - s*1.5, cy - s*1.6, cx - s*0.5, cy - s*0.2], fill=color)
    d.ellipse([cx - s*0.4, cy - s*1.8, cx + s*0.6, cy - s*0.4], fill=color)
    d.ellipse([cx + s*0.7, cy - s*1.5, cx + s*1.7, cy - s*0.1], fill=color)
    d.ellipse([cx - s*0.9, cy - s*0.3, cx + s*1.3, cy + s*1.5], fill=color)


def make_card(src, W, H, idx, total):
    """사진 한 장 -> 책갈피 카드 한 장면"""
    base = check_bg(W, H)

    margin_x = int(W * 0.09)
    top = int(H * 0.13)
    bottom = int(H * 0.09)
    cw = W - margin_x * 2
    ch = H - top - bottom

    photo = Image.open(src).convert("RGB")
    card = Image.new("RGB", (cw, ch), CARD)

    if os.path.basename(src).lower().startswith("brand"):
        # 로고는 잘리면 안 되니 가운데에 통째로 올린다 (표지).
        # 카드 바탕을 로고 모서리 색으로 맞춰야 네모 자국이 안 보인다.
        card = Image.new("RGB", (cw, ch), photo.getpixel((2, 2)))
        side = int(cw * 0.74)
        logo = photo.resize((side, side), Image.LANCZOS)
        card.paste(logo, ((cw - side) // 2, (ch - NOTCH - side) // 2))
    else:
        card.paste(cover(photo, cw, ch - NOTCH), (0, 0))

    mask = bookmark_mask(cw, ch)

    # 그림자
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shm = Image.new("L", (W, H), 0)
    shm.paste(mask, (margin_x, top + 10))
    shm = shm.filter(ImageFilter.GaussianBlur(18))
    sh.putalpha(shm.point(lambda v: int(v * 0.22)))
    base = Image.alpha_composite(base.convert("RGBA"), sh).convert("RGB")

    base.paste(card, (margin_x, top), mask)

    # 윗쪽 리본
    d = ImageDraw.Draw(base)
    rw, rh = int(W * 0.035), int(H * 0.055)
    rx = margin_x + int(cw * 0.07)
    d.polygon([(rx, 0), (rx + rw, 0), (rx + rw, rh),
               (rx + rw // 2, rh - rw // 2), (rx, rh)], fill=ACCENT)

    # 상단 글자 (이모지는 글꼴에 없어 네모로 깨지므로 발바닥은 직접 그린다)
    fb = font(FONT_B, int(H * 0.030))
    fr = font(FONT_R, int(H * 0.020))
    ty = int(H * 0.055)
    title = "만득이네"
    tw = d.textlength(title, font=fb)
    d.text((W // 2 + int(H * 0.012), ty), title, font=fb, fill=INK, anchor="mm")
    paw(d, W // 2 - tw // 2 - int(H * 0.022), ty, int(H * 0.011), ACCENT)
    d.text((W // 2, int(H * 0.088)), "평리동 애견미용실", font=fr, fill=SUB, anchor="mm")

    # 쪽 번호
    fp = font(FONT_R, int(H * 0.018))
    d.text((W // 2, H - int(bottom * 0.42)), f"{idx} / {total}", font=fp, fill=SUB, anchor="mm")
    return base


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    folder = sys.argv[1]
    vertical = "--vertical" in sys.argv
    W, H = (1080, 1920) if vertical else (1080, 1350)

    pics = []
    for ext in ("jpg", "jpeg", "png", "webp", "JPG", "PNG"):
        pics += glob.glob(os.path.join(folder, f"*.{ext}"))
    # logo.jpg 는 p01.jpg 와 같은 사진이라 뺀다 (brand.png = 로고, 맨 앞 표지로 쓴다)
    skip = {"logo.jpg"}
    pics = sorted({p for p in pics if os.path.basename(p).lower() not in skip})
    if not pics:
        print(f"[!] {folder} 안에 사진이 없습니다."); return
    print(f"사진 {len(pics)}장")

    work = os.path.join(folder, "_cards")
    os.makedirs(work, exist_ok=True)
    cards = []
    for i, p in enumerate(pics, 1):
        out = os.path.join(work, f"c{i:03d}.png")
        make_card(p, W, H, i, len(pics)).save(out)
        cards.append(out)
        print(f"  카드 {i}/{len(pics)}  {os.path.basename(p)}")

    # ffmpeg xfade 사슬 (책장 넘기듯 위로)
    seg = HOLD + TURN
    cmd = ["ffmpeg", "-y"]
    for c in cards:
        cmd += ["-loop", "1", "-t", f"{seg:.3f}", "-i", c]

    fc, prev, t = [], "0:v", 0.0
    for i in range(1, len(cards)):
        off = t + HOLD
        lbl = f"x{i}"
        fc.append(f"[{prev}][{i}:v]xfade=transition=slideup:duration={TURN}:offset={off:.3f}[{lbl}]")
        prev, t = lbl, off
    if len(cards) == 1:
        fc.append("[0:v]null[xo]"); prev = "xo"

    fc.append(f"[{prev}]format=yuv420p,fps={FPS}[v]")
    total = t + TURN + HOLD            # 영상 전체 길이
    out_mp4 = os.path.join(os.path.dirname(os.path.abspath(folder)) or ".",
                           "만득이네_아이들_책갈피.mp4")

    amap = []
    if MUSIC and os.path.exists(MUSIC):
        cmd += ["-i", MUSIC]
        ai = len(cards)                # 노래는 마지막 입력
        fc.append(f"[{ai}:a]atrim=0:{total:.2f},asetpts=N/SR/TB,"
                  f"afade=t=out:st={max(0, total - 1.6):.2f}:d=1.6,"
                  f"loudnorm=I=-16:TP=-1.5:LRA=11[a]")
        amap = ["-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-shortest"]
        print(f"노래 얹음: {os.path.basename(MUSIC)}  ({total:.1f}초)")

    cmd += ["-filter_complex", ";".join(fc), "-map", "[v]"] + amap + [
            "-c:v", "h264_nvenc", "-preset", "p5", "-cq", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_mp4]

    print("영상 만드는 중...")
    r = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    if r.returncode != 0:
        print("[NVENC 실패 → CPU로 재시도]")
        cmd[cmd.index("h264_nvenc")] = "libx264"
        r = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    if r.returncode != 0:
        print(r.stderr[-2500:]); return
    print("완성:", out_mp4)


if __name__ == "__main__":
    main()
