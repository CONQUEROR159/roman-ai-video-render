import math
import os
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont


WIDTH = 1080
HEIGHT = 1920
FPS = 18
SECONDS_PER_SCENE = 4

OUT_DIR = "out"
FRAMES_DIR = os.path.join(OUT_DIR, "frames")
VIDEO_PATH = os.path.join(OUT_DIR, "video.mp4")


def get_font(size: int, bold: bool = True):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def ease_out_cubic(x: float) -> float:
    return 1 - pow(1 - x, 3)


def extract_field(raw_text: str, field_name: str, fallback: str) -> str:
    lines = raw_text.splitlines()
    capture = False
    collected = []

    field_markers = [
        "ЗАГОЛОВОК:",
        "ЭКРАН 1:",
        "ЭКРАН 2:",
        "ЭКРАН 3:",
        "ОЗВУЧКА:",
        "ТЕКСТ ПОСТА:",
        "CTA:",
        "ВИДЕО СТИЛЬ:",
    ]

    target = field_name.upper()

    for line in lines:
        clean = line.strip()
        upper = clean.upper()

        if upper.startswith(target):
            capture = True
            value = clean.split(":", 1)[1].strip() if ":" in clean else ""
            if value:
                collected.append(value)
            continue

        if capture and any(upper.startswith(marker) for marker in field_markers):
            break

        if capture and clean:
            collected.append(clean)

    result = " ".join(collected).strip()
    return result if result else fallback


def shorten(text: str, max_len: int = 82) -> str:
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "..."


def wrap_text_by_width(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)

        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def draw_center_text(
    draw,
    text,
    font,
    center_x,
    center_y,
    max_width,
    fill=(255, 255, 255),
    shadow=True,
    line_spacing=20,
):
    lines = wrap_text_by_width(draw, text, font, max_width)

    line_heights = []
    total_height = 0

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        h = bbox[3] - bbox[1]
        line_heights.append(h)
        total_height += h + line_spacing

    total_height -= line_spacing
    y = center_y - total_height // 2

    for idx, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = center_x - w // 2

        if shadow:
            draw.text((x + 4, y + 5), line, font=font, fill=(0, 0, 0))

        draw.text((x, y), line, font=font, fill=fill)
        y += line_heights[idx] + line_spacing


def draw_rounded_panel(draw, xy, radius, fill, outline=None, width=3):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_terminal_background(draw, frame_index, scene_index):
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(6, 8, 15))

    # moving terminal grid
    grid_color = (24, 30, 48)
    shift = (frame_index * 2) % 90

    for x in range(-90, WIDTH + 90, 90):
        draw.line((x + shift, 0, x + shift, HEIGHT), fill=grid_color, width=1)

    for y in range(-90, HEIGHT + 90, 90):
        draw.line((0, y + shift, WIDTH, y + shift), fill=grid_color, width=1)

    # neon glows
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    glow_green = (20, 220, 130, 35)
    glow_red = (240, 70, 70, 25)
    glow_blue = (60, 130, 255, 22)

    pulse = int(30 * math.sin(frame_index / 12))

    od.ellipse((-180, 220 + pulse, 420, 820 + pulse), fill=glow_blue)
    od.ellipse((720, 1120 - pulse, 1320, 1720 - pulse), fill=glow_green)

    if scene_index % 2 == 0:
        od.ellipse((680, 230, 1260, 820), fill=glow_red)

    base = Image.alpha_composite(draw.im.convert("RGBA"), overlay)
    draw.im.paste(base.convert("RGB"))

    # fake animated candle chart
    green = (20, 220, 130)
    red = (240, 70, 70)
    muted_green = (12, 110, 75)
    muted_red = (130, 40, 45)

    base_y = 1350 + int(25 * math.sin(frame_index / 18))
    x = 60 - (frame_index * 3 % 80)

    candles = [
        (54, -90, green),
        (54, 80, red),
        (54, -130, green),
        (54, -50, green),
        (54, 120, red),
        (54, -170, green),
        (54, 60, red),
        (54, -80, green),
        (54, -140, green),
        (54, 110, red),
        (54, -180, green),
        (54, -60, green),
        (54, 90, red),
        (54, -120, green),
        (54, 70, red),
    ]

    y = base_y

    for i, (w, move, color) in enumerate(candles):
        open_y = y
        close_y = y + move
        high_y = min(open_y, close_y) - 45
        low_y = max(open_y, close_y) + 45

        current_x = x + i * 76
        if current_x < -70 or current_x > WIDTH + 70:
            y = close_y
            continue

        cx = current_x + w // 2

        wick_color = color
        body_color = color

        if current_x < 80:
            wick_color = muted_green if color == green else muted_red
            body_color = wick_color

        draw.line((cx, high_y, cx, low_y), fill=wick_color, width=5)

        top = min(open_y, close_y)
        bottom = max(open_y, close_y)

        draw.rounded_rectangle(
            (current_x, top, current_x + w, bottom),
            radius=8,
            fill=body_color,
        )

        y = close_y

    # price line
    price_y = 1135 + int(18 * math.sin(frame_index / 15))
    draw.line((70, price_y, WIDTH - 70, price_y), fill=(20, 220, 130), width=2)
    draw.rounded_rectangle((770, price_y - 30, WIDTH - 70, price_y + 30), radius=18, fill=(20, 220, 130))
    draw.text((795, price_y - 22), "LIVE MARKET", font=get_font(30), fill=(5, 10, 16))


