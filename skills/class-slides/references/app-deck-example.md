# 앱 슬라이드 예시 코드 (하우스 스타일)

`app-slides.md`의 장 역할별 마크업을 실제로 쓴 예다(하우스 스타일 판 3). **`deck.css`는 그대로 복사해 쓰고**, 장은 아래 마크업의 클래스와 구조를 따른 뒤 글만 바꾼다. 표지를 뺀 모든 장 끝(시뮬레이션 `x-embed` 앞)에는 진행 막대 `.foot`가 있다. 채움 너비(장 번호 ÷ 전체 장 수)와 "05 / 17"만 장마다 바꾼다. 과학 1학년 '입자는 스스로 움직일까?' 차시에서 뽑았다.

## project/deck.json

`title`, `order`, `sections`를 수업에 맞게 바꾸고 `faces`는 그대로 둔다. `designSystems`는 비어 있다. 디자인 시스템을 설치하면서 그 안내대로 기록을 채운다(`design-system-setup.md` 4절).

```json
{"v": 5, "createdOnFiles": {"v": 1, "at": "2026-11-16T16:00:00Z"}, "lists": "css", "format": {"v": 1, "shared": ["project/deck.css"]}, "title": "과학 1학년 – 입자는 스스로 움직일까?", "cover": "cover", "order": ["cover", "goals", "keywords", "guide1", "diffusion", "diffexamples", "check1", "task1", "task1ans", "guide2", "evaporation", "compare", "check2", "task2", "task2ans", "summary", "next"], "sections": {"s1": {"description": "도입: 학습 목표와 핵심어", "start": "cover"}, "s2": {"description": "주기 1: 냄새는 어떻게 퍼질까? (확산)", "start": "guide1"}, "s3": {"description": "주기 2: 젖은 빨래는 어떻게 마를까? (증발)", "start": "guide2"}, "s4": {"description": "정리: 요약과 차시 예고", "start": "summary"}}, "faces": {"noto-sans-kr": {"family": "Noto Sans KR", "href": "https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap"}, "hahmlet": {"family": "Hahmlet", "href": "https://fonts.googleapis.com/css2?family=Hahmlet:wght@600;700&display=swap"}}, "designSystems": []}
```

## project/deck.css (그대로 복사)

