"""교사 양식(.pptx)의 슬라이드를 복제해 글과 사진만 바꿔 수업 PPT를 만든다.

양식의 배경·장식·배치는 그대로 두고, 양식 슬라이드를 골라(같은 장을 여러 번 써도 됨) 도형 이름으로 내용을 채운다.
Canva 등에서 받은 양식처럼 디자인이 레이아웃이 아니라 슬라이드 위에 직접 그려진 경우에도 디자인이 지켜진다.
도형 이름과 위치는 먼저 --inspect로 확인한다. 글만 나열되는 장은 add로 카드·연표·흐름 도형을 그려 인포그래픽으로 만든다.

입력 JSON 예시 (그대로 복사해도 유효한 JSON):
{
  "template": "양식.pptx",
  "slides": [
    {"from": 1, "text": {"TextBox 14": ["6·25 전쟁과", "분단의 고착화"]}, "notes": "도입 2분"},
    {"from": 3, "text": {"TextBox 13": "냉전 체제의 형성", "TextBox 14": ["**미·소 대립**", "트루먼 독트린(1947)"]},
     "size": {"TextBox 14": 24},
     "geometry": {"TextBox 14": {"top": 5850000, "height": 2200000}},
     "clone": [{"from": "TextBox 14", "name": "본문 2", "top": 7000000}],
     "images": {"Freeform 9": {"path": "사진.jpg", "crop": [0, 0.5, 0.6, 1]}},
     "remove": ["Group 20"],
     "add": [{"shape": "circle", "left": 2000000, "top": 6000000, "width": 1200000, "height": 1200000,
              "fill": "8C2F2F", "text": "1947", "size": 24, "color": "FFFFFF", "bold": true},
             {"shape": "chevron", "left": 3400000, "top": 6100000, "width": 900000, "height": 1000000, "fill": "BBBBBB"}]}
  ]
}

설명:
- template: 양식 파일. slides의 from은 양식의 몇 번째 슬라이드를 복제할지(1부터)이다. 결과에는 slides에 적은 장만 그 순서로 남는다.
- text: {도형 이름: 글 또는 문단 목록}. i번째 문단은 양식의 i번째 문단 모양(글꼴, 크기, 색, 정렬, 글머리표)을 따르고,
  양식 문단이 모자라면 마지막 문단의 모양을 쓴다. 빈 목록은 쓸 수 없다 (글을 지우려면 remove). **굵게** 가능.
- size: {도형 이름: 글자 크기(pt)}. 양식 글자가 작을 때 키운다.
- geometry: {도형 이름: {left, top, width, height}} (EMU, --inspect에 나온 값과 같은 단위). 일부만 적어도 된다.
- clone: 도형을 복제해 새 이름을 붙인다 (목록 칸이 모자랄 때). 위치 값을 함께 적을 수 있다. text 등에서 새 이름으로 부른다.
- images: {그림 도형 이름: 사진 경로 또는 {"path", "crop"}}. 사진은 도형 비율에 맞게 가운데를 잘라 넣는다.
  crop은 먼저 잘라 낼 영역 [왼쪽, 위, 오른쪽, 아래]를 0~1 비율로 적는다 (중요한 부분이 한쪽에 있을 때).
- remove: 지울 도형 이름 목록 (주제와 맞지 않는 사진이나 남는 칸).
- add: 새로 그릴 도형 목록 (인포그래픽용). shape는 box / rounded / circle / chevron / arrow / line / image 중 하나.
  left·top·width·height(EMU)는 필수. fill·line(테두리)·color(글자)는 RRGGBB, text는 글 또는 문단 목록,
  size(pt)·bold·align(left/center/right)·font·line_width(pt)·name은 선택. 글꼴을 비우면 양식 제목의 글꼴을 쓴다.
  line은 left·top에서 left+width·top+height까지 긋는다.
  image는 path(그림 경로)와 crop(선택)을 받아 상자 안에 비율을 지켜 가운데 맞춤으로 넣는다 (지도·도표처럼 잘리면 안 되는 그림).
- "확인 필요" 경고: 복제한 장에 양식의 원래 글이 남았을 때(text·remove·images·size가 건드리지 않은 글 도형),
  글이 상자를 넘칠 때, 문단 끝 몇 글자만 다음 줄로 넘어갈 때, 글·그림·상자·선 등 도형이 슬라이드 밖으로 나갈 때
  (회전을 반영한 보이는 모양 기준). add 도형은 밖으로 나가면 크기는 그대로 두고 테두리 안으로 옮긴다. geometry 값은 회전 전 기준이다.
- notes: 발표자 노트.
- 실행 순서는 clone → remove → geometry → text·size → images → add → notes이다.
- 상대 경로는 입력 JSON 파일이 있는 폴더를 기준으로 찾는다.
- 출력 파일은 .pptx여야 하며 입력 JSON이나 양식 파일과 같은 경로일 수 없다 (원본 덮어쓰기 방지).

사용법:
    python fill_template.py --inspect 양식.pptx     양식의 슬라이드별 도형 이름·위치·글자 크기·글을 보여 준다
    python fill_template.py 입력.json 수업.pptx
"""

