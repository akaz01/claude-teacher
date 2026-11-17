# 기본 양식에 없는 칸까지 든 지도안 (make_hwpx.py)

SKILL.md 9절의 "기본 양식으로 담기 어려울 때"에만 쓴다. 세안, 공개수업처럼 교사가 기본 양식에 없는 칸(교과 역량 머리칸, 활동표 평가 칸, 판서 계획 등)까지 든 지도안을 원할 때다. 실행은 `python scripts/make_hwpx.py 지도안.json 지도안.hwpx`이다.

표가 넓으므로 `"margins": "narrow"`를 쓴다. 칸 합치기는 HTML 표처럼 쓴다: 합쳐서 가려지는 칸은 행에서 **빼고 적는다**.

```json
{
  "title": "과학과 교수·학습 과정안",
  "margins": "narrow",
  "page": "compact",
  "blocks": [
    {"type": "table", "widths": [12, 21, 12, 21, 12, 22], "rows": [
      [{"text": "단원", "shade": true, "bold": true, "align": "center"}, {"text": "물질의 상태 변화", "align": "center"},
       {"text": "대상", "shade": true, "bold": true, "align": "center"}, {"text": "○학년 ○반", "align": "center"},
       {"text": "일시", "shade": true, "bold": true, "align": "center"}, {"text": "2026. ○. ○.(○) ○교시", "align": "center"}],
      [{"text": "교과 역량", "shade": true, "bold": true, "align": "center"},
       {"text": "[확인 필요]", "colspan": 5, "align": "center"}],
      [{"text": "내용 영역", "shade": true, "bold": true, "align": "center"},
       {"text": "물질", "colspan": 5, "align": "center"}],
      [{"text": "핵심 아이디어", "shade": true, "bold": true, "align": "center"},
       {"text": "물질은 여러 가지 상태로 존재하며, 구성 입자의 운동에 따라 물질의 상태와 물리적 성질이 변한다.", "colspan": 5, "align": "center"}],
      [{"text": "내용 요소", "shade": true, "bold": true, "align": "center"},
       {"text": "입자 운동", "colspan": 5, "align": "center"}],
      [{"text": "성취기준", "shade": true, "bold": true, "align": "center"},
       {"text": "[9과04-01] 확산 및 증발 현상을 관찰하여 물질을 구성하는 입자가 운동하고 있음을 추론할 수 있다.", "colspan": 5, "align": "center"}],
      [{"text": "탐구 질문", "shade": true, "bold": true, "align": "center"},
       {"text": "바람이 없는 방에서도 냄새가 퍼지는 까닭을 어떻게 설명할 수 있을까?", "colspan": 5, "align": "center"}],
      [{"text": "학습 목표", "shade": true, "bold": true, "align": "center"},
       {"text": "확산 현상을 관찰하여 입자가 운동하고 있음을 추론할 수 있다.", "colspan": 5, "align": "center"}],
      [{"text": "학습 주제", "shade": true, "bold": true, "align": "center"},
       {"text": "냄새가 퍼지는 까닭 입자로 설명하기", "colspan": 5, "align": "center"}]
    ]},
    {"type": "heading", "text": "교수·학습 활동", "level": 2},
    {"type": "table", "header_rows": 2, "widths": [7, 7, 24, 24, 10, 17, 11], "rows": [
      [{"text": "단계", "rowspan": 2}, {"text": "학습 형태", "rowspan": 2}, {"text": "교수·학습 활동", "colspan": 2},
       {"text": "시간(분)", "rowspan": 2}, {"text": "자료(▣) 및 유의점(※)", "rowspan": 2}, {"text": "평가", "rowspan": 2}],
      ["교사", "학생"],
      [{"text": "도입", "rowspan": 2, "align": "center"}, {"text": "전체", "align": "center"},
       {"text": "◉ 동기 유발\n○ \"향수를 뿌리면 왜 멀리서도 냄새가 날까요?\"", "align": "center"},
       {"text": "- 냄새가 퍼져서요.", "align": "center"}, {"text": "3", "align": "center"},
       {"text": "▣ 향수병", "align": "center"}, {"text": "", "align": "center"}],
      [{"text": "전체", "align": "center"}, {"text": "◉ 탐구 질문 확인", "align": "center"},
       {"text": "- 함께 읽는다.", "align": "center"}, {"text": "2", "align": "center"},
       {"text": "", "align": "center"}, {"text": "", "align": "center"}],
      [{"text": "정리", "align": "center"}, {"text": "개인", "align": "center"},
       {"text": "◉ 탐구 질문에 답하기\n○ \"처음 질문에 한 문장으로 답해 봅시다.\"", "align": "center"},
       {"text": "- 쪽지에 쓴다.", "align": "center"}, {"text": "5", "align": "center"},
       {"text": "▣ 쪽지\n※ 나가면서 걷는다.", "align": "center"}, {"text": "쪽지", "align": "center"}]
    ]},
    {"type": "heading", "text": "평가 계획", "level": 2},
    {"type": "table", "header": ["평가 요소", "평가 방법", "상", "중", "하", "피드백(하)"],
     "widths": [15, 10, 20, 20, 15, 20], "rows": [
      [{"text": "입자 운동으로 확산 설명", "align": "center"}, {"text": "활동지", "align": "center"},
       {"text": "입자 운동으로 설명하고, 온도가 다른 새 상황에도 같은 설명을 쓴다", "align": "center"},
       {"text": "향수 냄새가 퍼지는 까닭을 입자 운동으로 설명한다", "align": "center"},
       {"text": "모형 그림을 보며 입자가 움직인다고 말한다", "align": "center"},
       {"text": "모형 그림을 순서대로 짚게 한 뒤 짝에게 다시 설명하게 한다", "align": "center"}]
    ]},
    {"type": "heading", "text": "판서 계획", "level": 2},
    {"type": "table", "widths": [45, 55], "rows": [
      [{"text": "물질의 상태 변화 (○/○차시)", "colspan": 2, "shade": true, "bold": true, "align": "center"}],
      [{"text": "탐구 질문: 바람이 없는 방에서도 냄새가 퍼지는 까닭을 어떻게 설명할 수 있을까?\n1. 냄새가 퍼지는 모습 관찰\n2. 입자 모형으로 그리기\n3. 탐구 질문에 한 문장으로 답하기", "align": "center"},
       {"text": "확산: 물질을 이루는 입자가 스스로 운동하여 퍼져 나가는 현상\n(학생이 그린 모형을 붙일 자리)", "align": "center"}]
    ]}
  ]
}
```