```css
section{background:#F6F3EC;color:#14213D;font-family:'Noto Sans KR','Malgun Gothic',Arial,sans-serif;padding:80px 128px 60px;display:flex;flex-direction:column;gap:40px;text-align:left;box-sizing:border-box;word-break:keep-all}
section.cool{background:#EAF0F7}
section.dark{background:#14213D;color:#F6F3EC}
section.amber{background:#F4B23E;color:#14213D}
.top{display:flex;justify-content:space-between;align-items:center;width:100%}
.eyebrow{font-size:28px;font-weight:700;color:#2E6DB4;background:#FFFFFF;border-radius:999px;padding:10px 28px;margin:0}
section.dark .eyebrow{color:#F4B23E;background:rgba(255,255,255,.08)}
section.amber .eyebrow{color:#14213D;background:rgba(255,255,255,.55)}
.course{font-size:26px;color:#556070;margin:0}
section.dark .course{color:#BFCCDA}
section.amber .course{color:#14213D}
.ttl{font-family:'Hahmlet','Noto Serif KR','Batang',Georgia,serif;font-size:68px;font-weight:700;letter-spacing:-1px;line-height:1.2;margin:0}
.body{flex:1;width:100%;display:flex;flex-direction:column;justify-content:center;gap:40px}
.spacer{flex:1;width:100%}
.foot{margin-top:auto;display:flex;align-items:center;gap:28px;width:100%}
.bar{flex:1;height:4px;background:#D9D3C7;border-radius:2px;display:flex}
section.dark .bar{background:rgba(255,255,255,.18)}
section.amber .bar{background:rgba(20,33,61,.15)}
.fill{display:block;background:#F4B23E;border-radius:2px}
section.amber .fill{background:#14213D}
.pg{font-size:26px;color:#556070;margin:0}
section.dark .pg{color:#BFCCDA}
section.amber .pg{color:#14213D}
section.cover{padding:0;display:grid;grid-template-columns:minmax(0,1.08fr) minmax(0,.92fr);gap:0}
.cv-l{position:relative;background:#14213D;color:#F6F3EC;padding:120px 104px 100px 128px;display:flex;flex-direction:column;justify-content:center;gap:36px;overflow:hidden}
.cv-dots{position:absolute;left:0;top:0}
.cv-chip{position:relative;align-self:flex-start;font-size:30px;font-weight:700;background:#F4B23E;color:#14213D;border-radius:999px;padding:10px 28px;margin:0}
.cv-bar{position:relative;width:96px;height:6px;background:#F4B23E}
.cv-l .display,.cv-l .lead{position:relative}
.cv-r{background:#F6F3EC;display:flex;align-items:center;justify-content:center}
.display{font-family:'Hahmlet','Noto Serif KR','Batang',Georgia,serif;font-size:100px;font-weight:700;letter-spacing:-2px;line-height:1.18;margin:0}
.lead{font-size:40px;line-height:1.45;margin:0;color:#BFCCDA}
.serif{font-family:'Hahmlet','Noto Serif KR','Batang',Georgia,serif;font-weight:700;font-size:56px;line-height:1.4;margin:0}
.muted{font-size:40px;line-height:1.45;margin:0;color:#556070}
.caption{font-size:40px;line-height:1.45;margin:0;color:#556070}
.key{display:flex;align-items:center;gap:28px;width:100%;border-top:2px solid #14213D;padding-top:24px;box-sizing:border-box}
.chip{font-size:30px;font-weight:700;background:#F4B23E;color:#14213D;border-radius:999px;padding:6px 22px;margin:0;flex:none}
.key-t{font-size:40px;font-weight:500;margin:0;line-height:1.4}
.cols{display:flex;width:100%;align-items:stretch}
.c{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;padding:24px 40px;border-left:1px solid #D9D3C7;text-align:center}
.c-first{border-left:none}
.stack{display:flex;flex-direction:column;width:100%}
.rowsep{border-top:1px solid #D9D3C7}
.c-word{font-family:'Hahmlet','Noto Serif KR','Batang',Georgia,serif;font-size:60px;font-weight:700;margin:0}
.c-tag{font-size:28px;font-weight:700;color:#2E6DB4;margin:0}
.c-t{font-size:40px;line-height:1.45;margin:0;color:#556070}
.list{display:flex;flex-direction:column;width:100%}
.li{display:flex;align-items:center;gap:48px;padding:36px 0;border-top:1px solid #D9D3C7}
.li-last{border-bottom:1px solid #D9D3C7}
.li-n{font-family:'Hahmlet','Noto Serif KR','Batang',Georgia,serif;font-size:80px;font-weight:700;color:#2E6DB4;margin:0;line-height:1;width:120px;flex:none}
.li-t{font-size:46px;font-weight:500;margin:0;line-height:1.4}
.li-off .li-n,.li-off .li-t{color:#556070}
.now{font-size:30px;font-weight:700;background:#F4B23E;color:#14213D;border-radius:999px;padding:6px 22px;margin:0}
.split{flex:1;display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);gap:72px;align-items:start;width:100%}
.q{display:flex;flex-direction:column;gap:28px}
.q .ttl{font-size:64px;line-height:1.25}
.ctx{font-size:40px;line-height:1.5;margin:0;color:#556070}
.opts{display:flex;flex-direction:column;gap:18px}
.opt{display:flex;align-items:center;gap:24px;background:#FFFFFF;border-radius:24px;padding:24px 32px}
.num{width:60px;height:60px;border-radius:50%;background:#14213D;color:#F6F3EC;font-family:'Hahmlet','Noto Serif KR','Batang',Georgia,serif;font-size:32px;font-weight:700;display:flex;align-items:center;justify-content:center;margin:0;flex:none}
.opt-t{flex:1;font-size:40px;margin:0;line-height:1.35;text-align:center}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:56px;width:100%}
.pair-col{display:flex;flex-direction:column;gap:18px}
.pair-h{font-size:40px;font-weight:700;color:#2E6DB4;margin:0}
.reveal{display:flex;align-items:center;gap:28px;width:100%;box-sizing:border-box;background:#FFFFFF;border-radius:20px;padding:22px 36px}
.reveal-mark{font-size:30px;font-weight:700;background:#14213D;color:#F4B23E;border-radius:999px;padding:6px 22px;margin:0;flex:none}
.reveal-t{font-size:40px;line-height:1.4;margin:0}
.prac{display:grid;grid-template-columns:auto minmax(0,1fr);gap:80px;align-items:start;width:100%}
.timer-n{font-family:'Hahmlet','Noto Serif KR','Batang',Georgia,serif;font-size:200px;font-weight:700;color:#F4B23E;margin:0;line-height:1;white-space:nowrap}
.timer-n span{font-size:80px}
.timer-t{font-size:40px;margin:12px 0 0;color:#BFCCDA}
.inst{font-size:40px;line-height:1.45;margin:16px 0 0;color:#BFCCDA}
.cards{display:flex;gap:32px;flex:1;width:100%}
.card{flex:1;display:flex;flex-direction:column;align-items:center;gap:20px;text-align:center;background:rgba(255,255,255,.07);border:1.5px solid rgba(255,255,255,.18);border-radius:28px;padding:36px 32px}
.card-n{width:68px;height:68px;border-radius:50%;background:#F4B23E;color:#14213D;font-family:'Hahmlet','Noto Serif KR','Batang',Georgia,serif;font-size:36px;font-weight:700;display:flex;align-items:center;justify-content:center;margin:0;flex:none}
.card-t{font-size:42px;font-weight:500;line-height:1.35;margin:0}
.answer{font-family:'Hahmlet','Noto Serif KR','Batang',Georgia,serif;font-weight:700;font-size:52px;line-height:1.5;margin:0;background:#FFF4DC;padding:40px 56px;border-radius:24px}
.fragment{opacity:0;transform:translateY(16px);transition:opacity .4s ease-out,transform .4s ease-out}
.fragment.visible{opacity:1;transform:translateY(0)}
```

## cover — 표지: 왼쪽 남색 칸(점 무늬·칩·명조 제목·노란 띠·부제) + 오른쪽 종이색 칸의 주제 선 그림(SVG). 점 무늬는 그대로, 그림만 차시 주제로 새로 그린다