from __future__ import annotations

import copy
import io
import math
import sys
from pathlib import Path

from pptx import Presentation
from pptx.exc import PackageNotFoundError
from pptx.oxml.ns import qn
from pptx.util import Emu

from fill_template_shapes import ADD_SHAPES, add_shapes, check_add, check_crop, open_cropped, style_runs
from make_deck_check import describe_os_error, read_input_json
from make_pptx_base import split_bold
from pptx_safety import check_image_size, check_inside_folder, check_pptx, stamp_properties
from slide_check import SHORT_TAIL_RATIO

OUTPUT_SUFFIX = ".pptx"
EMU_PER_INCH = 914400
DEFAULT_PT = 18
LINE_FACTOR = 1.2                    # 양식 글상자의 보통 줄 간격
OVERFLOW_RATIO = 1.25                # 예상 높이가 상자 높이의 이 배를 넘으면 경고
ORPHAN_RATIO = SHORT_TAIL_RATIO      # 마지막 줄이 한 줄의 이 비율 이하면 "몇 글자만 넘어감" (모든 검사가 같은 값)
# 글자 폭(글자 크기 대비). PowerPoint 실측 339문단과 비교해 맞춘 값 (판정 불일치 2개)
HANGUL_EM, LATIN_EM, SPACE_EM = 0.9, 0.55, 0.3
DEFAULT_INSET = 91440                # 글상자 기본 좌우 여백
TOP_BIAS = 0.35                      # 세로로 잘라 낼 때 위쪽을 더 남긴다 (사람 얼굴·건물 윗부분)
GEOMETRY_KEYS = ("left", "top", "width", "height")
R_ATTRS = (qn("r:embed"), qn("r:link"), qn("r:id"))
SKIPPED_RELS = ("/slideLayout", "/notesSlide")
GROUP = 6
LEFTOVER_CHARS = 20                  # 남은 양식 글을 경고에 보일 글자 수


# ---------------------------------------------------------------- 도형 찾기

def _walk(shapes, inside_group: bool = False):
    for shape in shapes:
        yield shape, inside_group
        if shape.shape_type == GROUP:
            yield from _walk(shape.shapes, True)


def _shape_map(slide) -> dict:
    found: dict = {}
    for shape, _ in _walk(slide.shapes):
        found.setdefault(shape.name, shape)
    return found


def _find(slide, name: str, where: str):
    shapes = _shape_map(slide)
    if name not in shapes:
        raise ValueError(f"{where}: '{name}' 도형이 없음 (있는 이름: {', '.join(shapes)})")
    return shapes[name]


# ---------------------------------------------------------------- 슬라이드 복제

