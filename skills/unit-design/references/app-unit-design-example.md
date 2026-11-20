# 단원 설계서 캔버스 예시 코드

`app-unit-design.md`의 부품을 실제로 쓴 예다. **마크업과 스타일 값을 그대로 쓰고 글만 바꾼다.** 새 색, 새 크기, 새 배치를 만들지 않는다. 그래야 누가 만들어도 같은 모양이 나온다.

고1 한국사1 '수취 체제와 신분제' 8차시(입력은 `unit-design-input.md`의 예시와 같다). A4 고정 4쪽이다. 상자는 쪽 경계에서 갈라지지 않고, 차시별 흐름 표는 3쪽 끝에서 행 단위로 나뉘어 4쪽에 머리 행을 다시 붙였다.

## project/canvas.json

`title`과 쪽 수만 바꾼다. 쪽이 늘면 `boards`에 `PageN.dc.html`을 x를 874px씩 늘려 더하고 `order`에도 넣는다. `designSystems`는 비워 둔다(학습지의 파랑 디자인 시스템을 설치하지 않는다).

```json
{
 "v": 3,
 "createdOnFiles": {
  "v": 1,
  "at": "2026-11-20T12:29:39Z"
 },
 "title": "단원 설계서 – 고1 한국사1 수취 체제와 신분제",
 "launch": {
  "view": "canvas"
 },
 "pages": [],
 "boards": {
  "Main.dc.html": {
   "x": 0,
   "y": 0,
   "w": 794,
   "h": 1123,
   "paper": "a4",
   "title": "1쪽"
  },
  "Page2.dc.html": {
   "x": 874,
   "y": 0,
   "w": 794,
   "h": 1123,
   "paper": "a4",
   "title": "2쪽"
  },
  "Page3.dc.html": {
   "x": 1748,
   "y": 0,
   "w": 794,
   "h": 1123,
   "paper": "a4",
   "title": "3쪽"
  },
  "Page4.dc.html": {
   "x": 2622,
   "y": 0,
   "w": 794,
   "h": 1123,
   "paper": "a4",
   "title": "4쪽"
  }
 },
 "order": [
  "Main.dc.html",
  "Page2.dc.html",
  "Page3.dc.html",
  "Page4.dc.html"
 ],
 "notes": {},
 "designSystems": []
}
```