```html
<section id="cover" class="cover">
<div class="cv-l">
<svg class="cv-dots" aria-hidden="true" width="1037" height="1080"><circle cx="760" cy="120" r="10" fill="#F4B23E" opacity="0.85"/><circle cx="840" cy="190" r="7" fill="#2E6DB4" opacity="0.8"/><circle cx="900" cy="100" r="12" fill="#2E6DB4" opacity="0.65"/><circle cx="960" cy="220" r="6" fill="#F4B23E" opacity="0.6"/><circle cx="820" cy="300" r="6" fill="#2E6DB4" opacity="0.5"/><circle cx="990" cy="330" r="5" fill="#2E6DB4" opacity="0.4"/><circle cx="700" cy="230" r="5" fill="#2E6DB4" opacity="0.45"/><circle cx="930" cy="420" r="4" fill="#F4B23E" opacity="0.35"/></svg><p class="cv-chip">과학 1학년 · 물질의 상태 변화 · 1차시</p>
<h1 class="display">입자는 스스로<br>움직일까?</h1>
<div class="cv-bar"></div><p class="lead">확산과 증발로 알아보는 입자의 운동</p></div>
<div class="cv-r">
<svg role="img" aria-label="향수병에서 입자가 퍼져 나가는 그림" width="640" height="640" viewBox="0 0 640 640"><rect x="96" y="470" width="110" height="130" rx="18" fill="none" stroke="#14213D" stroke-width="5"/><rect x="128" y="436" width="46" height="34" rx="6" fill="none" stroke="#14213D" stroke-width="5"/><circle cx="298" cy="309" r="9.6" fill="#F4B23E" opacity="0.71"/><circle cx="213" cy="394" r="11.3" fill="#2E6DB4" opacity="0.88"/><circle cx="203" cy="396" r="11.4" fill="#2E6DB4" opacity="0.89"/><circle cx="336" cy="223" r="8.9" fill="#2E6DB4" opacity="0.64"/><circle cx="393" cy="230" r="9.0" fill="#2E6DB4" opacity="0.65"/><circle cx="294" cy="359" r="10.2" fill="#F4B23E" opacity="0.77"/><circle cx="416" cy="270" r="8.1" fill="#2E6DB4" opacity="0.56"/><circle cx="224" cy="407" r="11.5" fill="#2E6DB4" opacity="0.90"/><circle cx="217" cy="358" r="10.7" fill="#2E6DB4" opacity="0.82"/><circle cx="483" cy="155" r="6.9" fill="#2E6DB4" opacity="0.44"/><circle cx="436" cy="201" r="7.8" fill="#F4B23E" opacity="0.53"/><circle cx="170" cy="396" r="11.3" fill="#2E6DB4" opacity="0.88"/><circle cx="456" cy="158" r="7.6" fill="#2E6DB4" opacity="0.51"/><circle cx="423" cy="188" r="8.1" fill="#2E6DB4" opacity="0.56"/><circle cx="517" cy="111" r="7.0" fill="#2E6DB4" opacity="0.45"/><circle cx="425" cy="259" r="8.1" fill="#F4B23E" opacity="0.56"/><circle cx="462" cy="235" r="7.3" fill="#2E6DB4" opacity="0.48"/><circle cx="228" cy="385" r="10.9" fill="#2E6DB4" opacity="0.84"/><circle cx="250" cy="344" r="10.7" fill="#2E6DB4" opacity="0.82"/><circle cx="478" cy="196" r="7.7" fill="#2E6DB4" opacity="0.52"/><circle cx="514" cy="157" r="6.6" fill="#F4B23E" opacity="0.41"/><circle cx="437" cy="204" r="8.0" fill="#2E6DB4" opacity="0.55"/><circle cx="552" cy="132" r="6.8" fill="#2E6DB4" opacity="0.43"/><circle cx="420" cy="214" r="7.7" fill="#2E6DB4" opacity="0.52"/><circle cx="489" cy="234" r="7.8" fill="#2E6DB4" opacity="0.53"/><circle cx="301" cy="323" r="9.8" fill="#F4B23E" opacity="0.73"/><circle cx="177" cy="420" r="11.7" fill="#2E6DB4" opacity="0.92"/><circle cx="198" cy="386" r="10.9" fill="#2E6DB4" opacity="0.84"/><circle cx="220" cy="368" r="10.8" fill="#2E6DB4" opacity="0.83"/><circle cx="494" cy="118" r="6.6" fill="#2E6DB4" opacity="0.41"/><circle cx="445" cy="259" r="8.3" fill="#F4B23E" opacity="0.58"/><circle cx="507" cy="115" r="6.7" fill="#2E6DB4" opacity="0.42"/><circle cx="371" cy="322" r="9.4" fill="#2E6DB4" opacity="0.69"/><circle cx="224" cy="352" r="10.7" fill="#2E6DB4" opacity="0.82"/><circle cx="287" cy="336" r="10.1" fill="#2E6DB4" opacity="0.76"/><circle cx="261" cy="315" r="9.9" fill="#F4B23E" opacity="0.74"/><circle cx="350" cy="319" r="9.3" fill="#2E6DB4" opacity="0.68"/><circle cx="466" cy="195" r="7.5" fill="#2E6DB4" opacity="0.50"/><circle cx="424" cy="237" r="7.6" fill="#2E6DB4" opacity="0.51"/><circle cx="526" cy="197" r="7.1" fill="#2E6DB4" opacity="0.46"/><circle cx="346" cy="241" r="9.2" fill="#F4B23E" opacity="0.67"/><circle cx="410" cy="143" r="7.8" fill="#2E6DB4" opacity="0.53"/><circle cx="250" cy="332" r="10.3" fill="#2E6DB4" opacity="0.78"/><circle cx="159" cy="401" r="11.4" fill="#2E6DB4" opacity="0.89"/><circle cx="215" cy="370" r="11.0" fill="#2E6DB4" opacity="0.85"/><circle cx="537" cy="69" r="6.6" fill="#F4B23E" opacity="0.41"/><circle cx="284" cy="316" r="10.0" fill="#2E6DB4" opacity="0.75"/><circle cx="265" cy="391" r="10.9" fill="#2E6DB4" opacity="0.84"/><circle cx="381" cy="210" r="8.7" fill="#2E6DB4" opacity="0.62"/><circle cx="214" cy="377" r="11.0" fill="#2E6DB4" opacity="0.85"/><circle cx="486" cy="65" r="6.8" fill="#F4B23E" opacity="0.43"/><circle cx="556" cy="43" r="6.2" fill="#2E6DB4" opacity="0.37"/><circle cx="374" cy="228" r="8.3" fill="#2E6DB4" opacity="0.58"/><circle cx="592" cy="131" r="6.1" fill="#2E6DB4" opacity="0.36"/><circle cx="289" cy="300" r="10.0" fill="#2E6DB4" opacity="0.75"/><circle cx="496" cy="196" r="7.1" fill="#F4B23E" opacity="0.46"/><circle cx="307" cy="319" r="9.5" fill="#2E6DB4" opacity="0.70"/><circle cx="593" cy="149" r="6.1" fill="#2E6DB4" opacity="0.36"/><circle cx="528" cy="100" r="6.9" fill="#2E6DB4" opacity="0.44"/><circle cx="391" cy="183" r="8.5" fill="#2E6DB4" opacity="0.60"/><circle cx="166" cy="418" r="11.7" fill="#F4B23E" opacity="0.92"/><circle cx="502" cy="172" r="7.5" fill="#2E6DB4" opacity="0.50"/><circle cx="588" cy="185" r="6.3" fill="#2E6DB4" opacity="0.38"/><circle cx="321" cy="262" r="9.3" fill="#2E6DB4" opacity="0.68"/><circle cx="248" cy="351" r="10.4" fill="#2E6DB4" opacity="0.79"/><circle cx="564" cy="115" r="6.5" fill="#F4B23E" opacity="0.40"/><circle cx="476" cy="138" r="7.7" fill="#2E6DB4" opacity="0.52"/><circle cx="487" cy="225" r="7.7" fill="#2E6DB4" opacity="0.52"/><circle cx="484" cy="116" r="7.2" fill="#2E6DB4" opacity="0.47"/><circle cx="486" cy="195" r="7.0" fill="#2E6DB4" opacity="0.45"/></svg></div>
<aside>말할 내용: “향수를 뿌리면 왜 멀리 있는 사람도 냄새를 맡을까요? 오늘은 그 까닭을 눈에 보이지 않는 입자로 설명해 봅니다.” (1분)
성취기준: [9과04-01] 확산 및 증발 현상을 관찰하여 물질을 구성하는 입자가 운동하고 있음을 추론할 수 있다. (2022 개정 교육과정)</aside>
</section>
```