def _duplicate(prs, source):
    slide = prs.slides.add_slide(source.slide_layout)
    for placeholder in list(slide.placeholders):
        placeholder._element.getparent().remove(placeholder._element)
    mapping = {}
    for rid, rel in source.part.rels.items():
        if rel.reltype.endswith(SKIPPED_RELS):
            continue
        if rel.is_external:
            mapping[rid] = slide.part.relate_to(rel.target_ref, rel.reltype, is_external=True)
        else:
            mapping[rid] = slide.part.relate_to(rel.target_part, rel.reltype)
    tree = slide.shapes._spTree
    for element in source.shapes._spTree:
        if element.tag in (qn("p:nvGrpSpPr"), qn("p:grpSpPr")):
            continue
        clone = copy.deepcopy(element)
        for node in clone.iter():
            for attr in R_ATTRS:
                if node.get(attr) in mapping:
                    node.set(attr, mapping[node.get(attr)])
        tree.append(clone)
    return slide


def _drop_original_slides(prs, count: int) -> None:
    id_list = prs.slides._sldIdLst
    for slide_id in list(id_list)[:count]:
        prs.part.drop_rel(slide_id.rId)
        id_list.remove(slide_id)


# ---------------------------------------------------------------- 도형 고치기

def _next_shape_id(slide) -> int:
    return max(int(node.get("id")) for node in slide.shapes._spTree.iter(qn("p:cNvPr"))) + 1


def _clone_shapes(slide, entries: list, where: str) -> None:
    for entry in entries:
        source = _find(slide, entry["from"], where)
        element = copy.deepcopy(source._element)
        name_node = element.find(".//" + qn("p:cNvPr"))
        name_node.set("name", entry["name"])
        name_node.set("id", str(_next_shape_id(slide)))
        source._element.addnext(element)
        _set_geometry(_find(slide, entry["name"], where), entry)


def _set_geometry(shape, values: dict) -> None:
    for key in GEOMETRY_KEYS:
        if key in values:
            setattr(shape, key, Emu(int(values[key])))


def _paragraph_model(paragraph) -> tuple:
    """양식 문단의 (문단 모양 pPr, 첫 글자 모양 rPr). 없으면 None."""
    first_run = paragraph.find(qn("a:r"))
    return paragraph.find(qn("a:pPr")), (first_run.find(qn("a:rPr")) if first_run is not None else None)


def _set_text(shape, value, size, where: str) -> None:
    if not shape.has_text_frame:
        raise ValueError(f"{where}: '{shape.name}'은 글을 넣을 수 없는 도형임")
    if isinstance(value, list) and not value:
        raise ValueError(f"{where}: '{shape.name}'의 글이 빈 목록임. 글을 지우려면 remove를 쓰세요")
    body = shape.text_frame._txBody
    paragraphs = body.findall(qn("a:p"))
    models = [_paragraph_model(p) for p in paragraphs]
    fallback_run = next((run_pr for _, run_pr in models if run_pr is not None), None)
    for paragraph in paragraphs:
        body.remove(paragraph)
    for index, text in enumerate(value if isinstance(value, list) else [value]):
        p_pr, r_pr = models[min(index, len(models) - 1)]     # i번째 문단은 양식의 i번째 문단 모양, 모자라면 마지막 것
        r_pr = r_pr if r_pr is not None else fallback_run
        paragraph = body.makeelement(qn("a:p"), {})
        if p_pr is not None:
            paragraph.append(copy.deepcopy(p_pr))
        for part, bold in split_bold(text):
            run = paragraph.makeelement(qn("a:r"), {})
            props = copy.deepcopy(r_pr) if r_pr is not None else run.makeelement(qn("a:rPr"), {})
            if bold:
                props.set("b", "1")
            run.append(props)
            node = run.makeelement(qn("a:t"), {})
            node.text = part
            run.append(node)
            paragraph.append(run)
        body.append(paragraph)
    style_runs(shape, size)