## project/Main.dc.html — 1쪽: 머리 띠·기본 정보 줄, Ⅰ 바라는 결과(성취기준 표, 핵심 아이디어·내용 요소 상자, 핵심 개념, 영속적 이해·핵심 질문 상자)

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>단원 설계서 1쪽</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hahmlet:wght@600;700&amp;family=Noto+Sans+KR:wght@400;500;700&amp;display=swap">
<style>
body{margin:0}
</style>
</helmet>
<div style="width: 794px; height: 1123px; box-sizing: border-box; padding: 40px 48px 28px; background: #FFFFFF; font-family: 'Noto Sans KR','Malgun Gothic',sans-serif; color: #1B2A2A; display: flex; flex-direction: column; gap: 14px; overflow: hidden; word-break: keep-all">
<div style="position: relative; overflow: hidden; margin: -40px -48px 0; padding: 22px 56px 18px; background: linear-gradient(115deg, #0F4A46 0%, #1F7A72 100%); display: flex; flex-direction: column; gap: 10px">
<svg aria-hidden="true" width="260" height="128" viewBox="0 0 260 128" style="position: absolute; right: 0; bottom: 0"><circle cx="200" cy="104" r="58" fill="#FFFFFF" fill-opacity="0.08"/><circle cx="96" cy="124" r="36" fill="#FFFFFF" fill-opacity="0.06"/></svg>
<div style="position: relative; display: flex; align-items: center; gap: 6px"><span style="display: inline-block; background: #FFFFFF; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap">고1</span><span style="display: inline-block; background: #FFFFFF; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap">한국사1</span><span style="display: inline-block; background: #FFFFFF; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap">8차시</span>
<div style="flex: 1"></div><p style="margin: 0; font-size: 12px; color: #D6EEEA">백워드 설계 · 개념기반 탐구 · GRASPS</p></div>
<div style="position: relative; display: flex; flex-direction: column; gap: 4px">
<h1 style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 28px; font-weight: 700; letter-spacing: -0.6px; color: #FFFFFF">단원 설계서</h1><p style="margin: 0; font-size: 14px; font-weight: 500; color: #FFFFFF">Ⅱ. 근대 이전 한국사의 탐구 – 수취 체제와 신분제</p></div></div>
<div style="display: grid; grid-template-columns: 1fr 0.7fr 1.5fr 0.8fr; border: 1.5px solid #A8D2CB; border-radius: 10px; background: #FFFFFF; flex: none">
<div style="display: flex; flex-direction: column; gap: 2px; padding: 6px 10px; "><p style="margin: 0; font-size: 12px; font-weight: 700; color: #1F7A72">적용 교육과정</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">2022 개정</p></div>
<div style="display: flex; flex-direction: column; gap: 2px; padding: 6px 10px; border-left: 1px solid #A8D2CB;"><p style="margin: 0; font-size: 12px; font-weight: 700; color: #1F7A72">단원 차시</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">8차시</p></div>
<div style="display: flex; flex-direction: column; gap: 2px; padding: 6px 10px; border-left: 1px solid #A8D2CB;"><p style="margin: 0; font-size: 12px; font-weight: 700; color: #1F7A72">학기 차시 기준</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">48차시 (3학점 × 16회, 학교 편성 확인 필요)</p></div>
<div style="display: flex; flex-direction: column; gap: 2px; padding: 6px 10px; border-left: 1px solid #A8D2CB;"><p style="margin: 0; font-size: 12px; font-weight: 700; color: #1F7A72">작성일</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">2026-11-20</p></div></div>
<div style="flex: none; display: flex; flex-direction: column">
<div style="display: flex; align-items: stretch; background: #E5F2F0; border-radius: 10px; overflow: hidden; border-bottom: 2px solid #1F7A72; flex: none"><p style="margin: 0; width: 40px; background: #1F7A72; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">Ⅰ</p>
<h2 style="margin: 0; padding: 6px 12px; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 20px; font-weight: 700; color: #0F4A46; letter-spacing: -0.3px; flex: 1">바라는 결과</h2>
<div style="display: flex; align-items: center; gap: 6px; padding-right: 10px"><span style="display: inline-block; background: #FFFFFF; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #A8D2CB">1단계</span></div></div></div>
<div style="flex: none; display: flex; flex-direction: column">
<div style="display: flex; align-items: center; gap: 8px; flex: none">
<div style="width: 6px; height: 16px; border-radius: 3px; background: #1F7A72"></div>
<h3 style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; color: #0F4A46">성취기준 분석</h3></div></div>
<div style="flex: none; display: flex; flex-direction: column">
<div data-table="1" style="border: 1px solid #A8D2CB; border-top: none; flex: none">
<div data-head="1" style="display: grid; grid-template-columns: 46fr 26fr 28fr; border-top: 1px solid #A8D2CB">
<div style="background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">성취기준</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">알아야 할 것 (지식⋅이해)</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">할 수 있어야 할 것 (과정⋅기능)</div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 46fr 26fr 28fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: left; justify-content: flex-start; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><b style="color: #0F4A46">[10한사1-02-02]</b><br>근대 이전의 수취 체제 변화를 농업 중심의 경제생활과 관련하여 탐구한다.</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">조세·공납·역의 구조, 대동법·균역법의 내용</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">수취 제도의 변화가 농민의 경제생활에 미친 영향을 사료로 설명한다</div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 46fr 26fr 28fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: left; justify-content: flex-start; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><b style="color: #0F4A46">[10한사1-02-03]</b><br>근대 이전 사회 구조를 신분제를 중심으로 분석한다.</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">양천제와 반상제, 신분별 권리와 의무</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">신분에 따라 수취 부담이 어떻게 달랐는지 분석한다</div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 46fr 26fr 28fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: left; justify-content: flex-start; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><b style="color: #0F4A46">[10한사1-02-05]</b><br>근대 이전 한국사 주제를 설정하여 탐구하고, 그 결과를 다양한 방법으로 표현한다.</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">탐구 주제와 사료 출처 밝히기</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">탐구 결과를 전시 해설로 표현한다</div></div></div></div></div>
<div style="flex: none; display: flex; flex-direction: column">
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px">
<div style="border: 1.5px solid #A8D2CB; border-radius: 10px; overflow: hidden; background: #F4FAF9">
<div style="background: #0F4A46; padding: 6px 12px"><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 14px; font-weight: 700; color: #FFFFFF; white-space: nowrap">핵심 아이디어 (교육과정)</p></div>
<div style="padding: 8px 12px; display: flex; flex-direction: column; gap: 4px"><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">· 역사 자료를 분석하고 해석할 때에는 역사적 맥락을 고려해야 한다.</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">· 역사 학습은 인간의 삶을 이해하고 나의 삶을 성찰하는 과정이다.</p></div></div>
<div style="border: 1.5px solid #A8D2CB; border-radius: 10px; overflow: hidden; background: #F4FAF9">
<div style="background: #0F4A46; padding: 6px 12px"><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 14px; font-weight: 700; color: #FFFFFF; white-space: nowrap">내용 요소</p></div>
<div style="padding: 8px 12px; display: flex; flex-direction: column; gap: 4px">
<div style="display: grid; grid-template-columns: 64px 1fr; gap: 8px; align-items: start">
<div><span style="display: inline-block; background: #DCEFEC; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap">지식⋅이해</span></div><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">수취 체제와 경제생활, 신분제와 사회 구조, 근대 이전 한국사 주제 탐구</p></div>
<div style="display: grid; grid-template-columns: 64px 1fr; gap: 8px; align-items: start">
<div><span style="display: inline-block; background: #DCEFEC; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap">과정⋅기능</span></div><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">신뢰할 수 있는 자료를 증거로 선택하기, 역사적 맥락에서 자료를 비판적으로 분석하고 해석하기, 한국사 탐구 주제의 결론을 다양한 방식으로 표현하기</p></div>
<div style="display: grid; grid-template-columns: 64px 1fr; gap: 8px; align-items: start">
<div><span style="display: inline-block; background: #DCEFEC; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap">가치⋅태도</span></div><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">타인의 역사적 해석을 존중하는 태도</p></div></div></div></div></div>
<div style="flex: none; display: flex; flex-direction: column">
<div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap"><p style="margin: 0; font-size: 12px; font-weight: 700; color: #1F7A72">핵심 개념</p><span style="display: inline-block; background: #FFFFFF; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #A8D2CB">수취 체제</span> <span style="display: inline-block; background: #FFFFFF; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #A8D2CB">신분 구조</span> <span style="display: inline-block; background: #FFFFFF; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #A8D2CB">경제생활</span> <span style="display: inline-block; background: #FFFFFF; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #A8D2CB">변화와 지속</span></div></div>
<div style="flex: none; display: flex; flex-direction: column">
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; flex: none">
<div style="border: 2px solid #0F4A46; border-radius: 10px; padding: 10px 14px; background: #FFFFFF; display: flex; flex-direction: column; gap: 6px">
<div><span style="display: inline-block; background: #0F4A46; color: #FFFFFF; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap">영속적 이해 (일반화)</span></div><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 15px; font-weight: 600; line-height: 1.55; color: #1B2A2A">국가의 수취 제도는 농업 생산과 신분 구조에 맞추어 바뀌며, 같은 제도 변화도 신분에 따라 삶에 다른 무게로 작용한다.</p></div>
<div style="border: 2px solid #E6C383; border-radius: 10px; padding: 10px 14px; background: #FFF6E3; display: flex; flex-direction: column; gap: 6px">
<div><span style="display: inline-block; background: #A8670F; color: #FFFFFF; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap">핵심 질문</span></div><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; line-height: 1.5; color: #1B2A2A">세금 제도가 바뀌면 누구의 삶이 어떻게 달라지는가?</p><p style="margin: 0; font-size: 12px; color: #4F5F5D">답이 영속적 이해가 되는 질문 · 1차시에 열고 마지막 차시에 답합니다</p></div></div></div>
<div style="margin-top: auto; height: 30px; box-sizing: border-box; display: flex; align-items: center; gap: 10px; padding-top: 6px; border-top: 1.5px solid #A8D2CB; flex: none">
<div style="width: 22px; height: 4px; border-radius: 2px; background: #1F7A72"></div><p style="margin: 0; font-size: 12px; color: #4F5F5D; flex: 1">고1 한국사1 단원 설계서 · 2026-11-20</p><p style="margin: 0; font-size: 12px; font-weight: 700; color: #FFFFFF; background: #0F4A46; border-radius: 999px; padding: 2px 9px">1 / 4</p></div></div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{"$preview": {"width": 794, "height": 1123}}'>
class Component extends DCLogic {
renderVals() {
return {};
}
}
</script>
</body>
</html>
```

## project/Page2.dc.html — 2쪽: 단원명 줄, 탐구 질문 상자, Ⅱ 평가 계획(GRASPS 카드, 운영 상자, 채점 기준 요약 표)

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>단원 설계서 2쪽</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hahmlet:wght@600;700&amp;family=Noto+Sans+KR:wght@400;500;700&amp;display=swap">
<style>
body{margin:0}
</style>
</helmet>
<div style="width: 794px; height: 1123px; box-sizing: border-box; padding: 40px 48px 28px; background: #FFFFFF; font-family: 'Noto Sans KR','Malgun Gothic',sans-serif; color: #1B2A2A; display: flex; flex-direction: column; gap: 14px; overflow: hidden; word-break: keep-all">
<div style="display: flex; align-items: center; gap: 8px; height: 20px; flex: none; border-bottom: 1.5px solid #A8D2CB">
<div style="width: 6px; height: 14px; border-radius: 3px; background: #0F4A46"></div><p style="margin: 0; font-size: 12px; font-weight: 700; color: #0F4A46">단원 설계서</p><p style="margin: 0; font-size: 12px; color: #4F5F5D; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">고1 한국사1 · Ⅱ. 근대 이전 한국사의 탐구 – 수취 체제와 신분제</p></div>
<div style="flex: none; display: flex; flex-direction: column">
<div style="border: 1.5px solid #A8D2CB; border-radius: 10px; overflow: hidden; background: #F4FAF9">
<div style="background: #1F7A72; padding: 6px 12px"><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 14px; font-weight: 700; color: #FFFFFF; white-space: nowrap">탐구 질문</p></div>
<div style="padding: 4px 12px; display: flex; flex-direction: column; gap: 4px">
<div style="display: grid; grid-template-columns: 52px 1fr; gap: 10px; align-items: start; padding: 6px 0; ">
<div><span style="display: inline-block; background: #1F7A72; color: #FFFFFF; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap">사실</span></div>
<div><p style="margin: 0; font-size: 14px; line-height: 1.55; color: #1B2A2A">조선은 조세·공납·역으로 무엇을 어떻게 거두었는가?</p><p style="margin: 0; font-size: 14px; line-height: 1.55; color: #1B2A2A">조선의 신분은 어떻게 나뉘었는가?</p></div></div>
<div style="display: grid; grid-template-columns: 52px 1fr; gap: 10px; align-items: start; padding: 6px 0; border-top: 1px dashed #A8D2CB;">
<div><span style="display: inline-block; background: #1F7A72; color: #FFFFFF; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap">개념</span></div>
<div><p style="margin: 0; font-size: 14px; line-height: 1.55; color: #1B2A2A">수취 제도의 변화는 농민의 경제생활, 신분 구조와 어떻게 맞물렸는가?</p></div></div>
<div style="display: grid; grid-template-columns: 52px 1fr; gap: 10px; align-items: start; padding: 6px 0; border-top: 1px dashed #A8D2CB;">
<div><span style="display: inline-block; background: #0F4A46; color: #FFFFFF; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap">논쟁</span></div>
<div><p style="margin: 0; font-size: 14px; line-height: 1.55; color: #1B2A2A">대동법과 균역법은 백성의 부담을 덜었다고 볼 수 있는가?</p></div></div></div></div></div>
<div style="flex: none; display: flex; flex-direction: column">
<div style="display: flex; align-items: stretch; background: #E5F2F0; border-radius: 10px; overflow: hidden; border-bottom: 2px solid #1F7A72; flex: none"><p style="margin: 0; width: 40px; background: #1F7A72; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">Ⅱ</p>
<h2 style="margin: 0; padding: 6px 12px; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 20px; font-weight: 700; color: #0F4A46; letter-spacing: -0.3px; flex: 1">평가 계획</h2>
<div style="display: flex; align-items: center; gap: 6px; padding-right: 10px"><span style="display: inline-block; background: #FFFFFF; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #A8D2CB">2단계</span></div></div></div>
<div style="flex: none; display: flex; flex-direction: column">
<div style="display: flex; align-items: center; gap: 8px; flex: none">
<div style="width: 6px; height: 16px; border-radius: 3px; background: #1F7A72"></div>
<h3 style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; color: #0F4A46">GRASPS 수행과제</h3></div></div>
<div style="flex: none; display: flex; flex-direction: column">
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; flex: none">
<div style="border: 1.5px solid #A8D2CB; border-radius: 10px; background: #FFFFFF; padding: 10px 12px; display: grid; grid-template-columns: 34px 1fr; gap: 10px; align-items: start"><p style="margin: 0; width: 34px; height: 34px; border-radius: 8px; background: #0F4A46; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 20px; font-weight: 700; display: flex; align-items: center; justify-content: center">G</p>
<div style="display: flex; flex-direction: column; gap: 2px"><p style="margin: 0; font-size: 12px; font-weight: 700; color: #1F7A72">목표</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">관람객이 핵심 질문(세금 제도가 바뀌면 누구의 삶이 어떻게 달라지는가?)에 스스로 답할 수 있게 조선의 수취 제도 변화를 사료로 설명한다.</p></div></div>
<div style="border: 1.5px solid #A8D2CB; border-radius: 10px; background: #FFFFFF; padding: 10px 12px; display: grid; grid-template-columns: 34px 1fr; gap: 10px; align-items: start"><p style="margin: 0; width: 34px; height: 34px; border-radius: 8px; background: #0F4A46; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 20px; font-weight: 700; display: flex; align-items: center; justify-content: center">R</p>
<div style="display: flex; flex-direction: column; gap: 2px"><p style="margin: 0; font-size: 12px; font-weight: 700; color: #1F7A72">역할</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">학교 역사 주간 특별 전시의 해설 학예사</p></div></div>
<div style="border: 1.5px solid #A8D2CB; border-radius: 10px; background: #FFFFFF; padding: 10px 12px; display: grid; grid-template-columns: 34px 1fr; gap: 10px; align-items: start"><p style="margin: 0; width: 34px; height: 34px; border-radius: 8px; background: #0F4A46; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 20px; font-weight: 700; display: flex; align-items: center; justify-content: center">A</p>
<div style="display: flex; flex-direction: column; gap: 2px"><p style="margin: 0; font-size: 12px; font-weight: 700; color: #1F7A72">청중</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">같은 학년 학생 (수업 시간 안 갤러리 워크 관람객)</p></div></div>
<div style="border: 1.5px solid #A8D2CB; border-radius: 10px; background: #FFFFFF; padding: 10px 12px; display: grid; grid-template-columns: 34px 1fr; gap: 10px; align-items: start"><p style="margin: 0; width: 34px; height: 34px; border-radius: 8px; background: #0F4A46; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 20px; font-weight: 700; display: flex; align-items: center; justify-content: center">S</p>
<div style="display: flex; flex-direction: column; gap: 2px"><p style="margin: 0; font-size: 12px; font-weight: 700; color: #1F7A72">상황</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">역사 주간에 &#x27;조선 백성의 세금과 신분&#x27; 전시를 연다. 관람객은 대동법과 균역법이 모두의 부담을 덜었다고 생각하기 쉽다. 수업 시간 안에서 제공된 사료 자료집만 써야 한다.</p></div></div>
<div style="border: 1.5px solid #A8D2CB; border-radius: 10px; background: #FFFFFF; padding: 10px 12px; display: grid; grid-template-columns: 34px 1fr; gap: 10px; align-items: start"><p style="margin: 0; width: 34px; height: 34px; border-radius: 8px; background: #0F4A46; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 20px; font-weight: 700; display: flex; align-items: center; justify-content: center">P</p>
<div style="display: flex; flex-direction: column; gap: 2px"><p style="margin: 0; font-size: 12px; font-weight: 700; color: #1F7A72">결과물</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">전시 패널 해설문(사료 인용과 출처 표기, 신분별 관점 비교)과 개인 해설 카드</p></div></div>
<div style="border: 1.5px solid #A8D2CB; border-radius: 10px; background: #FFFFFF; padding: 10px 12px; display: grid; grid-template-columns: 34px 1fr; gap: 10px; align-items: start"><p style="margin: 0; width: 34px; height: 34px; border-radius: 8px; background: #0F4A46; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 20px; font-weight: 700; display: flex; align-items: center; justify-content: center">S</p>
<div style="display: flex; flex-direction: column; gap: 2px"><p style="margin: 0; font-size: 12px; font-weight: 700; color: #1F7A72">기준</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">사료를 증거로 골라 출처를 밝히는가, 수취 제도 변화와 신분 구조를 시대 맥락 속에서 연결하는가, 서로 다른 신분의 처지에서 해석을 비교하는가</p></div></div></div></div>
<div style="flex: none; display: flex; flex-direction: column">
<div style="display: flex; gap: 8px; align-items: flex-start; background: #FFF6E3; border: 1.5px solid #E6C383; border-radius: 10px; padding: 8px 12px">
<div style="flex: none"><span style="display: inline-block; background: #A8670F; color: #FFFFFF; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap">운영</span></div><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">수행과제는 수업 시간 안에서 초안 → 피드백 → 수정으로 마칩니다. 모둠으로 하면 개인 산출물을 따로 받습니다. 배점과 단계 점수는 학교 학업성적관리규정에 맞춰 채점기준표에서 정합니다.</p></div></div>
<div style="flex: none; display: flex; flex-direction: column">
<div style="display: flex; align-items: center; gap: 8px; flex: none">
<div style="width: 6px; height: 16px; border-radius: 3px; background: #1F7A72"></div>
<h3 style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; color: #0F4A46">채점 기준 요약</h3></div></div>
<div style="flex: none; display: flex; flex-direction: column">
<div data-table="1" style="border: 1px solid #A8D2CB; border-top: none; flex: none">
<div data-head="1" style="display: grid; grid-template-columns: 22fr 78fr; border-top: 1px solid #A8D2CB">
<div style="background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">평가 요소</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">보는 것</div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 22fr 78fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><b style="color: #0F4A46">사료 활용</b></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: left; justify-content: flex-start; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">주장에 맞는 사료를 골라 출처를 밝히고 사료가 말하는 것과 말하지 않는 것을 구별함</div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 22fr 78fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><b style="color: #0F4A46">맥락적 설명</b></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: left; justify-content: flex-start; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">제도 변화의 배경과 결과를 농업 경제와 신분 구조에 연결해 설명함</div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 22fr 78fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><b style="color: #0F4A46">관점 비교</b></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: left; justify-content: flex-start; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">양반·상민·노비 등 처지에 따라 부담이 어떻게 달랐는지 근거를 들어 비교함</div></div></div></div></div>
<div style="margin-top: auto; height: 30px; box-sizing: border-box; display: flex; align-items: center; gap: 10px; padding-top: 6px; border-top: 1.5px solid #A8D2CB; flex: none">
<div style="width: 22px; height: 4px; border-radius: 2px; background: #1F7A72"></div><p style="margin: 0; font-size: 12px; color: #4F5F5D; flex: 1">고1 한국사1 단원 설계서 · 2026-11-20</p><p style="margin: 0; font-size: 12px; font-weight: 700; color: #FFFFFF; background: #0F4A46; border-radius: 999px; padding: 2px 9px">2 / 4</p></div></div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{"$preview": {"width": 794, "height": 1123}}'>
class Component extends DCLogic {
renderVals() {
return {};
}
}
</script>
</body>
</html>
```