## goals — 학습 목표: 큰 명조 번호 + 가는 선 목록

```html
<section id="goals">
<div class="top"><p class="eyebrow">학습 목표</p><p class="course">과학 1 · 물질의 상태 변화</p></div>
<h2 class="ttl">오늘 할 수 있게 될 것</h2>
<div class="body">
<div class="list">
<div class="li"><p class="li-n">01</p><p class="li-t">확산과 증발 현상을 관찰하고 설명할 수 있다.</p></div>
<div class="li li-last"><p class="li-n">02</p><p class="li-t">확산과 증발로 입자가 스스로 운동함을 추론할 수 있다.</p></div></div></div>
<div class="foot">
<div class="bar"><span class="fill" style="width:12%"></span></div><p class="pg">02 / 17</p></div>
<aside>말할 내용: 두 목표를 함께 읽는다. “수업이 끝나면 ‘입자가 스스로 움직인다’는 문장을 근거와 함께 말할 수 있어야 합니다.” (2분)</aside>
</section>
```

## keywords — 핵심어: 2×2, 뜻은 클릭하면 하나씩 나타남

```html
<section id="keywords">
<div class="top"><p class="eyebrow">핵심어</p><p class="course">과학 1 · 물질의 상태 변화</p></div>
<h2 class="ttl">이 낱말, 뜻을 말해 볼까요?</h2>
<div class="body">
<div class="stack">
<div class="cols">
<div class="c c-first"><p class="c-word">입자</p><p class="c-t fragment">물질을 이루는 아주 작은 알갱이</p></div>
<div class="c"><p class="c-word">확산</p><p class="c-t fragment">입자가 스스로 움직여 퍼져 나가는 현상</p></div></div>
<div class="cols rowsep">
<div class="c c-first"><p class="c-word">증발</p><p class="c-t fragment">액체 표면에서 입자가 기체로 날아가는 현상</p></div>
<div class="c"><p class="c-word">입자의 운동</p><p class="c-t fragment">입자가 쉬지 않고 스스로 움직이는 것</p></div></div></div></div>
<div class="foot">
<div class="bar"><span class="fill" style="width:18%"></span></div><p class="pg">03 / 17</p></div>
<aside>말할 내용: 낱말만 보이는 상태에서 “이 낱말 뜻을 아는 사람?” 하고 묻는다. 학생이 답한 뒤 클릭하면 뜻이 하나씩 나타난다(클릭 4번). (2분)
흔한 오해: ‘입자’를 먼지나 가루처럼 눈에 보이는 알갱이로 생각한다. 눈에 보이지 않을 만큼 작다는 점을 짚는다.</aside>
</section>
```

