# A4 디자인 학습지 예시 코드 (하우스 스타일 판 3)

`app-worksheet.md`의 부품을 실제로 쓴 예다. **마크업과 스타일 값을 그대로 쓰고 글·주제·용어·문항과 교과 아이콘만 바꾼다.** 새 색, 새 크기, 새 배치를 만들지 않는다. 그래야 누가 만들어도 같은 모양이 나온다.

- 예시 1(기본 형식, 개념 정리 학습지): 한국사2 '5·16 군사 정변으로 민주주의가 후퇴하다'. 1쪽 = 머리 + Ⅰ 주요 개념 및 내용 정리(번호 주제·이름표 줄·옆 칸·한 줄 정리), 2쪽 = Ⅱ 형성평가 + 도달 점검.

- 예시 2(활동지): 과학 1학년 '입자는 스스로 움직일까?'. 활동 머리, 표, 자료·도움말 상자, 쓰기 칸, O·X, 도전 과제, 마무리.

## 예시 1 — project/canvas.json

```json
{"v": 3, "createdOnFiles": {"v": 1, "at": "2026-11-16T16:00:00Z"}, "title": "학습지 – 한국사2 주제 19 5·16 군사 정변으로 민주주의가 후퇴하다", "launch": {"view": "canvas", "page": "student"}, "pages": [{"id": "student", "name": "학생용"}, {"id": "teacher", "name": "교사용"}], "boards": {"Main.dc.html": {"x": 0, "y": 0, "w": 794, "h": 1123, "title": "학생용 1쪽", "page": "student"}, "TeacherP1.dc.html": {"x": 0, "y": 0, "w": 794, "h": 1123, "title": "교사용 1쪽", "page": "teacher"}, "Page2.dc.html": {"x": 874, "y": 0, "w": 794, "h": 1123, "title": "학생용 2쪽", "page": "student"}, "TeacherP2.dc.html": {"x": 874, "y": 0, "w": 794, "h": 1123, "title": "교사용 2쪽", "page": "teacher"}}, "order": ["Main.dc.html", "TeacherP1.dc.html", "Page2.dc.html", "TeacherP2.dc.html"], "notes": {}, "designSystems": []}
```