def _display_size(shape) -> tuple[int, int]:
    """그룹 안 도형은 그룹의 확대·축소를 반영한 실제 크기를 돌려준다."""
    width, height = shape.width, shape.height
    parent = shape._element.getparent()
    while parent is not None and parent.tag == qn("p:grpSp"):
        xfrm = parent.find(qn("p:grpSpPr")).find(qn("a:xfrm"))
        ext, child = xfrm.find(qn("a:ext")), xfrm.find(qn("a:chExt"))
        if child is not None and int(child.get("cx")) and int(child.get("cy")):
            width = width * int(ext.get("cx")) / int(child.get("cx"))
            height = height * int(ext.get("cy")) / int(child.get("cy"))
        parent = parent.getparent()
    return int(width), int(height)


def _fit_image(path: Path, ratio: float, crop) -> io.BytesIO:
    image = open_cropped(path, crop)
    w, h = image.size
    if w / h > ratio:
        new_w = int(h * ratio)
        image = image.crop(((w - new_w) // 2, 0, (w - new_w) // 2 + new_w, h))
    else:
        new_h = int(w / ratio)
        top = int((h - new_h) * TOP_BIAS)
        image = image.crop((0, top, w, top + new_h))
    buffer = io.BytesIO()
    if image.mode in ("RGBA", "LA", "P"):
        image.save(buffer, "PNG")
    else:
        image.convert("RGB").save(buffer, "JPEG", quality=88)
    buffer.seek(0)
    return buffer


def _set_image(slide, shape, value, where: str) -> None:
    blip = shape._element.find(".//" + qn("a:blip"))
    if blip is None:
        raise ValueError(f"{where}: '{shape.name}'은 그림 채우기가 없는 도형이라 사진을 넣을 수 없음 (그림 도형을 고르세요)")
    path, crop = (value, None) if isinstance(value, str) else (value["path"], value.get("crop"))
    width, height = _display_size(shape)
    _, rid = slide.part.get_or_add_image_part(_fit_image(Path(path), width / height, crop))
    blip.set(qn("r:embed"), rid)
    for ext in blip.findall(qn("a:extLst")):  # SVG 대체 그림이 있으면 새 사진 대신 보이므로 지운다
        blip.remove(ext)
    fill = blip.getparent()
    for src_rect in fill.findall(qn("a:srcRect")):
        fill.remove(src_rect)


# ---------------------------------------------------------------- 넘침 경고

def _run_size(shape) -> float:
    for props in shape.text_frame._txBody.iter(qn("a:rPr")):
        if props.get("sz"):
            return int(props.get("sz")) / 100
    return DEFAULT_PT


def _inner_width(shape) -> int:
    body_pr = shape.text_frame._txBody.find(qn("a:bodyPr"))
    insets = sum(int(body_pr.get(key, DEFAULT_INSET)) for key in ("lIns", "rIns"))
    return max(1, shape.width - insets)


def _units(text: str) -> float:
    return sum(SPACE_EM if ch == " " else LATIN_EM if ord(ch) < 128 else HANGUL_EM for ch in text)


def _lines(shape) -> list[tuple[int, float, float]]:
    """문단마다 (예상 줄 수, 마지막 줄 폭, 한 줄 폭). 폭은 글자 크기(em) 단위."""
    per_line = _inner_width(shape) / EMU_PER_INCH * 72 / _run_size(shape)
    result = []
    for paragraph in shape.text_frame.paragraphs:
        units = _units(paragraph.text)
        lines = max(1, math.ceil(units / per_line))
        result.append((lines, units - (lines - 1) * per_line, per_line))
    return result


def _orphan(shape) -> bool:
    """몇 글자만 다음 줄로 넘어가는 문단이 있는가 (상자를 조금 넓히거나 글을 다듬으면 한 줄이 된다)."""
    return any(lines >= 2 and last <= per_line * ORPHAN_RATIO for lines, last, per_line in _lines(shape))


def _overflows(shape) -> bool:
    size = _run_size(shape)
    lines = sum(count for count, _, _ in _lines(shape))
    needed = lines * size * LINE_FACTOR / 72 * EMU_PER_INCH
    return needed > shape.height * OVERFLOW_RATIO


def _template_font(prs) -> str | None:
    """양식에서 가장 큰 글자의 글꼴(대개 제목 글꼴)을 돌려준다. add 도형의 기본 글꼴로 쓴다."""
    best: tuple[int, str | None] = (0, None)
    for slide in prs.slides:
        for props in slide.shapes._spTree.iter(qn("a:rPr")):
            typeface = _korean_typeface(props)
            size = int(props.get("sz") or 0)
            if typeface and size > best[0]:
                best = (size, typeface)
    return best[1]


def _korean_typeface(props) -> str | None:
    """글자 모양의 글꼴. 한글 자리(a:ea)를 먼저 읽고, 없거나 테마 참조(+mn-ea 등)면 영문 자리(a:latin)를 쓴다."""
    east_asian = props.find(qn("a:ea"))
    name = east_asian.get("typeface") if east_asian is not None else None
    if name and not name.startswith("+"):
        return name
    latin = props.find(qn("a:latin"))
    return latin.get("typeface") if latin is not None else None


# ---------------------------------------------------------------- 입력 검사와 실행

def _as_text(value) -> str:
    return "" if value is None else str(value)


def _check_images(where: str, images: dict) -> None:
    for value in images.values():
        if isinstance(value, dict):
            if not isinstance(value.get("path"), str):
                raise ValueError(f'{where}: images 값은 경로 또는 {{"path": 경로, "crop": [...]}} 형식이어야 함')
            if "crop" in value:
                check_crop(where, value["crop"])
        elif not isinstance(value, str):
            raise ValueError(f"{where}: images 값은 사진 경로여야 함")


def _check_slide(number: int, slide) -> None:
    where = f"{number}번 슬라이드"
    if not isinstance(slide, dict):
        raise ValueError(f'{where}: {{"from": 양식 쪽 번호, ...}} 형식이어야 함')
    source = slide.get("from")
    if not isinstance(source, int) or isinstance(source, bool) or source < 1:
        raise ValueError(f"{where}: from은 1 이상의 정수(양식의 몇 번째 슬라이드)여야 함")
    for key in ("text", "size", "geometry", "images"):
        if not isinstance(slide.get(key, {}), dict):
            raise ValueError(f"{where}: {key}는 {{도형 이름: 값}} 형식이어야 함")
    for key in ("remove", "clone", "add"):
        if not isinstance(slide.get(key, []), list):
            raise ValueError(f"{where}: {key}는 목록이어야 함")
    for name, value in slide.get("text", {}).items():
        if isinstance(value, list) and not value:
            raise ValueError(f"{where}: text의 '{name}'이(가) 빈 목록임. 글을 지우려면 remove를 쓰세요")
    for entry in slide.get("clone", []):
        if not isinstance(entry, dict) or not entry.get("from") or not entry.get("name"):
            raise ValueError(f'{where}: clone은 {{"from": 원래 이름, "name": 새 이름}} 형식이어야 함')
    _check_images(where, slide.get("images", {}))
    for entry in slide.get("add", []):
        check_add(where, entry)


def validate(spec) -> None:
    if not isinstance(spec, dict):
        raise ValueError("입력 JSON의 최상위는 {...} 객체여야 함")
    if not isinstance(spec.get("template"), str) or not spec["template"]:
        raise ValueError("template(양식 .pptx 파일 경로)이 필요함")
    if not isinstance(spec.get("slides"), list) or not spec["slides"]:
        raise ValueError("slides가 비어 있음")
    for number, slide in enumerate(spec["slides"], 1):
        _check_slide(number, slide)


def _open(path: str):
    check_pptx(path, "양식")
    try:
        return Presentation(path)
    except (PackageNotFoundError, OSError, KeyError, ValueError) as error:
        raise ValueError(f"양식을 열 수 없음: {path} (.pptx 파일인지 확인해 주세요)") from error


def _check_wrap(shape, name: str, where: str, warnings: list[str]) -> None:
    if _overflows(shape):
        warnings.append(f"{where} '{name}' 글이 상자보다 길어 넘칠 수 있음 (글을 줄이거나 size·geometry로 조정)")
    elif _orphan(shape):
        warnings.append(f"{where} '{name}' 문단 끝 몇 글자만 다음 줄로 넘어감 (상자를 넓히거나 글을 다듬어 한 줄로)")


def _fill_texts(slide, spec: dict, where: str, warnings: list[str]) -> None:
    sizes, texts = spec.get("size", {}), spec.get("text", {})
    for name, value in texts.items():
        shape = _find(slide, name, where)
        text = [_as_text(v) for v in value] if isinstance(value, list) else _as_text(value)
        _set_text(shape, text, sizes.get(name), where)
        _check_wrap(shape, name, where, warnings)
    for name, size in sizes.items():
        if name not in texts:
            style_runs(_find(slide, name, where), size)


def _has_picture(shape) -> bool:
    return shape._element.find(".//" + qn("a:blip")) is not None


def _rotation(shape) -> float:
    xfrm = shape._element.find(".//" + qn("a:xfrm"))  # 도형 자신의 xfrm이 자식보다 먼저 나온다
    return int(xfrm.get("rot", 0)) / 60000 if xfrm is not None else 0.0


def _visible_box(shape) -> tuple[float, float, float, float]:
    """회전을 반영해 화면에 보이는 (왼쪽, 위, 오른쪽, 아래)."""
    angle = math.radians(_rotation(shape))
    half_w = (abs(shape.width * math.cos(angle)) + abs(shape.height * math.sin(angle))) / 2
    half_h = (abs(shape.width * math.sin(angle)) + abs(shape.height * math.cos(angle))) / 2
    center_x, center_y = shape.left + shape.width / 2, shape.top + shape.height / 2
    return center_x - half_w, center_y - half_h, center_x + half_w, center_y + half_h


def _outside(shape, size: tuple[int, int]) -> bool:
    """슬라이드(가로, 세로) 테두리 밖으로 나가는가. 맨 위 단계 도형(그룹은 그룹 전체)에 쓴다."""
    left, top, right, bottom = _visible_box(shape)
    tolerance = 1  # EMU 반올림
    return left < -tolerance or top < -tolerance or right > size[0] + tolerance or bottom > size[1] + tolerance


def _kind(shape) -> str:
    if _has_picture(shape):
        return "그림"
    if shape.has_text_frame and shape.text_frame.text.strip():
        return "글"
    return "도형"


def _check_bounds(slide, size: tuple[int, int], where: str, warnings: list[str]) -> None:
    """글·그림·상자·선·묶음 등 모든 도형이 슬라이드 테두리 안에 있는지 본다."""
    for shape in slide.shapes:
        if _outside(shape, size):
            warnings.append(f"{where} '{shape.name}' {_kind(shape)}이(가) 슬라이드 밖으로 나감 "
                            "(geometry로 줄이거나 옮겨 테두리 안으로)")


def _move_inside(shape, size: tuple[int, int], name: str, where: str, warnings: list[str]) -> None:
    """add로 그린 도형이 테두리를 벗어나면 크기는 그대로 두고 안쪽으로 옮긴다."""
    left, top, right, bottom = _visible_box(shape)
    if right - left > size[0] or bottom - top > size[1]:
        return  # 슬라이드보다 커서 옮겨도 안 들어간다: _check_bounds가 알린다
    dx = -left if left < 0 else size[0] - right if right > size[0] else 0
    dy = -top if top < 0 else size[1] - bottom if bottom > size[1] else 0
    if dx or dy:
        shape.left, shape.top = Emu(int(shape.left + dx)), Emu(int(shape.top + dy))
        warnings.append(f"{where} add '{name}'이(가) 슬라이드 밖으로 나가 테두리 안으로 옮김 (좌표를 확인)")


def _warn_leftover(slide, spec: dict, where: str, warnings: list[str]) -> None:
    """text·images·size가 건드리지 않았는데 양식의 원래 글이 남은 글 도형을 알린다 (remove한 도형은 이미 없다)."""
    touched = set(spec.get("text", {})) | set(spec.get("images", {})) | set(spec.get("size", {}))
    for shape, _ in _walk(slide.shapes):
        if shape.name in touched or not shape.has_text_frame or not shape.text_frame.text.strip():
            continue
        excerpt = " / ".join(p.text for p in shape.text_frame.paragraphs if p.text.strip())[:LEFTOVER_CHARS]
        warnings.append(f"{where} '{shape.name}' 양식 원래 글이 남음 '{excerpt}' (text로 바꾸거나 remove로 지우세요)")


def _fill_slide(slide, spec: dict, where: str, font: str | None, size: tuple[int, int],
                warnings: list[str]) -> None:
    _clone_shapes(slide, spec.get("clone", []), where)
    for name in spec.get("remove", []):
        element = _find(slide, name, where)._element
        element.getparent().remove(element)
    for name, values in spec.get("geometry", {}).items():
        _set_geometry(_find(slide, name, where), values)
    _fill_texts(slide, spec, where, warnings)
    for name, value in spec.get("images", {}).items():
        _set_image(slide, _find(slide, name, where), value, where)
    _warn_leftover(slide, spec, where, warnings)
    for entry, shape in zip(spec.get("add", []), add_shapes(slide, spec.get("add", []), font)):
        name = entry.get("name") or f"add {entry['shape']}"
        _move_inside(shape, size, name, where, warnings)
        if shape.has_text_frame and shape.text_frame.text.strip():
            _check_wrap(shape, name, where, warnings)
    if spec.get("notes"):
        slide.notes_slide.notes_text_frame.text = _as_text(spec["notes"])


def build(spec: dict, out_path: Path) -> list[str]:
    validate(spec)
    prs = _open(spec["template"])
    originals = list(prs.slides)
    font = _template_font(prs)
    warnings: list[str] = []
    for number, slide_spec in enumerate(spec["slides"], 1):
        source = slide_spec["from"]
        if source > len(originals):
            raise ValueError(f"{number}번 슬라이드: from은 1~{len(originals)} 사이여야 함 (양식 슬라이드 {len(originals)}장)")
        slide = _duplicate(prs, originals[source - 1])
        where = f"{number}쪽(양식 {source}쪽)"
        size = (prs.slide_width, prs.slide_height)
        _fill_slide(slide, slide_spec, where, font, size, warnings)
        _check_bounds(slide, size, where, warnings)
    _drop_original_slides(prs, len(originals))
    stamp_properties(prs)
    prs.save(str(out_path))
    return warnings


def _describe(shape, inside_group: bool, size: tuple[int, int]) -> str:
    where = f"x={shape.left} y={shape.top} w={shape.width} h={shape.height}" + (" (묶음 안 좌표)" if inside_group else "")
    edge = " | 슬라이드 밖으로 나감" if not inside_group and _outside(shape, size) else ""
    if shape.has_text_frame and shape.text_frame.text.strip():
        lines = [p.text for p in shape.text_frame.paragraphs if p.text.strip()]
        excerpt = " / ".join(lines)[:60]
        return f"  글   {shape.name} | {where} | {_run_size(shape):g}pt · {len(lines)}문단 | \"{excerpt}\"{edge}"
    if _has_picture(shape):
        width, height = _display_size(shape)
        turn = f" | 회전 {_rotation(shape):g}°" if _rotation(shape) else ""
        return f"  그림 {shape.name} | {where} | 가로:세로 {width / height:.2f}{turn}{edge}"
    if shape.shape_type == GROUP:
        return f"  묶음 {shape.name} | {where}{edge}"
    return ""


def inspect_template(path) -> str:
    prs = _open(str(path))
    width_in, height_in = prs.slide_width / EMU_PER_INCH, prs.slide_height / EMU_PER_INCH
    report = [f"양식: {Path(path).name} · 슬라이드 {len(prs.slides)}장 · "
              f"{prs.slide_width}×{prs.slide_height} EMU ({width_in:.2f}×{height_in:.2f} in)",
              f"제목 글꼴: {_template_font(prs) or '(없음)'} · add 도형 종류: {', '.join(ADD_SHAPES)}"]
    for number, slide in enumerate(prs.slides, 1):
        report.append(f"[{number}쪽]")
        others, outside = [], []
        size = (prs.slide_width, prs.slide_height)
        for shape, inside_group in _walk(slide.shapes):
            line = _describe(shape, inside_group, size)
            if line:
                report.append(line)
            else:
                others.append(shape.name)
                if not inside_group and _outside(shape, size):
                    outside.append(shape.name)
        if others:
            report.append(f"  장식 {', '.join(others)}")
        if outside:
            report.append(f"  밖으로 나간 장식: {', '.join(outside)}")
    return "\n".join(report) + "\n"


def _resolve_paths(spec: dict, base: Path) -> dict:
    """상대 경로(양식, 사진, add 그림)를 입력 JSON 폴더 기준으로 바꾼 새 spec을 돌려준다."""
    def resolve(value: str) -> str:
        return value if Path(value).is_absolute() else str(base / value)

    def resolve_image(value: str) -> str:
        check_inside_folder(value, base)
        return resolve(value)

    slides = []
    for slide in spec["slides"]:
        images = {name: resolve_image(v) if isinstance(v, str) else {**v, "path": resolve_image(v["path"])}
                  for name, v in slide.get("images", {}).items()}
        adds = [{**entry, "path": resolve_image(entry["path"])} if isinstance(entry, dict) and isinstance(entry.get("path"), str)
                else entry for entry in slide.get("add", [])]
        slides.append({**slide, "images": images, "add": adds})
    return {**spec, "template": resolve(spec["template"]), "slides": slides}


def _check_paths(input_path: Path, output_path: Path, template: str) -> None:
    if output_path.suffix.lower() != OUTPUT_SUFFIX:
        raise ValueError(f"출력 파일 이름은 {OUTPUT_SUFFIX}로 끝나야 함 (받은 값: {output_path.name})")
    output = output_path.resolve()
    if output == input_path.resolve():
        raise ValueError("출력 파일이 입력 JSON 파일과 같을 수 없음 (원본이 덮어써집니다)")
    if output == Path(template).resolve():
        raise ValueError("출력 파일이 템플릿(양식) 파일과 같을 수 없음 (양식이 덮어써집니다)")


def _run(args: list[str]) -> list[str]:
    input_path, output_path = Path(args[0]), Path(args[1])
    spec = read_input_json(input_path)
    validate(spec)
    spec = _resolve_paths(spec, input_path.resolve().parent)
    _check_paths(input_path, output_path, spec["template"])
    return build(spec, output_path)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError, OSError):
        pass  # 이미 바뀌었거나 바꿀 수 없는 출력 스트림
    usage = "사용법: python fill_template.py --inspect 양식.pptx | python fill_template.py 입력.json 출력.pptx\n"
    if len(args) != 2:
        sys.stdout.write(usage)
        return 2
    try:
        if args[0] == "--inspect":
            sys.stdout.write(inspect_template(args[1]))
            return 0
        warnings = _run(args)
    except OSError as error:
        sys.stdout.write(f"입력 오류: {describe_os_error(error)}\n")
        return 1
    except (ValueError, KeyError, TypeError, AttributeError) as error:  # JSON 문법 오류도 read_input_json이 ValueError로 바꾼다
        sys.stdout.write(f"입력 오류: {error}\n")
        return 1
    except Exception as error:  # noqa: BLE001 - 어떤 입력에도 traceback 대신 안내 문구를 보인다
        sys.stdout.write(f"입력 오류: 예상하지 못한 입력입니다 ({type(error).__name__})\n")
        return 1
    sys.stdout.write(f"완료: {args[1]}\n")
    for warning in warnings:
        sys.stdout.write(f"확인 필요: {warning}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