## guide1 — 수업 안내: 지금 주기만 진하게 + '지금' 칩, 나머지는 흐리게

```html
<section id="guide1">
<div class="top"><p class="eyebrow">수업 안내</p><p class="course">과학 1 · 물질의 상태 변화</p></div>
<h2 class="ttl">오늘 수업의 흐름</h2>
<div class="body">
<div class="list">
<div class="li"><p class="li-n">01</p><p class="li-t">냄새는 어떻게 퍼질까? · 확산</p><p class="now">지금</p></div>
<div class="li li-last li-off"><p class="li-n">02</p><p class="li-t">젖은 빨래는 어떻게 마를까? · 증발</p></div></div></div>
<div class="foot">
<div class="bar"><span class="fill" style="width:24%"></span></div><p class="pg">04 / 17</p></div>
<aside>말할 내용: 두 질문에 차례로 답하며 입자의 운동을 찾아간다. 지금은 1번, 확산이다. (1분)</aside>
</section>
```

## diffusion — 설명(움직이는 현상): 실시간 시뮬레이션 + 설명 한 줄 + 핵심 줄

```html
<section id="diffusion">
<div class="top"><p class="eyebrow">주기 1 · 확산</p><p class="course">과학 1 · 물질의 상태 변화</p></div>
<h2 class="ttl">냄새는 입자가 스스로 움직여 퍼진다</h2>
<div class="spacer"></div><p class="caption">병 근처에 모여 있던 입자가, 저어 주지 않아도 상자 전체로 퍼집니다.</p>
<div class="key"><p class="chip">핵심</p><p class="key-t">확산 = 입자가 스스로 운동해 퍼지는 현상</p></div>
<div class="foot">
<div class="bar"><span class="fill" style="width:29%"></span></div><p class="pg">05 / 17</p></div>
<x-embed style="position:absolute;left:128px;top:300px;width:1664px;height:420px"><style>html,body{margin:0;height:100%;overflow:hidden;background:transparent}canvas{display:block;width:100%;height:100%}</style><canvas id="c"></canvas><script>
var c=document.getElementById('c'),g=c.getContext('2d'),W=0,H=0,D=window.devicePixelRatio||1;
function fit(){W=innerWidth;H=innerHeight;c.width=W*D;c.height=H*D;g.setTransform(D,0,0,D,0,0)}
fit();addEventListener('resize',fit);
function rr(a,b,w,h,r){g.beginPath();g.moveTo(a+r,b);g.arcTo(a+w,b,a+w,b+h,r);g.arcTo(a+w,b+h,a,b+h,r);g.arcTo(a,b+h,a,b,r);g.arcTo(a,b,a+w,b,r);g.closePath()}
function mk(x,y,s){var a=Math.random()*6.283;return {x:x,y:y,vx:Math.cos(a)*s,vy:Math.sin(a)*s,s:s}}
function move(p,turn,x0,y0,x1,y1){if(Math.random()<turn){var a=Math.random()*6.283;p.vx=Math.cos(a)*p.s;p.vy=Math.sin(a)*p.s}
p.x+=p.vx;p.y+=p.vy;if(p.x<x0){p.x=x0;p.vx=-p.vx}if(p.x>x1){p.x=x1;p.vx=-p.vx}if(p.y<y0){p.y=y0;p.vy=-p.vy}if(p.y>y1){p.y=y1;p.vy=-p.vy}}
function dot(p,r,col){g.fillStyle=col;g.beginPath();g.arc(p.x,p.y,r,0,6.283);g.fill()}
function label(t,x,y,col,al){g.font='700 30px "Malgun Gothic","Apple SD Gothic Neo",sans-serif';g.fillStyle=col;g.textAlign=al||'left';g.fillText(t,x,y)}

var P=[],t0=0,N=150;
function reset(){P=[];var bh=H*0.45;for(var i=0;i<N;i++)P.push(mk(60+Math.random()*80,H-30-Math.random()*bh,3.2));t0=performance.now()}
fit();reset();
function frame(now){var s=(now-t0)/1000;if(s>16)reset();
g.clearRect(0,0,W,H);rr(2,2,W-4,H-4,28);g.fillStyle='#FFFFFF';g.fill();g.lineWidth=2;g.strokeStyle='#CBD3DD';g.stroke();
var bh=H*0.5;g.beginPath();g.moveTo(44,H-bh);g.lineTo(44,H-16);g.lineTo(156,H-16);g.lineTo(156,H-bh);g.lineWidth=5;g.strokeStyle='#556070';g.stroke();
label('향수병',100,H-bh-14,'#556070','center');
for(var i=0;i<P.length;i++){move(P[i],0.035,16,16,W-16,H-16);dot(P[i],7,'#2E6DB4')}
label('지난 시간 '+Math.min(16,Math.floor(s))+'초',W-28,52,'#14213D','right');
requestAnimationFrame(frame)}
requestAnimationFrame(frame);
</script></x-embed>
<aside>말할 내용: 화면은 향수병에서 나온 입자가 움직이는 모습을 흉내 낸 것이다. 오른쪽 위 시간이 지날수록 입자가 상자 전체로 퍼지는 것을 함께 본다. 16초마다 처음부터 다시 시작한다.
발문: “아무도 입자를 밀지 않았는데 왜 퍼졌을까요?” → 입자가 스스로 움직이기 때문.
흔한 오해: 바람이 있어야 냄새가 퍼진다고 생각한다. 시뮬레이션에는 바람이 없다는 점을 짚는다.
실제 활동: 교실 앞에서 향수(없으면 귤껍질)를 뿌리고 냄새를 맡은 학생이 손을 들게 하면 앞줄부터 차례로 손이 올라간다. (4분)</aside>
</section>
```