def draw_top_badges(draw, post_id):
    badge_font = get_font(34)

    draw_rounded_panel(
        draw,
        (60, 72, 510, 145),
        radius=28,
        fill=(15, 22, 38),
        outline=(38, 56, 82),
        width=2,
    )
    draw.text((88, 92), "LIVE TRADING", font=badge_font, fill=(20, 220, 130))

    draw_rounded_panel(
        draw,
        (660, 72, WIDTH - 60, 145),
        radius=28,
        fill=(15, 22, 38),
        outline=(38, 56, 82),
        width=2,
    )
    draw.text((690, 92), post_id[:18], font=badge_font, fill=(255, 255, 255))


def draw_progress(draw, scene_index, total_scenes, local_progress):
    bar_x = 70
    bar_y = 1590
    bar_w = WIDTH - 140
    bar_h = 16

    draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), radius=8, fill=(38, 46, 68))

    full_progress = (scene_index + local_progress) / total_scenes
    filled = int(bar_w * full_progress)

    draw.rounded_rectangle((bar_x, bar_y, bar_x + filled, bar_y + bar_h), radius=8, fill=(20, 220, 130))


def draw_scene(frame_index, scene_index, total_scenes, label, text, post_id):
    img = Image.new("RGB", (WIDTH, HEIGHT), (6, 8, 15))
    draw = ImageDraw.Draw(img)

    draw_terminal_background(draw, frame_index, scene_index)
    draw_top_badges(draw, post_id)

    frames_per_scene = FPS * SECONDS_PER_SCENE
    local_frame = frame_index % frames_per_scene
    local_progress = local_frame / max(frames_per_scene - 1, 1)
    eased = ease_out_cubic(local_progress)

    accent = (20, 220, 130)
    if scene_index == 0:
        accent = (255, 255, 255)
    elif scene_index == 2:
        accent = (255, 74, 74)
    elif scene_index == total_scenes - 1:
        accent = (20, 220, 130)

    # label
    label_font = get_font(38)
    draw_rounded_panel(
        draw,
        (70, 250, 450, 318),
        radius=30,
        fill=(18, 24, 38),
        outline=accent,
        width=3,
    )
    draw.text((100, 268), label.upper(), font=label_font, fill=accent)

    # main animated panel
    panel_y = int(420 + (1 - eased) * 90)
    panel_bottom = panel_y + 600

    draw_rounded_panel(
        draw,
        (60, panel_y, WIDTH - 60, panel_bottom),
        radius=54,
        fill=(12, 17, 31),
        outline=(42, 54, 82),
        width=3,
    )

    # inner accent line
    draw.rounded_rectangle(
        (88, panel_y + 28, 105, panel_bottom - 28),
        radius=8,
        fill=accent,
    )

    # big text
    text_font_size = 82 if scene_index == 0 else 74
    if scene_index == total_scenes - 1:
        text_font_size = 66

    text_font = get_font(text_font_size)
    draw_center_text(
        draw=draw,
        text=text.upper(),
        font=text_font,
        center_x=WIDTH // 2 + 20,
        center_y=panel_y + 305,
        max_width=800,
        fill=(255, 255, 255),
        shadow=True,
        line_spacing=24,
    )

    # lower slogan
    micro_font = get_font(31, bold=False)
    draw.text((90, 1220), "NO GUARANTEES • NO SIGNALS • ONLY LIVE LOGIC", font=micro_font, fill=(120, 132, 158))

    # bottom CTA panel
    draw_rounded_panel(
        draw,
        (60, 1640, WIDTH - 60, 1805),
        radius=46,
        fill=(15, 22, 38),
        outline=(38, 56, 82),
        width=2,
    )

    cta_font = get_font(42)
    draw_center_text(
        draw=draw,
        text="БОЛЬШЕ LIVE-РАЗБОРОВ — В TELEGRAM @DERZKIYBAFFET",
        font=cta_font,
        center_x=WIDTH // 2,
        center_y=1722,
        max_width=880,
        fill=(255, 255, 255),
        shadow=False,
        line_spacing=12,
    )

    draw_progress(draw, scene_index, total_scenes, local_progress)

    return img