## 예시 1 — project/Main.dc.html (학생용 1쪽: 머리, Ⅰ 개념 정리)

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>한국사2 주제 19 학습지 학생용 1쪽</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hahmlet:wght@600;700&amp;family=Noto+Sans+KR:wght@400;500;700&amp;display=swap">
<style>
body{margin:0;word-break:keep-all;text-wrap:pretty}
</style>
</helmet>
<div style="width: 794px; height: 1123px; box-sizing: border-box; padding: 40px 48px 34px; display: flex; flex-direction: column; gap: 16px; font-family: 'Noto Sans KR','Malgun Gothic',sans-serif; color: #14213D; background: #FFFFFF; overflow: hidden">
<div style="display: flex; flex-direction: column; gap: 12px; flex: none">
<div style="position: relative; overflow: hidden; margin: -40px -48px 0; padding: 16px 48px 16px; background: linear-gradient(115deg, #1F3F7A 0%, #2E6DB4 100%); display: flex; flex-direction: column; gap: 10px">
<svg aria-hidden="true" width="230" height="118" viewBox="0 0 230 118" style="position: absolute; right: 0; bottom: 0"><circle cx="178" cy="96" r="52" fill="#FFFFFF" fill-opacity="0.08"/><circle cx="84" cy="112" r="34" fill="#FFFFFF" fill-opacity="0.06"/></svg>
<div style="position: relative; display: flex; align-items: center; gap: 10px">
<div style="display: flex; align-items: center; gap: 6px; background: #FFFFFF; border-radius: 999px; padding: 4px 11px 4px 9px; flex: none">
<svg aria-hidden="true" width="15" height="15" viewBox="0 0 48 48" fill="none" stroke="#1F3F7A" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 18L24 8l18 10M10 18v18M18 18v18M30 18v18M38 18v18M6 40h36"/></svg><p style="margin: 0; font-size: 12px; font-weight: 700; color: #1F3F7A; white-space: nowrap">고1 한국사2 · 대한민국의 발전 · 주제 19</p></div>
<div style="flex: 1"></div>
<div style="display: flex; gap: 9px">
<div style="display: flex; align-items: center; gap: 4px"><p style="margin: 0; font-size: 12px; color: #DCE7F6">학년</p>
<div style="width: 28px; height: 22px; background: #FFFFFF; border-radius: 6px"></div></div>
<div style="display: flex; align-items: center; gap: 4px"><p style="margin: 0; font-size: 12px; color: #DCE7F6">반</p>
<div style="width: 28px; height: 22px; background: #FFFFFF; border-radius: 6px"></div></div>
<div style="display: flex; align-items: center; gap: 4px"><p style="margin: 0; font-size: 12px; color: #DCE7F6">번</p>
<div style="width: 28px; height: 22px; background: #FFFFFF; border-radius: 6px"></div></div>
<div style="display: flex; align-items: center; gap: 4px"><p style="margin: 0; font-size: 12px; color: #DCE7F6">이름</p>
<div style="width: 92px; height: 22px; background: #FFFFFF; border-radius: 6px"></div></div></div></div>
<div style="position: relative; display: flex; align-items: flex-end; justify-content: space-between; gap: 12px">
<h1 style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 28px; font-weight: 700; letter-spacing: -0.6px; line-height: 1.2; color: #FFFFFF">5·16 군사 정변으로 민주주의가 후퇴하다</h1><p style="margin: 0 0 4px; font-size: 12px; color: #DCE7F6; white-space: nowrap">교과서 92~95쪽</p></div></div>
<div style="background: #EAF0F7; border: 1.5px solid #B9CDE6; border-radius: 10px; padding: 8px 16px; display: grid; grid-template-columns: 78px 1fr; column-gap: 12px; row-gap: 4px; align-items: start">
<div style="margin: 1px 0 0; align-self: start; display: flex"><p style="margin: 0; background: #2E6DB4; color: #FFFFFF; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 10px; border-radius: 999px; white-space: nowrap; flex: none">학습 목표</p></div>
<div><p style="margin: 0; font-size: 14px; line-height: 1.65; color: #14213D; line-height: 1.6">① 5·16 군사 정변 이후의 정치·경제적 변화를 설명할 수 있다.</p><p style="margin: 0; font-size: 14px; line-height: 1.65; color: #14213D; line-height: 1.6">② 한일 협정과 베트남 파병을 둘러싼 쟁점을 파악할 수 있다.</p></div>
<div style="margin: 1px 0 0; align-self: start; display: flex"><p style="margin: 0; background: #1F3F7A; color: #FFFFFF; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 10px; border-radius: 999px; white-space: nowrap; flex: none">핵심 질문</p></div><p style="margin: 0; font-size: 14px; line-height: 1.65; color: #14213D; line-height: 1.6">정부는 왜 시민들의 반대에도 한일 국교 정상화를 서둘렀을까?</p><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}">
<div style="margin: 1px 0 0; align-self: start; display: flex"><p style="margin: 0; background: #1D4ED8; color: #FFFFFF; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 10px; border-radius: 999px; white-space: nowrap; flex: none">교육과정</p></div></sc-if><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}">
<div><p style="margin: 0; font-size: 12px; line-height: 1.65; color: #1D4ED8; line-height: 1.6">[10한사2-02-03] 4·19 혁명에서 6월 민주 항쟁에 이르는 민주화 과정을 탐구한다.</p><p style="margin: 0; font-size: 12px; line-height: 1.65; color: #1D4ED8; line-height: 1.6">[10한사2-02-04] 산업화의 성과를 파악하고, 그것이 사회 및 환경에 미친 영향을 인식한다.</p></div></sc-if></div></div>
<div style="display: flex; align-items: stretch; background: #EAF0F7; border-radius: 10px; overflow: hidden; border-bottom: 2px solid #2E6DB4; margin-top: 2px; flex: none"><p style="margin: 0; width: 40px; background: #2E6DB4; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">Ⅰ</p>
<h2 style="margin: 0; padding: 6px 12px; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 20px; font-weight: 700; color: #1F3F7A; letter-spacing: -0.3px; flex: 1">주요 개념 및 내용 정리</h2>
<div style="display: flex; align-items: center; padding-right: 10px"></div></div>
<div style="display: flex; gap: 14px; align-items: stretch; flex: 1 0 auto; margin-bottom: 6px">
<div style="flex: 1; min-width: 0; display: flex; flex-direction: column; justify-content: space-between; gap: 12px">
<div style="display: flex; flex-direction: column; gap: 4px">
<div style="display: flex; align-items: center; gap: 8px"><p style="margin: 0; width: 24px; height: 24px; border-radius: 50%; background: #2E6DB4; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 14px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">1</p><h3 style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; white-space: nowrap">5·16 군사 정변과 군정</h3><p style="margin: 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; border-radius: 999px; padding: 2px 9px; white-space: nowrap">1961~1963</p>
<div style="flex: 1; height: 2px; border-radius: 2px; background: #E3EDF9"></div></div>
<div style="display: grid; grid-template-columns: 36px 1fr; column-gap: 10px; row-gap: 4px; margin-left: 11px; padding-left: 10px; border-left: 2px solid #E3EDF9"><p style="margin: 2px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; border-radius: 6px; text-align: center; line-height: 18px; height: 18px">정변</p>
<div><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">박정희 등 군인이 정권 장악 → 장면 내각·의회 해산</p></div><p style="margin: 2px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; border-radius: 6px; text-align: center; line-height: 18px; height: 18px">군정</p>
<div><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap"><span style="display: inline-block; width: 138px; background: #FFEFC2; border-bottom: 1.5px solid #14213D; border-radius: 3px 3px 0 0; text-align: center; line-height: 1.25; margin: 0 3px; white-space: nowrap"><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}"><b style="color: #1D4ED8">국가 재건 최고 회의</b></sc-if>&#8203;</span> 구성 → 입법·행정·사법권 장악</p><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">중앙정보부 설치 → 비판 세력 감시</p></div><p style="margin: 2px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; border-radius: 6px; text-align: center; line-height: 18px; height: 18px">집권</p>
<div><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">대통령 중심제 개헌 → 박정희 대통령 당선(1963)</p></div></div></div>
<div style="display: flex; flex-direction: column; gap: 4px">
<div style="display: flex; align-items: center; gap: 8px"><p style="margin: 0; width: 24px; height: 24px; border-radius: 50%; background: #2E6DB4; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 14px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">2</p><h3 style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; white-space: nowrap">한일 협정</h3><p style="margin: 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; border-radius: 999px; padding: 2px 9px; white-space: nowrap">1965</p>
<div style="flex: 1; height: 2px; border-radius: 2px; background: #E3EDF9"></div></div>
<div style="display: grid; grid-template-columns: 36px 1fr; column-gap: 10px; row-gap: 4px; margin-left: 11px; padding-left: 10px; border-left: 2px solid #E3EDF9"><p style="margin: 2px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; border-radius: 6px; text-align: center; line-height: 18px; height: 18px">배경</p>
<div><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">경제 개발 자금 마련 + 미국의 한·미·일 협력 요구</p></div><p style="margin: 2px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; border-radius: 6px; text-align: center; line-height: 18px; height: 18px">과정</p>
<div><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">김종필·오히라 메모(1962) → <span style="display: inline-block; width: 138px; background: #FFEFC2; border-bottom: 1.5px solid #14213D; border-radius: 3px 3px 0 0; text-align: center; line-height: 1.25; margin: 0 3px; white-space: nowrap"><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}"><b style="color: #1D4ED8">6·3 시위</b></sc-if>&#8203;</span>(1964)</p><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">비상계엄으로 시위 진압 → 한일 협정 체결(1965)</p></div><p style="margin: 2px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; border-radius: 6px; text-align: center; line-height: 18px; height: 18px">문제</p>
<div><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">식민 지배에 대한 <span style="display: inline-block; width: 138px; background: #FFEFC2; border-bottom: 1.5px solid #14213D; border-radius: 3px 3px 0 0; text-align: center; line-height: 1.25; margin: 0 3px; white-space: nowrap"><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}"><b style="color: #1D4ED8">사과와 배상</b></sc-if>&#8203;</span>이 빠짐</p><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">→ 징용·징병 피해 문제가 오늘날까지 남음</p></div></div></div>
<div style="display: flex; flex-direction: column; gap: 4px">
<div style="display: flex; align-items: center; gap: 8px"><p style="margin: 0; width: 24px; height: 24px; border-radius: 50%; background: #2E6DB4; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 14px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">3</p><h3 style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; white-space: nowrap">베트남 파병</h3><p style="margin: 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; border-radius: 999px; padding: 2px 9px; white-space: nowrap">1964~1973</p>
<div style="flex: 1; height: 2px; border-radius: 2px; background: #E3EDF9"></div></div>
<div style="display: grid; grid-template-columns: 36px 1fr; column-gap: 10px; row-gap: 4px; margin-left: 11px; padding-left: 10px; border-left: 2px solid #E3EDF9"><p style="margin: 2px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; border-radius: 6px; text-align: center; line-height: 18px; height: 18px">과정</p>
<div><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">미국의 요청 → 1964~1973년 32만여 명 파병</p></div><p style="margin: 2px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; border-radius: 6px; text-align: center; line-height: 18px; height: 18px">영향</p>
<div><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">미국의 군사 원조·차관 → 국군 현대화</p><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">군인 송금·군수 물자 수출·건설 참여 → 외화 획득</p></div><p style="margin: 2px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; border-radius: 6px; text-align: center; line-height: 18px; height: 18px">과제</p>
<div><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">사상자, <span style="display: inline-block; width: 138px; background: #FFEFC2; border-bottom: 1.5px solid #14213D; border-radius: 3px 3px 0 0; text-align: center; line-height: 1.25; margin: 0 3px; white-space: nowrap"><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}"><b style="color: #1D4ED8">고엽제</b></sc-if>&#8203;</span> 피해, 민간인 피해, 라이따이한</p></div></div></div>
<div style="display: flex; flex-direction: column; gap: 4px">
<div style="display: flex; align-items: center; gap: 8px"><p style="margin: 0; width: 24px; height: 24px; border-radius: 50%; background: #2E6DB4; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 14px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">4</p><h3 style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; white-space: nowrap">제1·2차 경제 개발 5개년 계획</h3><p style="margin: 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; border-radius: 999px; padding: 2px 9px; white-space: nowrap">1962~1971</p>
<div style="flex: 1; height: 2px; border-radius: 2px; background: #E3EDF9"></div></div>
<div style="display: grid; grid-template-columns: 36px 1fr; column-gap: 10px; row-gap: 4px; margin-left: 11px; padding-left: 10px; border-left: 2px solid #E3EDF9"><p style="margin: 2px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; border-radius: 6px; text-align: center; line-height: 18px; height: 18px">내용</p>
<div><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">섬유·신발 등 경공업, 비료·시멘트·정유 등 기간산업</p><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">경부 고속 도로(1970) 등 사회 간접 자본 확충</p></div><p style="margin: 2px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; border-radius: 6px; text-align: center; line-height: 18px; height: 18px">특징</p>
<div><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">저임금을 바탕으로 한 <span style="display: inline-block; width: 138px; background: #FFEFC2; border-bottom: 1.5px solid #14213D; border-radius: 3px 3px 0 0; text-align: center; line-height: 1.25; margin: 0 3px; white-space: nowrap"><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}"><b style="color: #1D4ED8">노동 집약적</b></sc-if>&#8203;</span> 수출 산업</p><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">수출 1억 달러 달성(1964) → 수출의 날 제정</p></div><p style="margin: 2px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; border-radius: 6px; text-align: center; line-height: 18px; height: 18px">결과</p>
<div><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">높은 경제 성장, 1인당 국민 소득 증가</p><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">↔ 무역 수지 악화, 외채 증가 → 대외 의존 심화</p></div></div></div>
<div style="display: flex; flex-direction: column; gap: 4px">
<div style="display: flex; align-items: center; gap: 8px"><p style="margin: 0; width: 24px; height: 24px; border-radius: 50%; background: #2E6DB4; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 14px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">5</p><h3 style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; white-space: nowrap">3선 개헌</h3><p style="margin: 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; border-radius: 999px; padding: 2px 9px; white-space: nowrap">1969</p>
<div style="flex: 1; height: 2px; border-radius: 2px; background: #E3EDF9"></div></div>
<div style="display: grid; grid-template-columns: 36px 1fr; column-gap: 10px; row-gap: 4px; margin-left: 11px; padding-left: 10px; border-left: 2px solid #E3EDF9"><p style="margin: 2px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; border-radius: 6px; text-align: center; line-height: 18px; height: 18px">배경</p>
<div><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">박정희 재선(1967), 북한 도발(1968) → 예비군·교련</p></div><p style="margin: 2px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; border-radius: 6px; text-align: center; line-height: 18px; height: 18px">전개</p>
<div><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">대통령 3회 연임 허용 개헌 추진 → 반대 투쟁</p><p style="margin: 0; font-size: 14px; line-height: 1.45; white-space: nowrap">여당 의원만 따로 모여 <span style="display: inline-block; width: 138px; background: #FFEFC2; border-bottom: 1.5px solid #14213D; border-radius: 3px 3px 0 0; text-align: center; line-height: 1.25; margin: 0 3px; white-space: nowrap"><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}"><b style="color: #1D4ED8">편법</b></sc-if>&#8203;</span>으로 통과</p></div></div></div></div>
<div style="width: 196px; flex: none; display: flex; flex-direction: column; gap: 12px">
<div style="flex: 1 0 auto; display: flex; flex-direction: column; border: 1.5px solid #B9CDE6; border-radius: 10px; overflow: hidden; background: #F6F9FD">
<div style="background: #1F3F7A; color: #FFFFFF; padding: 6px 12px; display: flex; align-items: center; gap: 8px"><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 14px; font-weight: 700; flex: 1; white-space: nowrap">용어 풀이</p></div>
<div style="flex: 1; display: flex; flex-direction: column; justify-content: space-evenly; padding: 4px 12px 8px">
<div style="display: flex; flex-direction: column; gap: 1px; padding: 5px 0;"><p style="margin: 0; font-size: 14px; font-weight: 700; color: #1F3F7A; white-space: nowrap">군정</p><p style="margin: 0; font-size: 12px; line-height: 1.45; white-space: nowrap">군대가 직접 다스리는 정치</p></div>
<div style="display: flex; flex-direction: column; gap: 1px; padding: 5px 0; border-top: 1px dashed #B9CDE6"><p style="margin: 0; font-size: 14px; font-weight: 700; color: #1F3F7A; white-space: nowrap">중앙정보부</p><p style="margin: 0; font-size: 12px; line-height: 1.45; white-space: nowrap">비판 세력을 감시·탄압한</p><p style="margin: 0; font-size: 12px; line-height: 1.45; white-space: nowrap">정보기관(1961)</p></div>
<div style="display: flex; flex-direction: column; gap: 1px; padding: 5px 0; border-top: 1px dashed #B9CDE6"><p style="margin: 0; font-size: 14px; font-weight: 700; color: #1F3F7A; white-space: nowrap">김종필·오히라 메모</p><p style="margin: 0; font-size: 12px; line-height: 1.45; white-space: nowrap">일본이 줄 돈의 액수·방식만</p><p style="margin: 0; font-size: 12px; line-height: 1.45; white-space: nowrap">정한 합의(1962)</p></div>
<div style="display: flex; flex-direction: column; gap: 1px; padding: 5px 0; border-top: 1px dashed #B9CDE6"><p style="margin: 0; font-size: 14px; font-weight: 700; color: #1F3F7A; white-space: nowrap">차관</p><p style="margin: 0; font-size: 12px; line-height: 1.45; white-space: nowrap">외국에서 빌려 온 돈</p></div>
<div style="display: flex; flex-direction: column; gap: 1px; padding: 5px 0; border-top: 1px dashed #B9CDE6"><p style="margin: 0; font-size: 14px; font-weight: 700; color: #1F3F7A; white-space: nowrap">라이따이한</p><p style="margin: 0; font-size: 12px; line-height: 1.45; white-space: nowrap">베트남 전쟁 때 태어난</p><p style="margin: 0; font-size: 12px; line-height: 1.45; white-space: nowrap">한국계 베트남인 2세</p></div>
<div style="display: flex; flex-direction: column; gap: 1px; padding: 5px 0; border-top: 1px dashed #B9CDE6"><p style="margin: 0; font-size: 14px; font-weight: 700; color: #1F3F7A; white-space: nowrap">사회 간접 자본</p><p style="margin: 0; font-size: 12px; line-height: 1.45; white-space: nowrap">도로·항만·전기 등</p><p style="margin: 0; font-size: 12px; line-height: 1.45; white-space: nowrap">생산을 돕는 기반 시설</p></div>
<div style="display: flex; flex-direction: column; gap: 1px; padding: 5px 0; border-top: 1px dashed #B9CDE6"><p style="margin: 0; font-size: 14px; font-weight: 700; color: #1F3F7A; white-space: nowrap">교련</p><p style="margin: 0; font-size: 12px; line-height: 1.45; white-space: nowrap">학교에서 가르친 군사 훈련 과목</p></div></div></div>
<div style="border: 1.5px solid #B9CDE6; border-radius: 10px; overflow: hidden; background: #F6F9FD">
<div style="background: #2E6DB4; color: #FFFFFF; padding: 6px 12px; display: flex; align-items: center; gap: 8px"><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 14px; font-weight: 700; flex: 1; white-space: nowrap">한눈에 보는 연표</p></div>
<div style="padding: 4px 12px 8px">
<div style="position: relative; padding-top: 3px">
<div style="position: absolute; left: 4px; top: 10px; bottom: 10px; width: 1.5px; background: #B9CDE6"></div>
<div style="display: flex; align-items: center; gap: 7px; padding: 2.5px 0; position: relative"><span style="width: 9px; height: 9px; border-radius: 50%; background: #2E6DB4; border: 2px solid #FFFFFF; box-sizing: border-box; flex: none; position: relative; z-index: 1"></span><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 12px; font-weight: 700; color: #1F3F7A; width: 31px; flex: none">1961</p><p style="margin: 0; font-size: 12px; white-space: nowrap">5·16 군사 정변</p></div>
<div style="display: flex; align-items: center; gap: 7px; padding: 2.5px 0; position: relative"><span style="width: 9px; height: 9px; border-radius: 50%; background: #2E6DB4; border: 2px solid #FFFFFF; box-sizing: border-box; flex: none; position: relative; z-index: 1"></span><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 12px; font-weight: 700; color: #1F3F7A; width: 31px; flex: none">1962</p><p style="margin: 0; font-size: 12px; white-space: nowrap">제1차 경제 개발 계획</p></div>
<div style="display: flex; align-items: center; gap: 7px; padding: 2.5px 0; position: relative"><span style="width: 9px; height: 9px; border-radius: 50%; background: #2E6DB4; border: 2px solid #FFFFFF; box-sizing: border-box; flex: none; position: relative; z-index: 1"></span><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 12px; font-weight: 700; color: #1F3F7A; width: 31px; flex: none">1963</p><p style="margin: 0; font-size: 12px; white-space: nowrap">박정희 대통령 당선</p></div>
<div style="display: flex; align-items: center; gap: 7px; padding: 2.5px 0; position: relative"><span style="width: 9px; height: 9px; border-radius: 50%; background: #2E6DB4; border: 2px solid #FFFFFF; box-sizing: border-box; flex: none; position: relative; z-index: 1"></span><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 12px; font-weight: 700; color: #1F3F7A; width: 31px; flex: none">1964</p><p style="margin: 0; font-size: 12px; white-space: nowrap">6·3 시위, 베트남 파병</p></div>
<div style="display: flex; align-items: center; gap: 7px; padding: 2.5px 0; position: relative"><span style="width: 9px; height: 9px; border-radius: 50%; background: #2E6DB4; border: 2px solid #FFFFFF; box-sizing: border-box; flex: none; position: relative; z-index: 1"></span><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 12px; font-weight: 700; color: #1F3F7A; width: 31px; flex: none">1965</p><p style="margin: 0; font-size: 12px; white-space: nowrap">한일 협정 체결</p></div>
<div style="display: flex; align-items: center; gap: 7px; padding: 2.5px 0; position: relative"><span style="width: 9px; height: 9px; border-radius: 50%; background: #2E6DB4; border: 2px solid #FFFFFF; box-sizing: border-box; flex: none; position: relative; z-index: 1"></span><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 12px; font-weight: 700; color: #1F3F7A; width: 31px; flex: none">1969</p><p style="margin: 0; font-size: 12px; white-space: nowrap">3선 개헌</p></div>
<div style="display: flex; align-items: center; gap: 7px; padding: 2.5px 0; position: relative"><span style="width: 9px; height: 9px; border-radius: 50%; background: #2E6DB4; border: 2px solid #FFFFFF; box-sizing: border-box; flex: none; position: relative; z-index: 1"></span><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 12px; font-weight: 700; color: #1F3F7A; width: 31px; flex: none">1970</p><p style="margin: 0; font-size: 12px; white-space: nowrap">경부 고속 도로 개통</p></div></div></div></div></div></div>
<div style="margin-top: auto; display: flex; align-items: center; gap: 10px; padding-top: 6px; border-top: 1.5px solid #B9CDE6">
<div style="width: 22px; height: 4px; border-radius: 2px; background: #2E6DB4"></div><p style="margin: 0; font-size: 12px; color: #556070; flex: 1">한국사2 · 주제 19 5·16 군사 정변으로 민주주의가 후퇴하다</p><p style="margin: 0; font-size: 12px; font-weight: 700; color: #FFFFFF; background: #1F3F7A; border-radius: 999px; padding: 2px 9px">1 / 2</p></div>
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{"teacher":{"editor":"boolean","default":false,"section":"교사용"},"$preview":{"width":794,"height":1123}}'>
class Component extends DCLogic {
renderVals() {
var t = this.props.teacher ?? false;
return { teacher: t, student: !t };
}
}
</script>
</body>
</html>
```

## 예시 1 — project/Page2.dc.html (학생용 2쪽: Ⅱ 형성평가, 도달 점검)

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>한국사2 주제 19 학습지 학생용 2쪽</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hahmlet:wght@600;700&amp;family=Noto+Sans+KR:wght@400;500;700&amp;display=swap">
<style>
body{margin:0;word-break:keep-all;text-wrap:pretty}
</style>
</helmet>
<div style="width: 794px; height: 1123px; box-sizing: border-box; padding: 40px 48px 34px; display: flex; flex-direction: column; gap: 16px; font-family: 'Noto Sans KR','Malgun Gothic',sans-serif; color: #14213D; background: #FFFFFF; overflow: hidden">
<div style="flex: 1 1 auto; display: flex; flex-direction: column">
<div style="display: flex; align-items: stretch; background: #EAF0F7; border-radius: 10px; overflow: hidden; border-bottom: 2px solid #2E6DB4; margin-top: 2px; flex: none"><p style="margin: 0; width: 40px; background: #2E6DB4; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">Ⅱ</p>
<h2 style="margin: 0; padding: 6px 12px; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 20px; font-weight: 700; color: #1F3F7A; letter-spacing: -0.3px; flex: 1">형성평가</h2>
<div style="display: flex; align-items: center; padding-right: 10px"><p style="margin: 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #FFFFFF; border: 1.5px solid #2E6DB4; border-radius: 999px; padding: 3px 12px; white-space: nowrap">맞은 문항 <span style="display: inline-block; width: 24px; border-bottom: 1.2px solid #14213D">&#8203;</span> / 7</p></div></div>
<div style="height: 12px; flex: none"></div>
<div style="display: flex; flex-direction: column; gap: 6px">
<div style="display: flex; align-items: flex-start; gap: 10px"><p style="margin: 1px 0 0; width: 24px; height: 24px; border-radius: 50%; background: #1F3F7A; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 14px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">1</p>
<div style="flex: 1"><p style="margin: 0; font-size: 15px; line-height: 1.65; color: #14213D">5·16 군사 정변 직후 군인들이 입법·행정·사법권을 장악하기 위해 만든 기구는?</p></div><p style="margin: 3px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; padding: 3px 10px; border-radius: 999px; flex: none">선택형</p></div>
<div style="margin-left: 34px">
<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px 12px"><p style="margin: 0; font-size: 15px; line-height: 1.6"><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}"><b style="color: #1D4ED8; text-decoration: underline">① 국가 재건 최고 회의</b></sc-if><sc-if value="{{student}}" hint-placeholder-val="{{ true }}">① 국가 재건 최고 회의</sc-if></p><p style="margin: 0; font-size: 15px; line-height: 1.6">② 중앙정보부</p><p style="margin: 0; font-size: 15px; line-height: 1.6">③ 민주 공화당</p><p style="margin: 0; font-size: 15px; line-height: 1.6">④ 향토 예비군</p><p style="margin: 0; font-size: 15px; line-height: 1.6">⑤ 제헌 국회</p></div></div><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}"><p style="margin: 0 0 0 34px; font-size: 12px; line-height: 1.5; color: #1D4ED8">해설: 중앙정보부는 비판 세력 감시 기구, 민주 공화당은 1963년에 만든 정당이다.</p></sc-if></div>
<div style="flex: 1 1 0; min-height: 14px; display: flex; align-items: center">
<div style="width: 100%; border-top: 1px dashed #C9D3DF"></div></div>
<div style="display: flex; flex-direction: column; gap: 6px">
<div style="display: flex; align-items: flex-start; gap: 10px"><p style="margin: 1px 0 0; width: 24px; height: 24px; border-radius: 50%; background: #1F3F7A; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 14px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">2</p>
<div style="flex: 1"><p style="margin: 0; font-size: 15px; line-height: 1.65; color: #14213D">다음 협정이 체결되기 직전에 일어난 사실로 옳은 것은?</p></div><p style="margin: 3px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; padding: 3px 10px; border-radius: 999px; flex: none">선택형</p></div>
<div style="margin-left: 34px">
<div data-multi style="background: #F6F9FD; border: 1.5px solid #B9CDE6; border-radius: 10px; padding: 8px 14px"><p style="margin: 0; font-size: 14px; line-height: 1.65; color: #14213D">제2조 1. 양 체약국은 양 체약국 및 그 국민 간의 청구권에 관한 문제가 …… 완전히 그리고 최종적으로 해결된 것이 된다는 것을 확인한다.</p><p style="margin: 0; font-size: 12px; line-height: 1.65; color: #556070">— 한일 청구권 협정(1965)</p></div></div>
<div style="margin-left: 34px">
<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px 12px"><p style="margin: 0; font-size: 15px; line-height: 1.6">① 4·19 혁명이 일어났다.</p><p style="margin: 0; font-size: 15px; line-height: 1.6"><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}"><b style="color: #1D4ED8; text-decoration: underline">② 6·3 시위가 일어났다.</b></sc-if><sc-if value="{{student}}" hint-placeholder-val="{{ true }}">② 6·3 시위가 일어났다.</sc-if></p><p style="margin: 0; font-size: 15px; line-height: 1.6">③ 3선 개헌이 이루어졌다.</p><p style="margin: 0; font-size: 15px; line-height: 1.6">④ 장면 내각이 출범하였다.</p><p style="margin: 0; font-size: 15px; line-height: 1.6">⑤ 6월 민주 항쟁이 일어났다.</p></div></div><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}"><p style="margin: 0 0 0 34px; font-size: 12px; line-height: 1.5; color: #1D4ED8">해설: 6·3 시위는 1964년이다. ①④는 1960년, ③은 1969년, ⑤는 1987년이다.</p></sc-if></div>
<div style="flex: 1 1 0; min-height: 14px; display: flex; align-items: center">
<div style="width: 100%; border-top: 1px dashed #C9D3DF"></div></div>
<div style="display: flex; flex-direction: column; gap: 6px">
<div style="display: flex; align-items: flex-start; gap: 10px"><p style="margin: 1px 0 0; width: 24px; height: 24px; border-radius: 50%; background: #1F3F7A; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 14px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">3</p>
<div style="flex: 1"><p style="margin: 0; font-size: 15px; line-height: 1.65; color: #14213D">1964년 굴욕적인 대일 외교에 반대하여 학생과 시민이 벌인 시위를 쓰시오.</p></div><p style="margin: 3px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; padding: 3px 10px; border-radius: 999px; flex: none">단답형</p></div>
<div style="margin-left: 34px">
<div style="display: flex; align-items: flex-end; gap: 8px"><p style="margin: 0; background: #EAF0F7; color: #2E6DB4; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 10px; border-radius: 999px; white-space: nowrap; flex: none">답</p>
<div style="width: 220px; border-bottom: 1.5px solid #14213D; height: 24px; text-align: center"><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}"><b style="color: #1D4ED8; font-size: 15px">6·3 시위</b></sc-if></div></div></div></div>
<div style="flex: 1 1 0; min-height: 14px; display: flex; align-items: center">
<div style="width: 100%; border-top: 1px dashed #C9D3DF"></div></div>
<div style="display: flex; flex-direction: column; gap: 6px">
<div style="display: flex; align-items: flex-start; gap: 10px"><p style="margin: 1px 0 0; width: 24px; height: 24px; border-radius: 50%; background: #1F3F7A; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 14px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">4</p>
<div style="flex: 1"><p style="margin: 0; font-size: 15px; line-height: 1.65; color: #14213D">“1965년 체결된 한일 협정에는 식민 지배에 대한 사과와 배상이 명시되었다.”</p></div><p style="margin: 3px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; padding: 3px 10px; border-radius: 999px; flex: none">O·X</p></div>
<div style="margin-left: 34px"><p style="margin: 0; font-size: 15px; line-height: 1.65; color: #14213D">( O　/　<sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}"><b style="color: #1D4ED8">X ← 정답</b></sc-if><sc-if value="{{student}}" hint-placeholder-val="{{ true }}">X</sc-if> )</p></div></div>
<div style="flex: 1 1 0; min-height: 14px; display: flex; align-items: center">
<div style="width: 100%; border-top: 1px dashed #C9D3DF"></div></div>
<div style="display: flex; flex-direction: column; gap: 6px">
<div style="display: flex; align-items: flex-start; gap: 10px"><p style="margin: 1px 0 0; width: 24px; height: 24px; border-radius: 50%; background: #1F3F7A; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 14px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">5</p>
<div style="flex: 1"><p style="margin: 0; font-size: 15px; line-height: 1.65; color: #14213D">베트남 파병에 대한 설명으로 옳지 <b>않은</b> 것은?</p></div><p style="margin: 3px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; padding: 3px 10px; border-radius: 999px; flex: none">선택형</p></div>
<div style="margin-left: 34px">
<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px 12px"><p style="margin: 0; font-size: 15px; line-height: 1.6">① 미국의 요청으로 이루어졌다.</p><p style="margin: 0; font-size: 15px; line-height: 1.6">② 1964년 비전투 요원 파병으로 시작되었다.</p><p style="margin: 0; font-size: 15px; line-height: 1.6">③ 군인 송금으로 외화를 벌었다.</p><p style="margin: 0; font-size: 15px; line-height: 1.6">④ 고엽제 피해자가 생겼다.</p><p style="margin: 0; font-size: 15px; line-height: 1.6"><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}"><b style="color: #1D4ED8; text-decoration: underline">⑤ 6·25 전쟁 중에 이루어졌다.</b></sc-if><sc-if value="{{student}}" hint-placeholder-val="{{ true }}">⑤ 6·25 전쟁 중에 이루어졌다.</sc-if></p></div></div></div>
<div style="flex: 1 1 0; min-height: 14px; display: flex; align-items: center">
<div style="width: 100%; border-top: 1px dashed #C9D3DF"></div></div>
<div style="display: flex; flex-direction: column; gap: 6px">
<div style="display: flex; align-items: flex-start; gap: 10px"><p style="margin: 1px 0 0; width: 24px; height: 24px; border-radius: 50%; background: #1F3F7A; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 14px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">6</p>
<div style="flex: 1"><p style="margin: 0; font-size: 15px; line-height: 1.65; color: #14213D">1969년 대통령의 3회 연임을 허용하도록 헌법을 바꾼 일을 쓰시오.</p></div><p style="margin: 3px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; padding: 3px 10px; border-radius: 999px; flex: none">단답형</p></div>
<div style="margin-left: 34px">
<div style="display: flex; align-items: flex-end; gap: 8px"><p style="margin: 0; background: #EAF0F7; color: #2E6DB4; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 10px; border-radius: 999px; white-space: nowrap; flex: none">답</p>
<div style="width: 220px; border-bottom: 1.5px solid #14213D; height: 24px; text-align: center"><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}"><b style="color: #1D4ED8; font-size: 15px">3선 개헌</b></sc-if></div></div></div></div>
<div style="flex: 1 1 0; min-height: 14px; display: flex; align-items: center">
<div style="width: 100%; border-top: 1px dashed #C9D3DF"></div></div>
<div style="display: flex; flex-direction: column; gap: 6px">
<div style="display: flex; align-items: flex-start; gap: 10px"><p style="margin: 1px 0 0; width: 24px; height: 24px; border-radius: 50%; background: #1F3F7A; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 14px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">7</p>
<div style="flex: 1"><p style="margin: 0; font-size: 15px; line-height: 1.65; color: #14213D">제1·2차 경제 개발 5개년 계획의 성과와 한계를 한 가지씩 쓰시오.</p></div><p style="margin: 3px 0 0; font-size: 12px; font-weight: 700; color: #1F3F7A; background: #E3EDF9; padding: 3px 10px; border-radius: 999px; flex: none">서술형</p></div>
<div style="margin-left: 34px">
<div style="background: #F6F9FD; border: 1.5px solid #B9CDE6; border-radius: 10px; padding: 8px 16px"><p style="margin: 0 0 2px; font-size: 14px; color: #767676">성과는 …, 한계는 …</p>
<div style="position: relative">
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div>
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}">
<div style="position: absolute; left: 6px; right: 6px; top: 0"><p style="margin: 0; font-size: 15px; line-height: 30px; color: #1D4ED8; font-weight: 700">성과: 높은 경제 성장, 1인당 국민 소득 증가 / 한계: 무역 수지 악화, 외채 증가</p><p style="margin: 0; font-size: 12px; line-height: 30px; color: #1D4ED8">채점: 성과와 한계를 하나씩 쓰면 정답, 하나만 쓰면 부분 점수</p></div></sc-if></div></div></div></div>
<div style="flex: 1.5 1 0; min-height: 20px"></div>
<div style="border: 1.5px solid #B9CDE6; border-radius: 10px; overflow: hidden; background: #F6F9FD">
<div style="background: #1F3F7A; color: #FFFFFF; padding: 6px 12px; display: flex; align-items: center; gap: 8px"><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 14px; font-weight: 700; flex: 1; white-space: nowrap">도달 점검</p><p style="margin: 0; font-size: 12px; color: #DCE7F6; white-space: nowrap">학습 목표에 도달했는지 스스로 표시하세요.</p></div>
<div style="padding: 2px 16px 4px">
<div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 5px 0;"><p style="margin: 0; font-size: 15px; line-height: 1.65; color: #14213D">나는 5·16 군사 정변 이후의 정치·경제적 변화를 설명할 수 있다.</p><p style="margin: 0; font-size: 14px; color: #556070; flex: none">예　/　아니요</p></div>
<div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 5px 0; border-top: 1px dashed #B9CDE6"><p style="margin: 0; font-size: 15px; line-height: 1.65; color: #14213D">나는 한일 협정과 베트남 파병을 둘러싼 쟁점을 말할 수 있다.</p><p style="margin: 0; font-size: 14px; color: #556070; flex: none">예　/　아니요</p></div></div></div></div>
<div style="margin-top: auto; display: flex; align-items: center; gap: 10px; padding-top: 6px; border-top: 1.5px solid #B9CDE6">
<div style="width: 22px; height: 4px; border-radius: 2px; background: #2E6DB4"></div><p style="margin: 0; font-size: 12px; color: #556070; flex: 1">한국사2 · 주제 19 5·16 군사 정변으로 민주주의가 후퇴하다</p><p style="margin: 0; font-size: 12px; font-weight: 700; color: #FFFFFF; background: #1F3F7A; border-radius: 999px; padding: 2px 9px">2 / 2</p></div>
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{"teacher":{"editor":"boolean","default":false,"section":"교사용"},"$preview":{"width":794,"height":1123}}'>
class Component extends DCLogic {
renderVals() {
var t = this.props.teacher ?? false;
return { teacher: t, student: !t };
}
}
</script>
</body>
</html>
```