## diffexamples — 설명(예 비교): 가는 세로선으로 나눈 칸

```html
<section id="diffexamples">
<div class="top"><p class="eyebrow">주기 1 · 확산</p><p class="course">과학 1 · 물질의 상태 변화</p></div>
<h2 class="ttl">확산은 기체와 액체 속에서 일어난다</h2>
<div class="body">
<div class="cols">
<div class="c c-first"><p class="c-tag">공기 속</p><p class="c-word">향수 냄새</p><p class="c-t">향수 입자가 공기 속으로 퍼진다</p></div>
<div class="c"><p class="c-tag">물속</p><p class="c-word">잉크 한 방울</p><p class="c-t">잉크 입자가 물 전체로 퍼진다</p></div>
<div class="c"><p class="c-tag">물속</p><p class="c-word">티백 우리기</p><p class="c-t">찻잎 성분이 물속으로 퍼진다</p></div></div></div>
<div class="key"><p class="chip">핵심</p><p class="key-t">저어 주지 않아도 퍼지는 것은 입자가 스스로 움직이기 때문</p></div>
<div class="foot">
<div class="bar"><span class="fill" style="width:35%"></span></div><p class="pg">06 / 17</p></div>
<aside>말할 내용: 물이 든 비커에 잉크를 한 방울 떨어뜨려 두고, 수업이 끝날 때 다시 보자고 한다. “저어 주지 않았는데도 퍼질까요?”
세 예의 공통점(저어 주거나 밀지 않아도 퍼진다)을 학생이 말하게 한다. (3분)</aside>
</section>
```

## check1 — 확인: 왼쪽 질문, 오른쪽 흰 보기 카드 4개, 클릭하면 정답 띠

```html
<section id="check1" class="cool">
<div class="top"><p class="eyebrow">확인 1 · 하나 고르기</p><p class="course">과학 1 · 물질의 상태 변화</p></div>
<div class="split">
<div class="q">
<h2 class="ttl">다음 중 확산의 예가 아닌 것은?</h2><p class="ctx">입자가 스스로 움직였는지, 무언가가 밀었는지 따져 보세요.</p></div>
<div class="opts">
<div class="opt"><p class="num">1</p><p class="opt-t">빵 굽는 냄새가 집 안에 퍼진다</p></div>
<div class="opt"><p class="num">2</p><p class="opt-t">물에 떨어뜨린 잉크가 퍼진다</p></div>
<div class="opt"><p class="num">3</p><p class="opt-t">선풍기 바람에 종이가 날아간다</p></div>
<div class="opt"><p class="num">4</p><p class="opt-t">티백의 색소가 물에 퍼진다</p></div></div></div>
<div class="reveal fragment"><p class="reveal-mark">정답 ③</p><p class="reveal-t">바람이 종이를 밀어서 움직인 것입니다. 확산은 입자가 스스로 움직여 퍼집니다.</p></div>
<div class="foot">
<div class="bar"><span class="fill" style="width:41%"></span></div><p class="pg">07 / 17</p></div>
<aside>말할 내용: 하나, 둘, 셋에 손가락으로 번호를 동시에 들게 한다. 결과를 본 뒤 클릭하면 정답과 까닭이 나타난다. (3분)
정답: ③
다음 행동: 절반 넘게 틀리면 앞의 시뮬레이션 장으로 돌아가 ‘스스로 움직인다’와 ‘밀려서 움직인다’의 차이를 다시 설명한다.</aside>
</section>
```

## check2 — 확인(참·거짓 + 근거): 두 묶음 + 클릭 정답