위 예시의 활동표는 형식을 보이려고 전개를 줄였다. 실제로는 시간 합을 차시 시간에 맞춘다. 단원 칸은 교과서 단원명으로 바꾼다.

- 칸 객체에 쓸 수 있는 항목: `text`, `rowspan`, `colspan`, `shade`(음영), `bold`, `align`(left/center/right), `valign`(top/center), `lines`(빈 칸 높이, 줄 수). 생성기의 칸 기본 정렬은 왼쪽이므로 머리칸이 아닌 칸에는 `"align": "center"`를 적는다.
- `header_rows`: `header`를 쓰지 않으면 `rows`의 앞쪽 몇 줄을 머리행으로 할지 정한다. `header`와 함께 쓰면 그 아래에 더할 머리행 수다. 머리행은 음영, 굵게, 가운데이고 쪽이 넘어가면 다음 쪽에 되풀이된다.
- **열 너비**: 합은 100으로 맞춘다. 분리형 7열은 `[7, 7, 24, 24, 10, 17, 11]`을 쓴다. 평가 칸을 뺀 분리형은 `[8, 7, 28, 28, 10, 19]`처럼 쓴다. "시간(분)"이 한 줄에 들려면 좁은 여백에서 시간 열이 10 이상이어야 한다. 표가 좁아 칸을 줄여야 하면 머리칸을 `시간\n(분)`으로 쓰고 6까지 줄인다.
- **표가 쪽을 넘을 때**: 높이 약 53mm 이하의 짧은 표와 머리행이 있는 약 106mm 이하의 표(평가 계획표 등)는 나뉘지 않고 통째로 다음 쪽으로 옮겨진다. 긴 활동표는 행 단위로 나뉘고 행 하나는 쪽 경계에서 갈라지지 않지만, 세로로 합친 단계 칸은 이름이 첫 쪽에만 보인다. 그래서 아래처럼 쓴다.
  - 한 행에 한 활동만 쓰고, 세부 활동이 많으면 행을 나눈다.
  - 단계가 바뀌는 곳에서 끊는 편이 좋으면 표를 둘로 나누고 그 사이에 `{"type": "page_break"}`를 넣는다. 둘째 표에도 머리행을 다시 쓴다.
  - 쪽 경계의 모습은 파일을 만든 뒤 한글에서 확인해 달라고 알린다.