## project/TeacherP1.dc.html — 교사용 쪽 (학생용을 불러와 답을 켬)

교사용 쪽은 모두 이 모양이다. `name`만 학생용 파일 이름(확장자 없이)으로 바꾼다.

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>한국사2 주제 19 학습지 교사용 1쪽</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hahmlet:wght@600;700&amp;family=Noto+Sans+KR:wght@400;500;700&amp;display=swap">
<style>
body{margin:0;word-break:keep-all;text-wrap:pretty}
</style>
</helmet>
<div style="width: 794px; height: 1123px">
<dc-import name="Main" teacher="{{ true }}" hint-size="794px,1123px"></dc-import>
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{"$preview":{"width":794,"height":1123}}'>
class Component extends DCLogic {
renderVals() {
return {};
}
}
</script>
</body>
</html>
```

## 예시 2 — 활동지 project/Main.dc.html (머리, 활동 1·2)

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>과학 학습지 학생용 1쪽</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hahmlet:wght@600;700&amp;family=Noto+Sans+KR:wght@400;500;700&amp;display=swap">
<style>
body{margin:0;word-break:keep-all;text-wrap:pretty}
</style>
</helmet>
<div style="width: 794px; height: 1123px; box-sizing: border-box; padding: 40px 48px 34px; display: flex; flex-direction: column; gap: 16px; font-family: 'Noto Sans KR','Malgun Gothic',sans-serif; color: #14213D; background: #FFFFFF; overflow: hidden">
<div style="display: flex; flex-direction: column; gap: 12px; flex: none">
<div style="position: relative; overflow: hidden; margin: -40px -48px 0; padding: 16px 48px 16px; background: linear-gradient(115deg, #1F3F7A 0%, #2E6DB4 100%); display: flex; flex-direction: column; gap: 10px">
<svg aria-hidden="true" width="230" height="118" viewBox="0 0 230 118" style="position: absolute; right: 0; bottom: 0"><circle cx="178" cy="96" r="52" fill="#FFFFFF" fill-opacity="0.08"/><circle cx="84" cy="112" r="34" fill="#FFFFFF" fill-opacity="0.06"/></svg>
<div style="position: relative; display: flex; align-items: center; gap: 10px">
<div style="display: flex; align-items: center; gap: 6px; background: #FFFFFF; border-radius: 999px; padding: 4px 11px 4px 9px; flex: none">
<svg aria-hidden="true" width="15" height="15" viewBox="0 0 48 48" fill="none" stroke="#1F3F7A" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="31" r="5"/><circle cx="23" cy="21" r="4"/><circle cx="33" cy="32" r="3.5"/><circle cx="38" cy="13" r="3"/></svg><p style="margin: 0; font-size: 12px; font-weight: 700; color: #1F3F7A; white-space: nowrap">중1 과학 · 물질의 상태 변화 · 1차시</p></div>
<div style="flex: 1"></div>
<div style="display: flex; gap: 9px">
<div style="display: flex; align-items: center; gap: 4px"><p style="margin: 0; font-size: 12px; color: #DCE7F6">학년</p>
<div style="width: 28px; height: 22px; background: #FFFFFF; border-radius: 6px"></div></div>
<div style="display: flex; align-items: center; gap: 4px"><p style="margin: 0; font-size: 12px; color: #DCE7F6">반</p>
<div style="width: 28px; height: 22px; background: #FFFFFF; border-radius: 6px"></div></div>
<div style="display: flex; align-items: center; gap: 4px"><p style="margin: 0; font-size: 12px; color: #DCE7F6">번</p>
<div style="width: 28px; height: 22px; background: #FFFFFF; border-radius: 6px"></div></div>
<div style="display: flex; align-items: center; gap: 4px"><p style="margin: 0; font-size: 12px; color: #DCE7F6">이름</p>
<div style="width: 92px; height: 22px; background: #FFFFFF; border-radius: 6px"></div></div></div></div>
<div style="position: relative; display: flex; align-items: flex-end; justify-content: space-between; gap: 12px">
<h1 style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 28px; font-weight: 700; letter-spacing: -0.6px; line-height: 1.2; color: #FFFFFF">입자는 스스로 움직일까?</h1><p style="margin: 0 0 4px; font-size: 12px; color: #DCE7F6; white-space: nowrap">확산과 증발로 알아보는 입자의 운동</p></div></div>
<div style="background: #EAF0F7; border: 1.5px solid #B9CDE6; border-radius: 10px; padding: 8px 16px; display: grid; grid-template-columns: 78px 1fr; column-gap: 12px; row-gap: 4px; align-items: start">
<div style="margin: 1px 0 0; align-self: start; display: flex"><p style="margin: 0; background: #2E6DB4; color: #FFFFFF; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 10px; border-radius: 999px; white-space: nowrap; flex: none">학습 목표</p></div><p style="margin: 0; font-size: 14px; line-height: 1.65; color: #14213D; line-height: 1.6">확산과 증발 현상을 관찰하고, 입자가 스스로 운동함을 추론할 수 있다.</p>
<div style="margin: 1px 0 0; align-self: start; display: flex"><p style="margin: 0; background: #1F3F7A; color: #FFFFFF; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 10px; border-radius: 999px; white-space: nowrap; flex: none">핵심 질문</p></div><p style="margin: 0; font-size: 14px; line-height: 1.65; color: #14213D; line-height: 1.6">향수 냄새는 어떻게 방 안 전체로 퍼질까?</p><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}">
<div style="margin: 1px 0 0; align-self: start; display: flex"><p style="margin: 0; background: #1D4ED8; color: #FFFFFF; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 10px; border-radius: 999px; white-space: nowrap; flex: none">교육과정</p></div></sc-if><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}"><p style="margin: 0; font-size: 12px; line-height: 1.65; color: #1D4ED8; line-height: 1.6">2022 개정 · [9과04-01] 확산 및 증발 현상을 관찰하여 물질을 구성하는 입자가 운동하고 있음을 추론할 수 있다.</p></sc-if></div></div>
<div style="display: flex; flex-direction: column; gap: 8px; flex: none; padding-top: 0">
<div style="display: flex; align-items: center; gap: 10px"><p style="margin: 0; width: 28px; height: 28px; border-radius: 50%; background: #2E6DB4; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">1</p>
<h2 style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; flex: 1">확산을 관찰하고 정리해 봅시다</h2><p style="margin: 0; background: #E3EDF9; color: #1F3F7A; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 10px; border-radius: 999px; white-space: nowrap; flex: none">개별 · 10분</p></div><p style="margin: 0; font-size: 15px; line-height: 1.65; color: #14213D">선생님이 보여 준 향수 냄새와 잉크가 퍼지는 모습을 떠올리며 표를 채우세요.</p>
<div style="display: flex; align-items: center; justify-content: center; gap: 10px">
<div style="display: flex; flex-direction: column; align-items: center; gap: 4px">
<svg role="img" aria-label="처음: 입자가 병 근처에 모여 있다" width="200" height="90" viewBox="0 0 200 90"><rect x="1" y="1" width="198" height="88" rx="12" fill="#FFFFFF" stroke="#B9CDE6" stroke-width="1.5"/><rect x="12" y="44" width="30" height="40" rx="4" fill="none" stroke="#556070" stroke-width="1.5"/><circle cx="30" cy="70" r="4" fill="#2E6DB4"/><circle cx="34" cy="78" r="4" fill="#2E6DB4"/><circle cx="33" cy="77" r="4" fill="#2E6DB4"/><circle cx="19" cy="59" r="4" fill="#2E6DB4"/><circle cx="37" cy="66" r="4" fill="#2E6DB4"/><circle cx="36" cy="45" r="4" fill="#2E6DB4"/><circle cx="27" cy="50" r="4" fill="#2E6DB4"/><circle cx="29" cy="63" r="4" fill="#2E6DB4"/><circle cx="18" cy="49" r="4" fill="#2E6DB4"/><circle cx="24" cy="77" r="4" fill="#2E6DB4"/><circle cx="33" cy="46" r="4" fill="#2E6DB4"/><circle cx="34" cy="46" r="4" fill="#2E6DB4"/><circle cx="30" cy="45" r="4" fill="#2E6DB4"/><circle cx="18" cy="75" r="4" fill="#2E6DB4"/><circle cx="22" cy="49" r="4" fill="#2E6DB4"/><circle cx="38" cy="75" r="4" fill="#2E6DB4"/></svg><p style="margin: 0; font-size: 13px; color: #556070">처음</p></div><p style="margin: 0; font-size: 22px; color: #2E6DB4; font-weight: 700; padding-bottom: 18px">›</p>
<div style="display: flex; flex-direction: column; align-items: center; gap: 4px">
<svg role="img" aria-label="조금 뒤: 입자가 퍼지기 시작한다" width="200" height="90" viewBox="0 0 200 90"><rect x="1" y="1" width="198" height="88" rx="12" fill="#FFFFFF" stroke="#B9CDE6" stroke-width="1.5"/><rect x="12" y="44" width="30" height="40" rx="4" fill="none" stroke="#556070" stroke-width="1.5"/><circle cx="45" cy="77" r="4" fill="#2E6DB4"/><circle cx="71" cy="58" r="4" fill="#2E6DB4"/><circle cx="36" cy="76" r="4" fill="#2E6DB4"/><circle cx="87" cy="78" r="4" fill="#2E6DB4"/><circle cx="109" cy="32" r="4" fill="#2E6DB4"/><circle cx="52" cy="23" r="4" fill="#2E6DB4"/><circle cx="29" cy="16" r="4" fill="#2E6DB4"/><circle cx="46" cy="53" r="4" fill="#2E6DB4"/><circle cx="14" cy="58" r="4" fill="#2E6DB4"/><circle cx="50" cy="33" r="4" fill="#2E6DB4"/><circle cx="101" cy="45" r="4" fill="#2E6DB4"/><circle cx="47" cy="45" r="4" fill="#2E6DB4"/><circle cx="89" cy="16" r="4" fill="#2E6DB4"/><circle cx="117" cy="14" r="4" fill="#2E6DB4"/><circle cx="93" cy="69" r="4" fill="#2E6DB4"/><circle cx="16" cy="66" r="4" fill="#2E6DB4"/></svg><p style="margin: 0; font-size: 13px; color: #556070">조금 뒤</p></div><p style="margin: 0; font-size: 22px; color: #2E6DB4; font-weight: 700; padding-bottom: 18px">›</p>
<div style="display: flex; flex-direction: column; align-items: center; gap: 4px">
<svg role="img" aria-label="나중: 입자가 고르게 퍼졌다" width="200" height="90" viewBox="0 0 200 90"><rect x="1" y="1" width="198" height="88" rx="12" fill="#FFFFFF" stroke="#B9CDE6" stroke-width="1.5"/><rect x="12" y="44" width="30" height="40" rx="4" fill="none" stroke="#556070" stroke-width="1.5"/><circle cx="76" cy="50" r="4" fill="#2E6DB4"/><circle cx="12" cy="13" r="4" fill="#2E6DB4"/><circle cx="43" cy="77" r="4" fill="#2E6DB4"/><circle cx="45" cy="63" r="4" fill="#2E6DB4"/><circle cx="177" cy="76" r="4" fill="#2E6DB4"/><circle cx="72" cy="35" r="4" fill="#2E6DB4"/><circle cx="104" cy="64" r="4" fill="#2E6DB4"/><circle cx="29" cy="62" r="4" fill="#2E6DB4"/><circle cx="154" cy="70" r="4" fill="#2E6DB4"/><circle cx="17" cy="76" r="4" fill="#2E6DB4"/><circle cx="26" cy="34" r="4" fill="#2E6DB4"/><circle cx="120" cy="74" r="4" fill="#2E6DB4"/><circle cx="71" cy="75" r="4" fill="#2E6DB4"/><circle cx="108" cy="32" r="4" fill="#2E6DB4"/><circle cx="67" cy="22" r="4" fill="#2E6DB4"/><circle cx="24" cy="20" r="4" fill="#2E6DB4"/></svg><p style="margin: 0; font-size: 13px; color: #556070">나중</p></div></div>
<table style="width: 100%; border-collapse: collapse; table-layout: fixed">
<tr><th style="width: 22%; border: 1px solid #B9CDE6; background: #EAF0F7; color: #1F3F7A; font-size: 14px; font-weight: 700; padding: 8px 6px; text-align: center">관찰한 것</th><th style="width: 39%; border: 1px solid #B9CDE6; background: #EAF0F7; color: #1F3F7A; font-size: 14px; font-weight: 700; padding: 8px 6px; text-align: center">일어난 일</th><th style="width: 39%; border: 1px solid #B9CDE6; background: #EAF0F7; color: #1F3F7A; font-size: 14px; font-weight: 700; padding: 8px 6px; text-align: center">입자로 설명하면</th></tr>
<tr><td style="border: 1px solid #B9CDE6; font-size: 14px; font-weight: 700; color: #1F3F7A; text-align: center; padding: 4px 6px; vertical-align: middle">향수 냄새</td><td style="border: 1px solid #B9CDE6; font-size: 14px; text-align: center; padding: 4px 6px; vertical-align: middle">
<div style="position: relative">
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div>
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}">
<div style="position: absolute; left: 6px; right: 6px; top: 0"><p style="margin: 0; font-size: 15px; line-height: 30px; color: #1D4ED8; font-weight: 700">앞줄부터 차례로 냄새를 맡았다.</p></div></sc-if></div></td><td style="border: 1px solid #B9CDE6; font-size: 14px; text-align: center; padding: 4px 6px; vertical-align: middle">
<div style="position: relative">
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div>
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}">
<div style="position: absolute; left: 6px; right: 6px; top: 0"><p style="margin: 0; font-size: 15px; line-height: 30px; color: #1D4ED8; font-weight: 700">향수 입자가 스스로 움직여 퍼졌다.</p></div></sc-if></div></td></tr>
<tr><td style="border: 1px solid #B9CDE6; font-size: 14px; font-weight: 700; color: #1F3F7A; text-align: center; padding: 4px 6px; vertical-align: middle">잉크 한 방울</td><td style="border: 1px solid #B9CDE6; font-size: 14px; text-align: center; padding: 4px 6px; vertical-align: middle">
<div style="position: relative">
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div>
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}">
<div style="position: absolute; left: 6px; right: 6px; top: 0"><p style="margin: 0; font-size: 15px; line-height: 30px; color: #1D4ED8; font-weight: 700">저어 주지 않아도 물 전체로 퍼졌다.</p></div></sc-if></div></td><td style="border: 1px solid #B9CDE6; font-size: 14px; text-align: center; padding: 4px 6px; vertical-align: middle">
<div style="position: relative">
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div>
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}">
<div style="position: absolute; left: 6px; right: 6px; top: 0"><p style="margin: 0; font-size: 15px; line-height: 30px; color: #1D4ED8; font-weight: 700">잉크 입자가 스스로 움직여 퍼졌다.</p></div></sc-if></div></td></tr></table><p style="margin: 0; font-size: 15px; line-height: 1.65; color: #14213D">물질을 이루는 입자가 스스로 움직여 퍼져 나가는 현상을 <span style="display: inline-block; width: 96px; background: #FFEFC2; border-bottom: 1.5px solid #14213D; border-radius: 3px 3px 0 0; text-align: center; line-height: 1.25; margin: 0 3px; white-space: nowrap"><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}"><b style="color: #1D4ED8">확산</b></sc-if>&#8203;</span>이라고 한다.</p></div>
<div style="display: flex; flex-direction: column; gap: 8px; flex: none; padding-top: 12px; border-top: 1px dashed #C9D3DF">
<div style="display: flex; align-items: center; gap: 10px"><p style="margin: 0; width: 28px; height: 28px; border-radius: 50%; background: #2E6DB4; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">2</p>
<h2 style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; flex: 1">찬물과 더운물, 어디서 더 빨리 퍼질까?</h2><p style="margin: 0; background: #E3EDF9; color: #1F3F7A; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 10px; border-radius: 999px; white-space: nowrap; flex: none">개별 · 8분</p></div><p style="margin: 0; font-size: 15px; line-height: 1.65; color: #14213D">찬물과 더운물에 잉크를 한 방울씩 떨어뜨리면 <span style="display: inline-block; width: 96px; background: #FFEFC2; border-bottom: 1.5px solid #14213D; border-radius: 3px 3px 0 0; text-align: center; line-height: 1.25; margin: 0 3px; white-space: nowrap"><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}"><b style="color: #1D4ED8">더운물</b></sc-if>&#8203;</span>에서 더 빨리 퍼질 것이다.</p>
<div style="background: #FFF6E3; border: 1.5px solid #E6C383; border-radius: 10px; padding: 8px 14px; display: flex; gap: 10px; align-items: flex-start">
<div style="padding-top: 3px"><p style="margin: 0; background: #A8670F; color: #FFFFFF; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 10px; border-radius: 999px; white-space: nowrap; flex: none">도움말</p></div><p style="margin: 0; font-size: 14px; line-height: 1.65; color: #14213D">온도가 높으면 입자의 움직임은 어떻게 달라질까요? 활동 1의 표에 쓴 ‘입자의 움직임’을 떠올려 보세요.</p></div>
<div style="background: #F6F9FD; border: 1.5px solid #B9CDE6; border-radius: 10px; padding: 8px 16px"><p style="margin: 0 0 2px; font-size: 14px; color: #767676">그렇게 예측한 까닭은 …</p>
<div style="position: relative">
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div>
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}">
<div style="position: absolute; left: 6px; right: 6px; top: 0"><p style="margin: 0; font-size: 15px; line-height: 30px; color: #1D4ED8; font-weight: 700">온도가 높을수록 입자의 운동이 활발해 잉크 입자가 더 빨리 퍼지기 때문이다.</p><p style="margin: 0; font-size: 12px; line-height: 30px; color: #1D4ED8">채점: ‘온도’와 ‘입자의 운동’을 이어 쓰면 인정</p></div></sc-if></div></div></div>
<div style="margin-top: auto; display: flex; align-items: center; gap: 10px; padding-top: 6px; border-top: 1.5px solid #B9CDE6">
<div style="width: 22px; height: 4px; border-radius: 2px; background: #2E6DB4"></div><p style="margin: 0; font-size: 12px; color: #556070; flex: 1">과학 · 입자는 스스로 움직일까?</p><p style="margin: 0; font-size: 12px; font-weight: 700; color: #FFFFFF; background: #1F3F7A; border-radius: 999px; padding: 2px 9px">1 / 2</p></div>
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{"teacher":{"editor":"boolean","default":false,"section":"교사용"},"$preview":{"width":794,"height":1123}}'>
class Component extends DCLogic {
renderVals() {
var t = this.props.teacher ?? false;
return { teacher: t, student: !t };
}
}
</script>
</body>
</html>
```