```html
<section id="check2" class="cool">
<div class="top"><p class="eyebrow">확인 2 · 참·거짓과 근거</p><p class="course">과학 1 · 물질의 상태 변화</p></div>
<h2 class="ttl">“증발은 물이 끓을 때만 일어난다.”</h2>
<div class="body">
<div class="pair">
<div class="pair-col"><p class="pair-h">1. 참일까, 거짓일까?</p>
<div class="opt"><p class="num">가</p><p class="opt-t">참</p></div>
<div class="opt"><p class="num">나</p><p class="opt-t">거짓</p></div></div>
<div class="pair-col"><p class="pair-h">2. 근거는?</p>
<div class="opt"><p class="num">㉠</p><p class="opt-t">빨래는 끓이지 않아도 마른다</p></div>
<div class="opt"><p class="num">㉡</p><p class="opt-t">물은 100 ℃에서 끓는다</p></div></div></div></div>
<div class="reveal fragment"><p class="reveal-mark">거짓 · ㉠</p><p class="reveal-t">끓지 않아도 액체 표면에서는 늘 증발이 일어납니다. ㉡은 맞는 말이지만 근거가 아닙니다.</p></div>
<div class="foot">
<div class="bar"><span class="fill" style="width:76%"></span></div><p class="pg">13 / 17</p></div>
<aside>말할 내용: 공책에 ‘참/거짓’과 ‘㉠/㉡’을 함께 쓰게 한 뒤 클릭해 정답을 보인다. (3분)
정답: 거짓, 근거 ㉠
다음 행동: ‘참’이 많으면 증발 시뮬레이션 장으로 돌아간다. ㉡을 고른 학생에게는 “맞는 말이지만 이 문장이 틀린 까닭이 될까?”라고 묻는다.</aside>
</section>
```

## task1 — 연습: 남색 바탕, 큰 명조 시간 + 제목·지시 + 단계 카드

```html
<section id="task1" class="dark">
<div class="top"><p class="eyebrow">연습 1 · 혼자 쓰고 짝과 비교</p><p class="course">과학 1 · 물질의 상태 변화</p></div>
<div class="prac">
<div><p class="timer-n">4<span>분</span></p><p class="timer-t">공책에 예측과 까닭 한 문장</p></div>
<div>
<h2 class="ttl">찬물과 더운물, 어디서 더 빨리 퍼질까?</h2><p class="inst">찬물과 더운물에 잉크를 한 방울씩 떨어뜨립니다.</p></div></div>
<div class="cards">
<div class="card"><p class="card-n">1</p><p class="card-t">어느 쪽에서 더 빨리 퍼질지 예측한다.</p></div>
<div class="card"><p class="card-n">2</p><p class="card-t">까닭을 ‘입자의 운동’을 넣어 한 문장으로 쓴다.</p></div></div>
<div class="foot">
<div class="bar"><span class="fill" style="width:47%"></span></div><p class="pg">08 / 17</p></div>
<aside>말할 내용: 혼자 쓰고, 2분 뒤 짝과 비교하게 한다. (4분)
예상 답: 더운물. 까닭에 ‘온도가 높아서’만 쓰고 입자를 빼는 경우가 많다 → “온도가 높으면 입자가 어떻게 될까?”라고 묻는다.</aside>
</section>
```

## task1ans — 연습 답(직접 비교): 시뮬레이션 두 개 + 클릭하면 예시 답