## project/Page3.dc.html — 3쪽: 평가 배치 줄·평가 배치 표, Ⅲ 차시별 흐름 표(1~6차시)

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>단원 설계서 3쪽</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hahmlet:wght@600;700&amp;family=Noto+Sans+KR:wght@400;500;700&amp;display=swap">
<style>
body{margin:0}
</style>
</helmet>
<div style="width: 794px; height: 1123px; box-sizing: border-box; padding: 40px 48px 28px; background: #FFFFFF; font-family: 'Noto Sans KR','Malgun Gothic',sans-serif; color: #1B2A2A; display: flex; flex-direction: column; gap: 14px; overflow: hidden; word-break: keep-all">
<div style="display: flex; align-items: center; gap: 8px; height: 20px; flex: none; border-bottom: 1.5px solid #A8D2CB">
<div style="width: 6px; height: 14px; border-radius: 3px; background: #0F4A46"></div><p style="margin: 0; font-size: 12px; font-weight: 700; color: #0F4A46">단원 설계서</p><p style="margin: 0; font-size: 12px; color: #4F5F5D; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">고1 한국사1 · Ⅱ. 근대 이전 한국사의 탐구 – 수취 체제와 신분제</p></div>
<div style="flex: none; display: flex; flex-direction: column">
<div style="display: flex; align-items: center; gap: 8px; flex: none">
<div style="width: 6px; height: 16px; border-radius: 3px; background: #1F7A72"></div>
<h3 style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; color: #0F4A46">평가 배치</h3></div></div>
<div style="flex: none; display: flex; flex-direction: column">
<div style="border: 1.5px solid #A8D2CB; border-radius: 10px; background: #F4FAF9; padding: 12px 14px; display: flex; flex-direction: column; gap: 10px; flex: none">
<div style="position: relative; display: grid; grid-template-columns: repeat(8, 1fr); gap: 4px">
<div style="position: absolute; left: 6%; right: 6%; top: 13px; height: 2px; background: #A8D2CB"></div>
<div style="display: flex; flex-direction: column; align-items: center; gap: 6px"><p style="margin: 0; width: 28px; height: 28px; box-sizing: border-box; border-radius: 999px; background: #0F4A46; border: 2px solid #0F4A46; color: #FFFFFF; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; position: relative">1</p>
<div><span style="display: inline-block; background: #FFFFFF; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #0F4A46">진단</span></div></div>
<div style="display: flex; flex-direction: column; align-items: center; gap: 6px"><p style="margin: 0; width: 28px; height: 28px; box-sizing: border-box; border-radius: 999px; background: #FFFFFF; border: 2px solid #0F4A46; color: #0F4A46; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; position: relative">2</p><p style="margin: 0; font-size: 12px; color: #4F5F5D">수업</p></div>
<div style="display: flex; flex-direction: column; align-items: center; gap: 6px"><p style="margin: 0; width: 28px; height: 28px; box-sizing: border-box; border-radius: 999px; background: #0F4A46; border: 2px solid #0F4A46; color: #FFFFFF; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; position: relative">3</p>
<div><span style="display: inline-block; background: #DCEFEC; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #A8D2CB">형성</span></div></div>
<div style="display: flex; flex-direction: column; align-items: center; gap: 6px"><p style="margin: 0; width: 28px; height: 28px; box-sizing: border-box; border-radius: 999px; background: #FFFFFF; border: 2px solid #0F4A46; color: #0F4A46; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; position: relative">4</p><p style="margin: 0; font-size: 12px; color: #4F5F5D">수업</p></div>
<div style="display: flex; flex-direction: column; align-items: center; gap: 6px"><p style="margin: 0; width: 28px; height: 28px; box-sizing: border-box; border-radius: 999px; background: #0F4A46; border: 2px solid #0F4A46; color: #FFFFFF; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; position: relative">5</p>
<div><span style="display: inline-block; background: #DCEFEC; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #A8D2CB">형성</span></div></div>
<div style="display: flex; flex-direction: column; align-items: center; gap: 6px"><p style="margin: 0; width: 28px; height: 28px; box-sizing: border-box; border-radius: 999px; background: #FFFFFF; border: 2px solid #0F4A46; color: #0F4A46; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; position: relative">6</p><p style="margin: 0; font-size: 12px; color: #4F5F5D">수업</p></div>
<div style="display: flex; flex-direction: column; align-items: center; gap: 6px"><p style="margin: 0; width: 28px; height: 28px; box-sizing: border-box; border-radius: 999px; background: #0F4A46; border: 2px solid #0F4A46; color: #FFFFFF; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; position: relative">7</p>
<div><span style="display: inline-block; background: #0F4A46; color: #FFFFFF; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap">수행</span></div></div>
<div style="display: flex; flex-direction: column; align-items: center; gap: 6px"><p style="margin: 0; width: 28px; height: 28px; box-sizing: border-box; border-radius: 999px; background: #0F4A46; border: 2px solid #0F4A46; color: #FFFFFF; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; position: relative">8</p>
<div><span style="display: inline-block; background: #0F4A46; color: #FFFFFF; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap">수행</span></div></div></div>
<div style="display: flex; align-items: center; gap: 10px; border-top: 1px dashed #A8D2CB; padding-top: 8px"><p style="margin: 0; font-size: 12px; font-weight: 700; color: #1F7A72">단원 밖</p>
<div style="display: flex; align-items: center; gap: 6px"><span style="display: inline-block; background: #FFF6E3; color: #A8670F; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #E6C383">지필</span><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">정기시험 · 서술형 1문항</p></div>
<div style="flex: 1"></div><span style="display: inline-block; background: #FFFFFF; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #0F4A46">진단</span> <span style="display: inline-block; background: #DCEFEC; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #A8D2CB">형성</span> <span style="display: inline-block; background: #0F4A46; color: #FFFFFF; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap">수행</span> <span style="display: inline-block; background: #FFF6E3; color: #A8670F; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #E6C383">지필</span></div></div></div>
<div style="flex: none; display: flex; flex-direction: column">
<div data-table="1" style="border: 1px solid #A8D2CB; border-top: none; flex: none">
<div data-head="1" style="display: grid; grid-template-columns: 11fr 11fr 26fr 30fr 22fr; border-top: 1px solid #A8D2CB">
<div style="background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">차시</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">종류</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">방법</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">확인할 것</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">성취기준</div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 11fr 11fr 26fr 30fr 22fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><b>1</b></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="display: inline-block; background: #FFFFFF; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #0F4A46">진단</span></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">사전 질문지</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">세금·신분에 대한 선행 지식과 오개념</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="white-space: nowrap">[10한사1-02-02]</span></div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 11fr 11fr 26fr 30fr 22fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><b>3</b></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="display: inline-block; background: #DCEFEC; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #A8D2CB">형성</span></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">출구 카드 (형성용, 점수 없음)</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">공납의 폐단과 대동법의 의도 설명</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="white-space: nowrap">[10한사1-02-02]</span></div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 11fr 11fr 26fr 30fr 22fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><b>5</b></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="display: inline-block; background: #DCEFEC; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #A8D2CB">형성</span></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">사료 메모 짝 점검 (중간 산출물, 형성용)</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">신분별 의무와 부담 분석</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="white-space: nowrap">[10한사1-02-03]</span></div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 11fr 11fr 26fr 30fr 22fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><b>7~8</b></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="display: inline-block; background: #0F4A46; color: #FFFFFF; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap">수행</span></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">GRASPS 전시 해설 (개인 해설 카드 포함)</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">사료 근거, 맥락적 설명, 관점 비교</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="white-space: nowrap">[10한사1-02-02]</span><br><span style="white-space: nowrap">[10한사1-02-03]</span><br><span style="white-space: nowrap">[10한사1-02-05]</span></div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 11fr 11fr 26fr 30fr 22fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><b>정기시험</b></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="display: inline-block; background: #FFF6E3; color: #A8670F; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #E6C383">지필</span></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">서술형 1문항</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">대동법 시행 전후 농민 부담 비교</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="white-space: nowrap">[10한사1-02-02]</span></div></div></div></div></div>
<div style="flex: none; display: flex; flex-direction: column">
<div style="display: flex; align-items: stretch; background: #E5F2F0; border-radius: 10px; overflow: hidden; border-bottom: 2px solid #1F7A72; flex: none"><p style="margin: 0; width: 40px; background: #1F7A72; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">Ⅲ</p>
<h2 style="margin: 0; padding: 6px 12px; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 20px; font-weight: 700; color: #0F4A46; letter-spacing: -0.3px; flex: 1">차시별 흐름</h2>
<div style="display: flex; align-items: center; gap: 6px; padding-right: 10px"><span style="display: inline-block; background: #FFFFFF; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #A8D2CB">3단계</span></div></div></div>
<div style="flex: none; display: flex; flex-direction: column">
<div data-table="1" style="border: 1px solid #A8D2CB; border-top: none; flex: none">
<div data-head="1" style="display: grid; grid-template-columns: 9fr 33fr 44fr 14fr; border-top: 1px solid #A8D2CB">
<div style="background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">차시</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">학습 목표 · 성취기준</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">주요 활동</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">평가</div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 9fr 33fr 44fr 14fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 20px; font-weight: 700; color: #0F4A46">1</p></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><p style="margin: 0 0 3px; font-size: 12px; line-height: 1.5">수취 제도와 신분에 대해 아는 것을 말할 수 있다.</p><span style="font-size: 12px; color: #1F7A72; font-weight: 500; white-space: nowrap">[10한사1-02-02]</span></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: left; justify-content: flex-start; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">
<div style="text-align: left"><p style="margin: 0; font-size: 12px; line-height: 1.55; font-weight: 700; color: #0F4A46">◉ 핵심 질문 열기</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">○ 수행과제와 채점 기준 미리 보기</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">○ 사전 질문지</p></div></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="display: inline-block; background: #FFFFFF; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #0F4A46">진단</span></div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 9fr 33fr 44fr 14fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 20px; font-weight: 700; color: #0F4A46">2</p></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><p style="margin: 0 0 3px; font-size: 12px; line-height: 1.5">조세·공납·역의 구조를 설명할 수 있다.</p><span style="font-size: 12px; color: #1F7A72; font-weight: 500; white-space: nowrap">[10한사1-02-02]</span></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: left; justify-content: flex-start; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">
<div style="text-align: left"><p style="margin: 0; font-size: 12px; line-height: 1.55; font-weight: 700; color: #0F4A46">◉ 사실 질문: 무엇을 어떻게 거두었나</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">○ 수취 구조도 그리기</p></div></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="font-size: 12px; color: #4F5F5D">관찰</span></div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 9fr 33fr 44fr 14fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 20px; font-weight: 700; color: #0F4A46">3</p></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><p style="margin: 0 0 3px; font-size: 12px; line-height: 1.5">공납의 폐단과 대동법의 의도를 사료로 설명할 수 있다.</p><span style="font-size: 12px; color: #1F7A72; font-weight: 500; white-space: nowrap">[10한사1-02-02]</span></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: left; justify-content: flex-start; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">
<div style="text-align: left"><p style="margin: 0; font-size: 12px; line-height: 1.55; font-weight: 700; color: #0F4A46">◉ 방납 관련 사료 읽기</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">○ 대동법 시행 전후 비교표</p></div></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="display: inline-block; background: #DCEFEC; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #A8D2CB">형성</span></div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 9fr 33fr 44fr 14fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 20px; font-weight: 700; color: #0F4A46">4</p></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><p style="margin: 0 0 3px; font-size: 12px; line-height: 1.5">군역의 변화와 균역법의 결과를 설명할 수 있다.</p><span style="font-size: 12px; color: #1F7A72; font-weight: 500; white-space: nowrap">[10한사1-02-02]</span></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: left; justify-content: flex-start; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">
<div style="text-align: left"><p style="margin: 0; font-size: 12px; line-height: 1.55; font-weight: 700; color: #0F4A46">◉ 3차시 출구 카드 피드백 보고 고치기 (10분)</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">○ 군포 부담 사료 분석</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">○ 균역법 이후 부족분은 누가 메웠나</p></div></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="font-size: 12px; color: #4F5F5D">관찰</span></div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 9fr 33fr 44fr 14fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 20px; font-weight: 700; color: #0F4A46">5</p></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><p style="margin: 0 0 3px; font-size: 12px; line-height: 1.5">신분에 따라 의무와 부담이 어떻게 달랐는지 분석할 수 있다.</p><span style="font-size: 12px; color: #1F7A72; font-weight: 500; white-space: nowrap">[10한사1-02-03]</span></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: left; justify-content: flex-start; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">
<div style="text-align: left"><p style="margin: 0; font-size: 12px; line-height: 1.55; font-weight: 700; color: #0F4A46">◉ 개념 질문: 수취와 신분은 어떻게 맞물렸나</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">○ 신분별 처지 사료 읽고 사료 메모 쓰기 (해설문 재료)</p></div></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="display: inline-block; background: #DCEFEC; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #A8D2CB">형성</span></div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 9fr 33fr 44fr 14fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 20px; font-weight: 700; color: #0F4A46">6</p></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><p style="margin: 0 0 3px; font-size: 12px; line-height: 1.5">개혁의 성과를 두고 서로 다른 해석을 비교할 수 있다.</p><span style="font-size: 12px; color: #1F7A72; font-weight: 500; white-space: nowrap">[10한사1-02-02]</span> <span style="font-size: 12px; color: #1F7A72; font-weight: 500; white-space: nowrap">[10한사1-02-03]</span></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: left; justify-content: flex-start; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">
<div style="text-align: left"><p style="margin: 0; font-size: 12px; line-height: 1.55; font-weight: 700; color: #0F4A46">◉ 사료 메모 피드백 보고 고치기 (10분)</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">○ 논쟁 질문 토론: 개혁은 부담을 덜었나</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">○ 같은 사료, 다른 해석 비교</p></div></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="font-size: 12px; color: #4F5F5D">관찰</span></div></div></div></div></div>
<div style="margin-top: auto; height: 30px; box-sizing: border-box; display: flex; align-items: center; gap: 10px; padding-top: 6px; border-top: 1.5px solid #A8D2CB; flex: none">
<div style="width: 22px; height: 4px; border-radius: 2px; background: #1F7A72"></div><p style="margin: 0; font-size: 12px; color: #4F5F5D; flex: 1">고1 한국사1 단원 설계서 · 2026-11-20</p><p style="margin: 0; font-size: 12px; font-weight: 700; color: #FFFFFF; background: #0F4A46; border-radius: 999px; padding: 2px 9px">3 / 4</p></div></div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{"$preview": {"width": 794, "height": 1123}}'>
class Component extends DCLogic {
renderVals() {
return {};
}
}
</script>
</body>
</html>
```

## project/Page4.dc.html — 4쪽: 차시별 흐름 표의 나머지 행(머리 행 다시 붙임), Ⅳ 다음 단계

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>단원 설계서 4쪽</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hahmlet:wght@600;700&amp;family=Noto+Sans+KR:wght@400;500;700&amp;display=swap">
<style>
body{margin:0}
</style>
</helmet>
<div style="width: 794px; height: 1123px; box-sizing: border-box; padding: 40px 48px 28px; background: #FFFFFF; font-family: 'Noto Sans KR','Malgun Gothic',sans-serif; color: #1B2A2A; display: flex; flex-direction: column; gap: 14px; overflow: hidden; word-break: keep-all">
<div style="display: flex; align-items: center; gap: 8px; height: 20px; flex: none; border-bottom: 1.5px solid #A8D2CB">
<div style="width: 6px; height: 14px; border-radius: 3px; background: #0F4A46"></div><p style="margin: 0; font-size: 12px; font-weight: 700; color: #0F4A46">단원 설계서</p><p style="margin: 0; font-size: 12px; color: #4F5F5D; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">고1 한국사1 · Ⅱ. 근대 이전 한국사의 탐구 – 수취 체제와 신분제</p></div>
<div style="flex: none; display: flex; flex-direction: column">
<div data-table="1" style="border: 1px solid #A8D2CB; border-top: none; flex: none">
<div data-head="1" style="display: grid; grid-template-columns: 9fr 33fr 44fr 14fr; border-top: 1px solid #A8D2CB">
<div style="background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">차시</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">학습 목표 · 성취기준</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">주요 활동</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">평가</div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 9fr 33fr 44fr 14fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 20px; font-weight: 700; color: #0F4A46">7</p></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><p style="margin: 0 0 3px; font-size: 12px; line-height: 1.5">탐구 주제를 정하고 사료로 해설문 초안을 쓸 수 있다.</p><span style="font-size: 12px; color: #1F7A72; font-weight: 500; white-space: nowrap">[10한사1-02-02]</span> <span style="font-size: 12px; color: #1F7A72; font-weight: 500; white-space: nowrap">[10한사1-02-03]</span> <span style="font-size: 12px; color: #1F7A72; font-weight: 500; white-space: nowrap">[10한사1-02-05]</span></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: left; justify-content: flex-start; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">
<div style="text-align: left"><p style="margin: 0; font-size: 12px; line-height: 1.55; font-weight: 700; color: #0F4A46">◉ 예시 해설문으로 기준 읽기</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">○ 사료 메모를 모아 해설문 초안 쓰기</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">○ 채점 기준으로 동료 피드백</p></div></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="display: inline-block; background: #0F4A46; color: #FFFFFF; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap">수행</span></div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 9fr 33fr 44fr 14fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 20px; font-weight: 700; color: #0F4A46">8</p></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><p style="margin: 0 0 3px; font-size: 12px; line-height: 1.5">해설문을 고쳐 전시하고 관람객에게 설명할 수 있다.</p><span style="font-size: 12px; color: #1F7A72; font-weight: 500; white-space: nowrap">[10한사1-02-02]</span> <span style="font-size: 12px; color: #1F7A72; font-weight: 500; white-space: nowrap">[10한사1-02-03]</span> <span style="font-size: 12px; color: #1F7A72; font-weight: 500; white-space: nowrap">[10한사1-02-05]</span></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: left; justify-content: flex-start; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">
<div style="text-align: left"><p style="margin: 0; font-size: 12px; line-height: 1.55; font-weight: 700; color: #0F4A46">◉ 수정본 전시와 갤러리 워크</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">○ 개인 해설 카드</p><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #1B2A2A">○ 핵심 질문에 한 문장으로 답하기</p></div></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="display: inline-block; background: #0F4A46; color: #FFFFFF; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap">수행</span></div></div></div></div></div>
<div style="flex: none; display: flex; flex-direction: column">
<div style="display: flex; align-items: stretch; background: #E5F2F0; border-radius: 10px; overflow: hidden; border-bottom: 2px solid #1F7A72; flex: none"><p style="margin: 0; width: 40px; background: #1F7A72; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">Ⅳ</p>
<h2 style="margin: 0; padding: 6px 12px; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 20px; font-weight: 700; color: #0F4A46; letter-spacing: -0.3px; flex: 1">다음 단계</h2>
<div style="display: flex; align-items: center; gap: 6px; padding-right: 10px"><span style="display: inline-block; background: #FFFFFF; color: #0F4A46; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 9px; border-radius: 999px; white-space: nowrap; border: 1.5px solid #A8D2CB">다른 스킬로</span></div></div></div>
<div style="flex: none; display: flex; flex-direction: column"><p style="margin: 0; font-size: 12px; line-height: 1.55; color: #4F5F5D">아래 요청 문장을 그대로 보내면 이 설계서의 값을 넘겨받아 이어서 만듭니다.</p></div>
<div style="flex: none; display: flex; flex-direction: column">
<div data-table="1" style="border: 1px solid #A8D2CB; border-top: none; flex: none">
<div data-head="1" style="display: grid; grid-template-columns: 24fr 40fr 36fr; border-top: 1px solid #A8D2CB">
<div style="background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">다음에 만들 것</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">이렇게 요청하세요</div></div>
<div style="border-left: 1px solid #A8D2CB; background: #E5F2F0; color: #0F4A46; font-weight: 700; justify-content: center; text-align: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">넘길 내용</div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 24fr 40fr 36fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><b style="color: #0F4A46">지도안 (lesson-plan)</b></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="display: inline-block; background: #FFEFC2; border-bottom: 1.5px solid #1B2A2A; padding: 2px 6px; font-size: 12px; font-weight: 700">지도안: 단원 설계의 3차시 써 줘</span></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">3차시 학습 목표, 사료, 출구 카드, [10한사1-02-02]</div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 24fr 40fr 36fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><b style="color: #0F4A46">수업 PPT (class-slides)</b></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="display: inline-block; background: #FFEFC2; border-bottom: 1.5px solid #1B2A2A; padding: 2px 6px; font-size: 12px; font-weight: 700">PPT: 단원 설계의 6차시 토론 수업</span></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">논쟁 질문, 해석 비교 활동 순서</div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 24fr 40fr 36fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><b style="color: #0F4A46">학습지 (worksheet)</b></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="display: inline-block; background: #FFEFC2; border-bottom: 1.5px solid #1B2A2A; padding: 2px 6px; font-size: 12px; font-weight: 700">학습지: 5차시 신분별 처지 사료 학습지</span></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">5차시 활동과 형성평가</div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 24fr 40fr 36fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><b style="color: #0F4A46">채점기준표 (rubric)</b></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="display: inline-block; background: #FFEFC2; border-bottom: 1.5px solid #1B2A2A; padding: 2px 6px; font-size: 12px; font-weight: 700">수행평가: 단원 설계의 전시 해설 과제로 채점기준표</span></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">GRASPS, 기준(S), 평가 요소 3개, 성취기준 3개</div></div></div>
<div data-row="1" style="display: grid; grid-template-columns: 24fr 40fr 36fr; border-top: 1px solid #A8D2CB">
<div style="background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><b style="color: #0F4A46">문항 (assessment-items)</b></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit"><span style="display: inline-block; background: #FFEFC2; border-bottom: 1.5px solid #1B2A2A; padding: 2px 6px; font-size: 12px; font-weight: 700">문항: 대동법 전후 비교 서술형 1문항</span></div></div>
<div style="border-left: 1px solid #A8D2CB; background: #FFFFFF; color: #1B2A2A; text-align: center; justify-content: center; font-size: 12px; line-height: 1.5; padding: 5px 7px; min-width: 0; display: flex; flex-direction: column; align-items: stretch; overflow-wrap: anywhere">
<div style="text-align: inherit">평가 배치의 지필 칸, 영속적 이해, [10한사1-02-02]</div></div></div></div></div>
<div style="margin-top: auto; height: 30px; box-sizing: border-box; display: flex; align-items: center; gap: 10px; padding-top: 6px; border-top: 1.5px solid #A8D2CB; flex: none">
<div style="width: 22px; height: 4px; border-radius: 2px; background: #1F7A72"></div><p style="margin: 0; font-size: 12px; color: #4F5F5D; flex: 1">고1 한국사1 단원 설계서 · 2026-11-20</p><p style="margin: 0; font-size: 12px; font-weight: 700; color: #FFFFFF; background: #0F4A46; border-radius: 999px; padding: 2px 9px">4 / 4</p></div></div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{"$preview": {"width": 794, "height": 1123}}'>
class Component extends DCLogic {
renderVals() {
return {};
}
}
</script>
</body>
</html>
```
