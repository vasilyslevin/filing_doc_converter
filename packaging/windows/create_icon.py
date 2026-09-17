import sys
from pathlib import Path

from PIL import Image, ImageDraw


def create_icon(output_path: Path) -> None:
    image = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((40, 40, 984, 984), radius=190, fill="#123B5D")
    draw.polygon(
        [(245, 145), (650, 145), (795, 290), (795, 850), (245, 850)],
        fill="#F7FAFC",
    )
    draw.polygon([(650, 145), (650, 290), (795, 290)], fill="#B9D5E6")
    draw.rounded_rectangle((335, 355, 700, 405), radius=24, fill="#2CB1A1")
    draw.rounded_rectangle((335, 455, 650, 505), radius=24, fill="#79CEC4")
    draw.polygon(
        [(340, 620), (610, 620), (610, 565), (720, 650), (610, 735), (610, 680), (340, 680)],
        fill="#F6B84A",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(
        output_path,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


if __name__ == "__main__":
    create_icon(Path(sys.argv[1]))