```html
<section id="task1ans">
<div class="top"><p class="eyebrow">연습 1 · 직접 비교해 봅시다</p><p class="course">과학 1 · 물질의 상태 변화</p></div>
<h2 class="ttl">같은 시간, 어느 쪽이 더 퍼졌나요?</h2>
<div class="spacer"></div>
<div class="reveal fragment"><p class="reveal-mark">예시 답</p><p class="reveal-t">더운물에서 더 빨리 퍼진다. 온도가 높을수록 입자의 운동이 활발하기 때문이다.</p></div>
<div class="foot">
<div class="bar"><span class="fill" style="width:53%"></span></div><p class="pg">09 / 17</p></div>
<x-embed style="position:absolute;left:128px;top:300px;width:1664px;height:500px"><style>html,body{margin:0;height:100%;overflow:hidden;background:transparent}canvas{display:block;width:100%;height:100%}</style><canvas id="c"></canvas><script>
var c=document.getElementById('c'),g=c.getContext('2d'),W=0,H=0,D=window.devicePixelRatio||1;
function fit(){W=innerWidth;H=innerHeight;c.width=W*D;c.height=H*D;g.setTransform(D,0,0,D,0,0)}
fit();addEventListener('resize',fit);
function rr(a,b,w,h,r){g.beginPath();g.moveTo(a+r,b);g.arcTo(a+w,b,a+w,b+h,r);g.arcTo(a+w,b+h,a,b+h,r);g.arcTo(a,b+h,a,b,r);g.arcTo(a,b,a+w,b,r);g.closePath()}
function mk(x,y,s){var a=Math.random()*6.283;return {x:x,y:y,vx:Math.cos(a)*s,vy:Math.sin(a)*s,s:s}}
function move(p,turn,x0,y0,x1,y1){if(Math.random()<turn){var a=Math.random()*6.283;p.vx=Math.cos(a)*p.s;p.vy=Math.sin(a)*p.s}
p.x+=p.vx;p.y+=p.vy;if(p.x<x0){p.x=x0;p.vx=-p.vx}if(p.x>x1){p.x=x1;p.vx=-p.vx}if(p.y<y0){p.y=y0;p.vy=-p.vy}if(p.y>y1){p.y=y1;p.vy=-p.vy}}
function dot(p,r,col){g.fillStyle=col;g.beginPath();g.arc(p.x,p.y,r,0,6.283);g.fill()}
function label(t,x,y,col,al){g.font='700 30px "Malgun Gothic","Apple SD Gothic Neo",sans-serif';g.fillStyle=col;g.textAlign=al||'left';g.fillText(t,x,y)}

var A=[],B=[],t0=0,N=110;
function box(i){var w=(W-60)/2;return {x:i?w+60:0,y:60,w:w,h:H-60}}
function reset(){A=[];B=[];var a=box(0),b=box(1);for(var i=0;i<N;i++){A.push(mk(a.x+a.w/2+(Math.random()-.5)*30,130+Math.random()*30,1.1));B.push(mk(b.x+b.w/2+(Math.random()-.5)*30,130+Math.random()*30,4.2))}t0=performance.now()}
fit();reset();
function draw(bx,arr,name,tint){rr(bx.x+2,bx.y+2,bx.w-4,bx.h-4,28);g.fillStyle=tint;g.fill();g.lineWidth=2;g.strokeStyle='#CBD3DD';g.stroke();
for(var i=0;i<arr.length;i++){move(arr[i],0.04,bx.x+16,bx.y+16,bx.x+bx.w-16,bx.y+bx.h-16);dot(arr[i],7,'#2E6DB4')}
label(name,bx.x+bx.w/2,bx.y+bx.h-26,'#14213D','center')}
function frame(now){var s=(now-t0)/1000;if(s>14)reset();g.clearRect(0,0,W,H);
draw(box(0),A,'찬물','#E3EEF8');draw(box(1),B,'더운물','#FBE6D6');
label('지난 시간 '+Math.min(14,Math.floor(s))+'초',W-28,40,'#14213D','right');
requestAnimationFrame(frame)}
requestAnimationFrame(frame);
</script></x-embed>
<aside>말할 내용: 예측을 몇 명 들은 뒤 시뮬레이션을 함께 본다. 왼쪽(찬물)과 오른쪽(더운물)에서 같은 시간 동안 잉크 입자가 얼마나 퍼지는지 견준다. 다 본 뒤 클릭하면 예시 답이 나타난다. (3분)
인정: ‘입자가 더 빨리 움직인다’처럼 입자의 운동을 넣어 썼으면 맞다.
가능하면 실제 찬물·더운물 비커로도 보여 준다. 더운물은 교사가 다룬다.</aside>
</section>
```

## task2ans — 연습 답(글): 옅은 노랑 상자의 명조 예시 답

```html
<section id="task2ans">
<div class="top"><p class="eyebrow">연습 2 · 이렇게 쓸 수 있어요</p><p class="course">과학 1 · 물질의 상태 변화</p></div>
<h2 class="ttl">생활 속 예를 입자로 설명하기</h2>
<div class="body"><p class="answer">젖은 머리가 마르는 것은 물 입자가<br>스스로 움직여 공기 중으로 날아가기 때문이다.</p><p class="muted">다른 예: 복도까지 카레 냄새가 나는 것은 냄새 입자가 스스로 움직여 퍼지기 때문이다.</p></div>
<div class="foot">
<div class="bar"><span class="fill" style="width:88%"></span></div><p class="pg">15 / 17</p></div>
<aside>말할 내용: 학생 문장 두세 개를 발표하게 하고, 확산인지 증발인지 함께 가른다. 답이 하나가 아니므로 입자의 운동으로 설명했으면 인정한다. (2분)</aside>
</section>
```

## summary — 요약: 노란 강조 장 한 장

```html
<section id="summary" class="amber">
<div class="top"><p class="eyebrow">오늘 배운 것</p><p class="course">과학 1 · 물질의 상태 변화</p></div>
<div class="body"><p class="serif">누가 밀지 않아도 냄새는 퍼지고, 빨래는 마른다.</p><p class="display">입자는 스스로 운동한다.</p></div>
<div class="foot">
<div class="bar"><span class="fill" style="width:94%"></span></div><p class="pg">16 / 17</p></div>
<aside>말할 내용: 수업 처음에 떨어뜨린 잉크 비커와 칠판의 젖은 줄을 다시 본다. 학습 목표 두 개와 짝을 맞춰 읽는다. (3분)</aside>
</section>
```

## next — 차시 예고: 남색 바탕

```html
<section id="next" class="dark">
<div class="top"><p class="eyebrow">다음 시간</p><p class="course">과학 1 · 물질의 상태 변화</p></div>
<div class="body">
<h1 class="display">물질의 세 가지 상태와<br>입자 모형</h1><p class="lead">고체·액체·기체에서 입자는 어떻게 다를까?</p></div>
<div class="foot">
<div class="bar"><span class="fill" style="width:100%"></span></div><p class="pg">17 / 17</p></div>
<aside>말할 내용: 오늘 ‘입자가 움직인다’를 알았으니, 다음 시간에는 상태마다 입자가 어떻게 움직이는지 그림으로 나타내 본다. (1분)</aside>
</section>
```