## 예시 2 — 활동지 project/Page2.dc.html (활동 3·4, 도전 과제, 마무리)

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>과학 학습지 학생용 2쪽</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hahmlet:wght@600;700&amp;family=Noto+Sans+KR:wght@400;500;700&amp;display=swap">
<style>
body{margin:0;word-break:keep-all;text-wrap:pretty}
</style>
</helmet>
<div style="width: 794px; height: 1123px; box-sizing: border-box; padding: 40px 48px 34px; display: flex; flex-direction: column; gap: 16px; font-family: 'Noto Sans KR','Malgun Gothic',sans-serif; color: #14213D; background: #FFFFFF; overflow: hidden">
<div style="display: flex; flex-direction: column; gap: 8px; flex: none; padding-top: 0">
<div style="display: flex; align-items: center; gap: 10px"><p style="margin: 0; width: 28px; height: 28px; border-radius: 50%; background: #2E6DB4; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">3</p>
<h2 style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; flex: 1">젖은 빨래는 어떻게 마를까?</h2><p style="margin: 0; background: #E3EDF9; color: #1F3F7A; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 10px; border-radius: 999px; white-space: nowrap; flex: none">개별 · 10분</p></div>
<div style="display: flex; align-items: center; gap: 14px">
<div style="flex: 1">
<div style="background: #FFF6E3; border: 1.5px solid #E6C383; border-radius: 10px; padding: 8px 14px; display: flex; gap: 10px; align-items: flex-start">
<div style="padding-top: 3px"><p style="margin: 0; background: #A8670F; color: #FFFFFF; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 10px; border-radius: 999px; white-space: nowrap; flex: none">자료</p></div><p style="margin: 0; font-size: 14px; line-height: 1.65; color: #14213D">젖은 걸레로 그은 칠판 줄이 끓이지 않았는데 사라졌다.</p></div></div>
<svg role="img" aria-label="물 표면의 입자가 공기 중으로 날아가는 모습" width="160" height="80" viewBox="0 0 160 80"><rect x="1" y="1" width="158" height="78" rx="12" fill="#FFFFFF" stroke="#B9CDE6" stroke-width="1.5"/><rect x="2" y="44" width="156" height="34" fill="#CFE0F2"/><line x1="2" y1="44" x2="158" y2="44" stroke="#2E6DB4" stroke-width="1.5"/><circle cx="75" cy="59" r="3.5" fill="#2E6DB4"/><circle cx="29" cy="69" r="3.5" fill="#2E6DB4"/><circle cx="11" cy="62" r="3.5" fill="#2E6DB4"/><circle cx="136" cy="54" r="3.5" fill="#2E6DB4"/><circle cx="88" cy="64" r="3.5" fill="#2E6DB4"/><circle cx="16" cy="60" r="3.5" fill="#2E6DB4"/><circle cx="108" cy="61" r="3.5" fill="#2E6DB4"/><circle cx="112" cy="55" r="3.5" fill="#2E6DB4"/><circle cx="43" cy="54" r="3.5" fill="#2E6DB4"/><circle cx="81" cy="70" r="3.5" fill="#2E6DB4"/><circle cx="93" cy="67" r="3.5" fill="#2E6DB4"/><circle cx="64" cy="67" r="3.5" fill="#2E6DB4"/><circle cx="24" cy="18" r="3.5" fill="#2E6DB4" opacity="0.45"/><circle cx="104" cy="29" r="3.5" fill="#2E6DB4" opacity="0.45"/><circle cx="69" cy="12" r="3.5" fill="#2E6DB4" opacity="0.45"/><circle cx="47" cy="15" r="3.5" fill="#2E6DB4" opacity="0.45"/><circle cx="49" cy="31" r="3.5" fill="#2E6DB4" opacity="0.45"/></svg></div><p style="margin: 0; font-size: 15px; line-height: 1.65; color: #14213D">액체 표면의 입자가 기체가 되어 공기 중으로 날아가는 현상을 <span style="display: inline-block; width: 96px; background: #FFEFC2; border-bottom: 1.5px solid #14213D; border-radius: 3px 3px 0 0; text-align: center; line-height: 1.25; margin: 0 3px; white-space: nowrap"><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}"><b style="color: #1D4ED8">증발</b></sc-if>&#8203;</span>이라고 한다.</p><p style="margin: 0; font-size: 15px; line-height: 1.65; color: #14213D">“증발은 물이 끓을 때만 일어난다.”　( O　/　<sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}"><b style="color: #1D4ED8">X ← 정답</b></sc-if><sc-if value="{{student}}" hint-placeholder-val="{{ true }}">X</sc-if> )</p>
<div style="background: #F6F9FD; border: 1.5px solid #B9CDE6; border-radius: 10px; padding: 8px 16px"><p style="margin: 0 0 2px; font-size: 14px; color: #767676">칠판의 줄이 사라진 까닭은 …</p>
<div style="position: relative">
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div>
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}">
<div style="position: absolute; left: 6px; right: 6px; top: 0"><p style="margin: 0; font-size: 15px; line-height: 30px; color: #1D4ED8; font-weight: 700">물 입자가 스스로 움직여 공기 중으로 날아갔기 때문이다.</p><p style="margin: 0; font-size: 12px; line-height: 30px; color: #1D4ED8">채점: 물 입자가 스스로 움직였다는 내용이 있으면 인정</p></div></sc-if></div></div></div>
<div style="display: flex; flex-direction: column; gap: 8px; flex: none; padding-top: 12px; border-top: 1px dashed #C9D3DF">
<div style="display: flex; align-items: center; gap: 10px"><p style="margin: 0; width: 28px; height: 28px; border-radius: 50%; background: #2E6DB4; color: #FFFFFF; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex: none">4</p>
<h2 style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 16px; font-weight: 700; flex: 1">확산과 증발을 비교해 봅시다</h2><p style="margin: 0; background: #E3EDF9; color: #1F3F7A; font-size: 12px; font-weight: 700; line-height: 1; padding: 4px 10px; border-radius: 999px; white-space: nowrap; flex: none">짝 · 10분</p></div>
<table style="width: 100%; border-collapse: collapse; table-layout: fixed">
<tr><th style="width: 18%; border: 1px solid #B9CDE6; background: #EAF0F7; color: #1F3F7A; font-size: 14px; font-weight: 700; padding: 8px 6px; text-align: center">구분</th><th style="width: 41%; border: 1px solid #B9CDE6; background: #EAF0F7; color: #1F3F7A; font-size: 14px; font-weight: 700; padding: 8px 6px; text-align: center">확산</th><th style="width: 41%; border: 1px solid #B9CDE6; background: #EAF0F7; color: #1F3F7A; font-size: 14px; font-weight: 700; padding: 8px 6px; text-align: center">증발</th></tr>
<tr><td style="border: 1px solid #B9CDE6; font-size: 14px; font-weight: 700; color: #1F3F7A; text-align: center; padding: 4px 6px; vertical-align: middle">어떤 현상인가</td><td style="border: 1px solid #B9CDE6; font-size: 14px; text-align: center; padding: 4px 6px; vertical-align: middle">
<div style="position: relative">
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div>
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}">
<div style="position: absolute; left: 6px; right: 6px; top: 0"><p style="margin: 0; font-size: 15px; line-height: 30px; color: #1D4ED8; font-weight: 700">입자가 스스로 움직여 퍼져 나간다.</p></div></sc-if></div></td><td style="border: 1px solid #B9CDE6; font-size: 14px; text-align: center; padding: 4px 6px; vertical-align: middle">
<div style="position: relative">
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div>
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}">
<div style="position: absolute; left: 6px; right: 6px; top: 0"><p style="margin: 0; font-size: 15px; line-height: 30px; color: #1D4ED8; font-weight: 700">표면의 입자가 기체로 날아간다.</p></div></sc-if></div></td></tr>
<tr><td style="border: 1px solid #B9CDE6; font-size: 14px; font-weight: 700; color: #1F3F7A; text-align: center; padding: 4px 6px; vertical-align: middle">생활 속 예</td><td style="border: 1px solid #B9CDE6; font-size: 14px; text-align: center; padding: 4px 6px; vertical-align: middle">
<div style="position: relative">
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}">
<div style="position: absolute; left: 6px; right: 6px; top: 0"><p style="margin: 0; font-size: 15px; line-height: 30px; color: #1D4ED8; font-weight: 700">향수 냄새, 티백 우리기</p></div></sc-if></div></td><td style="border: 1px solid #B9CDE6; font-size: 14px; text-align: center; padding: 4px 6px; vertical-align: middle">
<div style="position: relative">
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}">
<div style="position: absolute; left: 6px; right: 6px; top: 0"><p style="margin: 0; font-size: 15px; line-height: 30px; color: #1D4ED8; font-weight: 700">빨래가 마름, 젖은 머리가 마름</p></div></sc-if></div></td></tr></table>
<div style="background: #F6F9FD; border: 1.5px solid #B9CDE6; border-radius: 10px; padding: 8px 16px"><p style="margin: 0 0 2px; font-size: 14px; color: #767676">확산과 증발에서 모두 알 수 있는 것은 …</p>
<div style="position: relative">
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div>
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}">
<div style="position: absolute; left: 6px; right: 6px; top: 0"><p style="margin: 0; font-size: 15px; line-height: 30px; color: #1D4ED8; font-weight: 700">물질을 이루는 입자가 스스로 운동하고 있다는 것이다.</p><p style="margin: 0; font-size: 12px; line-height: 30px; color: #1D4ED8">채점: ‘입자가 스스로 운동한다’는 내용이면 인정</p></div></sc-if></div></div></div>
<div style="border: 1.5px solid #B9CDE6; border-radius: 10px; overflow: hidden; background: #F6F9FD">
<div style="background: #2E6DB4; color: #FFFFFF; padding: 6px 12px; display: flex; align-items: center; gap: 8px"><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 14px; font-weight: 700; flex: 1; white-space: nowrap">도전 과제</p></div>
<div style="padding: 8px 16px 8px"><p style="margin: 0; font-size: 15px; line-height: 1.65; color: #14213D">겨울과 여름 가운데 언제 젖은 빨래가 더 빨리 마를까요? 까닭을 입자의 운동으로 설명하세요.</p>
<div style="position: relative">
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div>
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div><sc-if value="{{teacher}}" hint-placeholder-val="{{ false }}">
<div style="position: absolute; left: 6px; right: 6px; top: 0"><p style="margin: 0; font-size: 15px; line-height: 30px; color: #1D4ED8; font-weight: 700">여름. 기온이 높아 물 입자의 운동이 활발해서 더 빨리 증발하기 때문이다.</p></div></sc-if></div></div></div>
<div style="border: 1.5px solid #B9CDE6; border-radius: 10px; overflow: hidden; background: #F6F9FD">
<div style="background: #1F3F7A; color: #FFFFFF; padding: 6px 12px; display: flex; align-items: center; gap: 8px"><p style="margin: 0; font-family: 'Hahmlet','Noto Serif KR',Batang,serif; font-size: 14px; font-weight: 700; flex: 1; white-space: nowrap">마무리 · 스스로 평가하고 돌아봅시다</p></div>
<div style="padding: 4px 16px 8px">
<div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 4px 0;"><p style="margin: 0; font-size: 15px; line-height: 1.65; color: #14213D">나는 확산과 증발 현상을 설명할 수 있다.</p>
<div style="display: flex; gap: 4px; flex: none">
<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24"><path d="M12 2l3 6.5 7 .9-5.1 4.9 1.3 7L12 18l-6.2 3.3 1.3-7L2 9.4l7-.9z" fill="none" stroke="#1F3F7A" stroke-width="1.5" stroke-linejoin="round"/></svg>
<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24"><path d="M12 2l3 6.5 7 .9-5.1 4.9 1.3 7L12 18l-6.2 3.3 1.3-7L2 9.4l7-.9z" fill="none" stroke="#1F3F7A" stroke-width="1.5" stroke-linejoin="round"/></svg>
<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24"><path d="M12 2l3 6.5 7 .9-5.1 4.9 1.3 7L12 18l-6.2 3.3 1.3-7L2 9.4l7-.9z" fill="none" stroke="#1F3F7A" stroke-width="1.5" stroke-linejoin="round"/></svg>
<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24"><path d="M12 2l3 6.5 7 .9-5.1 4.9 1.3 7L12 18l-6.2 3.3 1.3-7L2 9.4l7-.9z" fill="none" stroke="#1F3F7A" stroke-width="1.5" stroke-linejoin="round"/></svg>
<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24"><path d="M12 2l3 6.5 7 .9-5.1 4.9 1.3 7L12 18l-6.2 3.3 1.3-7L2 9.4l7-.9z" fill="none" stroke="#1F3F7A" stroke-width="1.5" stroke-linejoin="round"/></svg></div></div>
<div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 4px 0; border-top: 1px dashed #B9CDE6"><p style="margin: 0; font-size: 15px; line-height: 1.65; color: #14213D">나는 확산과 증발로 입자가 스스로 운동함을 말할 수 있다.</p>
<div style="display: flex; gap: 4px; flex: none">
<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24"><path d="M12 2l3 6.5 7 .9-5.1 4.9 1.3 7L12 18l-6.2 3.3 1.3-7L2 9.4l7-.9z" fill="none" stroke="#1F3F7A" stroke-width="1.5" stroke-linejoin="round"/></svg>
<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24"><path d="M12 2l3 6.5 7 .9-5.1 4.9 1.3 7L12 18l-6.2 3.3 1.3-7L2 9.4l7-.9z" fill="none" stroke="#1F3F7A" stroke-width="1.5" stroke-linejoin="round"/></svg>
<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24"><path d="M12 2l3 6.5 7 .9-5.1 4.9 1.3 7L12 18l-6.2 3.3 1.3-7L2 9.4l7-.9z" fill="none" stroke="#1F3F7A" stroke-width="1.5" stroke-linejoin="round"/></svg>
<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24"><path d="M12 2l3 6.5 7 .9-5.1 4.9 1.3 7L12 18l-6.2 3.3 1.3-7L2 9.4l7-.9z" fill="none" stroke="#1F3F7A" stroke-width="1.5" stroke-linejoin="round"/></svg>
<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24"><path d="M12 2l3 6.5 7 .9-5.1 4.9 1.3 7L12 18l-6.2 3.3 1.3-7L2 9.4l7-.9z" fill="none" stroke="#1F3F7A" stroke-width="1.5" stroke-linejoin="round"/></svg></div></div><p style="margin: 6px 0 2px; font-size: 14px; color: #767676">오늘 새롭게 알게 된 점은 …</p>
<div style="position: relative">
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div>
<div style="height: 29px; border-bottom: 1px solid #97AECB"></div></div></div></div>
<div style="margin-top: auto; display: flex; align-items: center; gap: 10px; padding-top: 6px; border-top: 1.5px solid #B9CDE6">
<div style="width: 22px; height: 4px; border-radius: 2px; background: #2E6DB4"></div><p style="margin: 0; font-size: 12px; color: #556070; flex: 1">과학 · 입자는 스스로 움직일까?</p><p style="margin: 0; font-size: 12px; font-weight: 700; color: #FFFFFF; background: #1F3F7A; border-radius: 999px; padding: 2px 9px">2 / 2</p></div>
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{"teacher":{"editor":"boolean","default":false,"section":"교사용"},"$preview":{"width":794,"height":1123}}'>
class Component extends DCLogic {
renderVals() {
var t = this.props.teacher ?? false;
return { teacher: t, student: !t };
}
}
</script>
</body>
</html>
```
