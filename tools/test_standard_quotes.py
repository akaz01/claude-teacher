"""스킬 문서와 예시에 인용한 성취기준 문장이 shared/curriculum의 고시문 문장과 같은지 확인한다.

모델은 예시를 그대로 옮기므로, 예시에 지어낸 성취기준 문장이 있으면 결과물에도 그대로 나온다.
"""
import collections
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURRICULUM = ROOT / "shared" / "curriculum"
ROW = re.compile(r"^\|\s*\[([^\]]+)\]\s*\|\s*(.+?)\s*\|\s*$", re.M)
# [코드] 뒤에 "~다."로 끝나는 문장. 코드 설명(`[4국01-02]`는 ~)처럼 백틱으로 묶은 것은 뺀다
QUOTE = re.compile(r"(?<!`)\[(\d{1,2}[가-힣A-Za-z0-9]+\d{0,2}-\d{2}(?:-\d{2})?)\]\**\s*([^\[\]\n|\"`]{4,}?다\.)")
SAME = str.maketrans({"⋅": "·", "∙": "·"})


def _norm(text: str) -> str:
    return re.sub(r"[\s‘’'\"“”]", "", text.translate(SAME))


def _standards() -> dict[str, set[str]]:
    found = collections.defaultdict(set)
    for path in CURRICULUM.rglob("*.md"):
        if path.name in {"README.md", "INDEX.md"}:
            continue
        for code, text in ROW.findall(path.read_text(encoding="utf-8")):
            found[code].add(_norm(text))
    return found


def _documents() -> list[Path]:
    paths = [*(ROOT / "skills").rglob("*.md"), *(ROOT / "skills").rglob("*.json"),
             *(ROOT / "shared").rglob("*.md"), *(ROOT / "shared").rglob("*.json")]
    return sorted(path for path in paths if CURRICULUM not in path.parents)


def test_quoted_standards_match_the_official_text():
    standards = _standards()
    assert len(standards) > 4000                       # 데이터가 통째로 빠지면 검사가 헛돌지 않게
    wrong, checked = [], 0
    for path in _documents():
        for code, text in QUOTE.findall(path.read_text(encoding="utf-8")):
            checked += 1
            if _norm(text) not in standards.get(code, set()):
                wrong.append(f"{path.relative_to(ROOT)}: [{code}] {text}")
    assert checked >= 5                                # 정규식이 망가져 아무것도 못 찾는 경우를 막는다
    assert not wrong, "성취기준 원문과 다른 인용:\n" + "\n".join(wrong)
