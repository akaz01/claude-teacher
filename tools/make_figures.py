"""문제지 대화 장면에 쓰는 인물 클립아트를 그린다 (개발용, Pillow 필요).

결과: shared/scripts/fill_exam_figure_<이름>.png. 글자가 없는 상반신 그림이고, 흑백 인쇄에서도
얼굴과 옷이 구분되도록 진한 테두리를 두른다. 배포 묶음에는 PNG만 들어가고 이 스크립트는 들어가지 않는다.

    python tools/make_figures.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "shared" / "scripts"
W, H = 300, 330
S = 4                                   # 크게 그려 줄여 매끄럽게 한다
LINE = (51, 51, 51, 255)
SKIN = (250, 222, 196, 255)
CHEEK = (246, 180, 170, 255)
WHITE = (255, 255, 255, 255)
STROKE = 3


def _box(*xy: float) -> list[float]:
    return [v * S for v in xy]


class Figure:
    def __init__(self) -> None:
        self.image = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)

    def _outline(self, line: bool) -> dict:
        return {"outline": LINE, "width": STROKE * S} if line else {"outline": None, "width": 0}

    def ellipse(self, box, fill, line=True):
        self.draw.ellipse(_box(*box), fill=fill, **self._outline(line))

    def rounded(self, box, radius, fill, line=True):
        self.draw.rounded_rectangle(_box(*box), radius * S, fill=fill, **self._outline(line))

    def polygon(self, points, fill, line=True):
        self.draw.polygon([v * S for point in points for v in point], fill=fill, **self._outline(line))

    def chord(self, box, start, end, fill, line=True):
        self.draw.chord(_box(*box), start, end, fill=fill, **self._outline(line))

    def arc(self, box, start, end, width=STROKE):
        self.draw.arc(_box(*box), start, end, fill=LINE, width=width * S)

    def line(self, points, width=STROKE):
        self.draw.line([v * S for point in points for v in point], fill=LINE, width=width * S, joint="curve")

    def save(self, name: str) -> Path:
        path = OUT / f"fill_exam_figure_{name}.png"
        self.image.resize((W, H), Image.LANCZOS).save(path, optimize=True)
        return path


# ---------------------------------------------------------------- 부분

def body(fig: Figure, cloth, collar=None) -> None:
    fig.rounded((45, 238, 255, 360), 60, cloth)
    fig.rounded((132, 182, 168, 246), 10, SKIN)
    if collar == "uniform":                         # 흰 깃 + 겉옷 깃
        fig.polygon([(118, 240), (150, 292), (182, 240)], WHITE)
        fig.polygon([(100, 246), (150, 320), (118, 240)], cloth)
        fig.polygon([(200, 246), (150, 320), (182, 240)], cloth)
    elif collar == "shirt":
        fig.polygon([(122, 240), (150, 270), (178, 240)], WHITE)
    elif collar == "round":
        fig.chord((118, 222, 182, 262), 0, 180, SKIN)


def tie(fig: Figure, color) -> None:
    fig.polygon([(143, 268), (157, 268), (161, 316), (150, 328), (139, 316)], color)
    fig.polygon([(141, 256), (159, 256), (155, 270), (145, 270)], color)


def ribbon(fig: Figure, color) -> None:
    fig.polygon([(150, 272), (124, 260), (124, 286)], color)
    fig.polygon([(150, 272), (176, 260), (176, 286)], color)
    fig.ellipse((143, 265, 157, 279), color)


def face(fig: Figure, cheeks=True) -> None:
    fig.ellipse((80, 128, 96, 156), SKIN)            # 귀
    fig.ellipse((204, 128, 220, 156), SKIN)
    fig.ellipse((88, 66, 212, 204), SKIN)
    if cheeks:
        fig.ellipse((104, 156, 124, 170), CHEEK, line=False)
        fig.ellipse((176, 156, 196, 170), CHEEK, line=False)
    fig.ellipse((122, 128, 134, 142), LINE, line=False)
    fig.ellipse((166, 128, 178, 142), LINE, line=False)
    fig.arc((132, 150, 168, 180), 20, 160)


def glasses(fig: Figure) -> None:
    fig.ellipse((110, 120, 146, 150), None)
    fig.ellipse((154, 120, 190, 150), None)
    fig.line([(146, 133), (154, 133)])


def cap(fig: Figure, box, color, fringe) -> None:
    """윗머리: 테두리는 위쪽 호에만 두르고, 이마 쪽은 앞머리(fringe) 다각형으로 들쭉날쭉하게 덮는다."""
    fig.chord(box, 180, 360, color, line=False)
    fig.polygon(fringe, color, line=False)
    fig.arc(box, 180, 360)


# ---------------------------------------------------------------- 인물

def student_m1() -> Figure:
    fig = Figure()
    body(fig, (70, 96, 150, 255), "uniform")
    tie(fig, (200, 70, 70, 255))
    face(fig)
    hair = (60, 45, 40, 255)
    cap(fig, (84, 52, 216, 176), hair, [(86, 110), (214, 110), (212, 120), (190, 112), (172, 126), (150, 110),
                                         (128, 124), (108, 112), (88, 124)])
    return fig


def student_m2() -> Figure:
    fig = Figure()
    body(fig, (95, 95, 95, 255), "uniform")
    tie(fig, (60, 110, 190, 255))
    face(fig)
    glasses(fig)
    hair = (30, 30, 30, 255)
    cap(fig, (84, 50, 216, 170), hair, [(86, 106), (214, 106), (212, 120), (196, 112), (150, 104), (120, 116),
                                         (100, 108), (88, 122)])
    return fig


def student_f1() -> Figure:
    fig = Figure()
    hair = (70, 50, 45, 255)
    fig.ellipse((196, 70, 262, 190), hair)                       # 묶은 머리
    body(fig, (70, 96, 150, 255), "uniform")
    ribbon(fig, (200, 70, 70, 255))
    face(fig)
    cap(fig, (82, 50, 218, 186), hair, [(84, 112), (216, 112), (214, 132), (200, 118), (150, 112), (130, 122),
                                         (110, 112), (90, 130)])
    fig.ellipse((200, 80, 218, 98), (240, 200, 70, 255))         # 머리끈
    return fig


def student_f2() -> Figure:
    fig = Figure()
    hair = (40, 32, 30, 255)
    fig.rounded((72, 64, 228, 262), 56, hair)                    # 긴 머리
    body(fig, (95, 95, 95, 255), "uniform")
    ribbon(fig, (60, 110, 190, 255))
    face(fig)
    cap(fig, (82, 52, 218, 180), hair, [(84, 110), (216, 110), (214, 122), (84, 122)])
    return fig


def teacher_f() -> Figure:
    fig = Figure()
    hair = (110, 70, 50, 255)
    fig.rounded((76, 60, 224, 214), 60, hair)                    # 단발
    body(fig, (150, 110, 160, 255), "round")
    face(fig)
    glasses(fig)
    cap(fig, (80, 50, 220, 170), hair, [(82, 106), (218, 106), (216, 126), (180, 110), (150, 104), (110, 116),
                                         (86, 128)])
    return fig


def teacher_m() -> Figure:
    fig = Figure()
    body(fig, (60, 70, 90, 255), "shirt")
    tie(fig, (170, 60, 60, 255))
    face(fig, cheeks=False)
    hair = (45, 40, 38, 255)
    cap(fig, (84, 56, 216, 156), hair, [(86, 104), (214, 104), (212, 114), (170, 100), (130, 100), (88, 116)])
    return fig


def elder_m() -> Figure:
    fig = Figure()
    body(fig, (120, 100, 80, 255), "shirt")
    face(fig)
    glasses(fig)
    gray = (190, 190, 190, 255)
    fig.chord((82, 84, 112, 150), 90, 270, gray)                 # 옆머리
    fig.chord((188, 84, 218, 150), 270, 90, gray)
    fig.arc((116, 98, 140, 110), 200, 340, 2)                    # 이마 주름
    fig.arc((160, 98, 184, 110), 200, 340, 2)
    fig.chord((128, 160, 172, 178), 180, 360, gray)              # 콧수염
    return fig


def elder_f() -> Figure:
    fig = Figure()
    gray = (185, 185, 185, 255)
    fig.ellipse((118, 24, 182, 78), gray)                        # 쪽머리
    body(fig, (110, 140, 120, 255), "round")
    face(fig)
    cap(fig, (82, 54, 218, 170), gray, [(84, 110), (216, 110), (214, 122), (150, 108), (86, 122)])
    fig.arc((112, 150, 128, 162), 20, 160, 2)                    # 눈가 주름
    fig.arc((172, 150, 188, 162), 20, 160, 2)
    return fig


FIGURES = {"student_m1": student_m1, "student_m2": student_m2, "student_f1": student_f1,
           "student_f2": student_f2, "teacher_f": teacher_f, "teacher_m": teacher_m,
           "elder_m": elder_m, "elder_f": elder_f}


def main() -> None:
    for name, make in FIGURES.items():
        print(make().save(name))


if __name__ == "__main__":
    main()
