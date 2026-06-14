import os
import textwrap
import subprocess
from PIL import Image, ImageDraw, ImageFont


WIDTH = 1080
HEIGHT = 1920
FPS = 30
SECONDS_PER_SCENE = 5

OUT_DIR = "out"
FRAMES_DIR = os.path.join(OUT_DIR, "frames")
VIDEO_PATH = os.path.join(OUT_DIR, "video.mp4")


def get_font(size: int):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_wrapped_text(draw, text, font, x, y, max_width, line_spacing=18, fill=(255, 255, 255)):
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

    total_height = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        total_height += (bbox[3] - bbox[1]) + line_spacing

    start_y = y - total_height // 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        draw.text((x - line_width // 2, start_y), line, font=font, fill=fill)
        start_y += (bbox[3] - bbox[1]) + line_spacing


def make_background(draw):
    # dark trading-style background
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(8, 10, 18))

    # grid
    grid_color = (25, 30, 45)
    for x in range(0, WIDTH, 90):
        draw.line((x, 0, x, HEIGHT), fill=grid_color, width=1)
    for y in range(0, HEIGHT, 90):
        draw.line((0, y, WIDTH, y), fill=grid_color, width=1)

    # fake candle chart line
    green = (20, 220, 130)
    red = (240, 70, 70)
    base_y = 1350
    x = 80
    candles = [
        (60, -90, green), (60, 80, red), (60, -130, green), (60, -50, green),
        (60, 120, red), (60, -170, green), (60, 60, red), (60, -80, green),
        (60, -140, green), (60, 110, red), (60, -180, green), (60, -60, green),
    ]

    y = base_y
    for w, move, color in candles:
        open_y = y
        close_y = y + move
        high_y = min(open_y, close_y) - 50
        low_y = max(open_y, close_y) + 50

        cx = x + w // 2
        draw.line((cx, high_y, cx, low_y), fill=color, width=6)
        top = min(open_y, close_y)
        bottom = max(open_y, close_y)
        draw.rounded_rectangle((x, top, x + w, bottom), radius=8, fill=color)

        y = close_y
        x += 80


def create_scene(text, scene_index, total_scenes):
    img = Image.new("RGB", (WIDTH, HEIGHT), (8, 10, 18))
    draw = ImageDraw.Draw(img)

    make_background(draw)

    title_font = get_font(78)
    small_font = get_font(42)
    badge_font = get_font(36)

    # top badge
    draw.rounded_rectangle((70, 90, 520, 155), radius=28, fill=(18, 24, 38))
    draw.text((95, 105), "LIVE TRADING", font=badge_font, fill=(20, 220, 130))

    # main text box
    draw.rounded_rectangle((70, 430, WIDTH - 70, 980), radius=48, fill=(13, 18, 32))
    draw_wrapped_text(
        draw=draw,
        text=text.upper(),
        font=title_font,
        x=WIDTH // 2,
        y=705,
        max_width=850,
        line_spacing=24,
        fill=(255, 255, 255),
    )

    # progress dots
    dot_y = 1090
    start_x = WIDTH // 2 - (total_scenes * 34) // 2
    for i in range(total_scenes):
        color = (20, 220, 130) if i == scene_index else (80, 90, 110)
        draw.ellipse((start_x + i * 34, dot_y, start_x + i * 34 + 16, dot_y + 16), fill=color)

    # bottom CTA
    draw.rounded_rectangle((70, 1650, WIDTH - 70, 1780), radius=40, fill=(18, 24, 38))
    draw_wrapped_text(
        draw=draw,
        text="БОЛЬШЕ LIVE-РАЗБОРОВ — В TELEGRAM @DERZKIYBAFFET",
        font=small_font,
        x=WIDTH // 2,
        y=1715,
        max_width=870,
        line_spacing=12,
        fill=(255, 255, 255),
    )

    path = os.path.join(FRAMES_DIR, f"scene_{scene_index}.png")
    img.save(path)
    return path


def main():
    os.makedirs(FRAMES_DIR, exist_ok=True)

    title = os.getenv("VIDEO_TITLE", "Почему я не зашёл в сделку")
    screen1 = os.getenv("SCREEN_1", "Движение было красивое")
    screen2 = os.getenv("SCREEN_2", "Но подтверждения не было")
    screen3 = os.getenv("SCREEN_3", "Лучше пропустить, чем зайти в ловушку")

    scenes = [title, screen1, screen2, screen3]

    scene_paths = []
    for i, text in enumerate(scenes):
        scene_paths.append(create_scene(text, i, len(scenes)))

    list_path = os.path.join(OUT_DIR, "inputs.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for path in scene_paths:
            f.write(f"file '{os.path.abspath(path)}'\n")
            f.write(f"duration {SECONDS_PER_SCENE}\n")
        f.write(f"file '{os.path.abspath(scene_paths[-1])}'\n")

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            list_path,
            "-vf",
            "fps=30,format=yuv420p",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            VIDEO_PATH,
        ],
        check=True,
    )

    print(f"Video created: {VIDEO_PATH}")


if __name__ == "__main__":
    main()