def build_video(scenes, post_id):
    if os.path.exists(OUT_DIR):
        shutil.rmtree(OUT_DIR)

    os.makedirs(FRAMES_DIR, exist_ok=True)

    frame_counter = 0
    total_scenes = len(scenes)

    for scene_index, scene in enumerate(scenes):
        label = scene["label"]
        text = scene["text"]

        for frame_in_scene in range(FPS * SECONDS_PER_SCENE):
            global_frame = scene_index * FPS * SECONDS_PER_SCENE + frame_in_scene

            img = draw_scene(
                frame_index=global_frame,
                scene_index=scene_index,
                total_scenes=total_scenes,
                label=label,
                text=text,
                post_id=post_id,
            )

            frame_path = os.path.join(FRAMES_DIR, f"frame_{frame_counter:05d}.jpg")
            img.save(frame_path, quality=90, optimize=True)
            frame_counter += 1

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            os.path.join(FRAMES_DIR, "frame_%05d.jpg"),
            "-vf",
            "format=yuv420p",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            VIDEO_PATH,
        ],
        check=True,
    )

    print(f"Video created: {VIDEO_PATH}")


def main():
    post_id = os.getenv("POST_ID", "POST")
    raw_text = os.getenv("RAW_TEXT", "")

    if raw_text:
        title = shorten(
            extract_field(raw_text, "ЗАГОЛОВОК:", "Почему я не зашёл в сделку"),
            86,
        )
        screen1 = shorten(
            extract_field(raw_text, "ЭКРАН 1:", "Цена дала движение"),
            78,
        )
        screen2 = shorten(
            extract_field(raw_text, "ЭКРАН 2:", "Но подтверждения не было"),
            78,
        )
        screen3 = shorten(
            extract_field(raw_text, "ЭКРАН 3:", "Лучше пропустить ловушку"),
            78,
        )
    else:
        title = os.getenv("VIDEO_TITLE", "Почему я не зашёл в сделку")
        screen1 = os.getenv("SCREEN_1", "Цена дала движение")
        screen2 = os.getenv("SCREEN_2", "Но подтверждения не было")
        screen3 = os.getenv("SCREEN_3", "Лучше пропустить ловушку")

    scenes = [
        {"label": "Хук", "text": title},
        {"label": "Факт 1", "text": screen1},
        {"label": "Факт 2", "text": screen2},
        {"label": "Вывод", "text": screen3},
        {"label": "Telegram", "text": "Продолжение разбора — в Telegram"},
    ]

    build_video(scenes, post_id)


if __name__ == "__main__":
    main()
