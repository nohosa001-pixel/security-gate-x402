# 📱 Colosseum 1주차 비디오 업데이트 (Weekly Video Update) 완벽 촬영 가이드

> **Live Video Link**: [https://www.youtube.com/watch?v=KgweWFcfPc8](https://www.youtube.com/watch?v=KgweWFcfPc8) (YouTube Shorts: [https://youtube.com/shorts/KgweWFcfPc8](https://youtube.com/shorts/KgweWFcfPc8))  
> **길이**: 1분 43초 (103s)  
> **목표**: 11월 11일(내일) 오후 창구가 열렸을 때 바로 제출할 1주차 영상 (총 75초)  
> **촬영 도구**: 스마트폰 카메라 (세로 또는 가로, 편하신 대로)  
> **주제**: "이번 1주차에 우리가 무엇을 만들었고(Built), 무엇을 배웠는가(Learned)?"

---

## 🎬 스마트폰 촬영 3단계 동선 (총 75초)

| 시간 | 카메라 앵글 (스마트폰이 비추는 곳) | 화면에 보이는 내용 |
| :---: | :--- | :--- |
| **0:00 ~ 0:20**<br>(20초) | **내 얼굴 (셀카) 또는 모니터 정면** | 차분하고 자신감 있는 표정으로 1주차 빌드 소개 |
| **0:20 ~ 0:50**<br>(30초) | **컴퓨터 모니터 화면 비추기** | 터미널에서 데모 실행 (`python scripts/demo_colosseum_live.py --auto`)<br>• 빨간색 `[BLOCKED]` 차단 화면 비추기<br>• 솔라나 `[REVERTED]` 온체인 한도 화면 비추기 |
| **0:50 ~ 1:15**<br>(25초) | **모니터(410 tests) 또는 다시 내 얼굴** | 이번 주에 배운 교훈(Learned)과 마무리 인사 |

---

## 🎙️ 1주차 전용 나레이션 대본 (영문 + 한글 발음 + 의미)

### [1단계: 오프닝 및 이번 주 만든 것 (0:00 ~ 0:20)]
*(스마트폰으로 카메라를 보며)*

**English:**
> "Hi Colosseum, this is Seung Il Choi with our Week 1 update for A.GRID Security Gate."

* **한글 발음**: "하이 콜로세움, 디스 이즈 승일 최 위드 아워 위크 원 업데이트 포 에이그리드 시큐리티 게이트."
* **의미**: "안녕하세요 콜로세움, A.GRID 시큐리티 게이트의 1주차 업데이트를 전해드리는 최승일입니다."

**English:**
> "This week, we focused on our core deterministic security engine on Solana Mainnet."

* **한글 발음**: "디스 위크, 위 포커스트 온 아워 코어 디터미니스틱 시큐리티 엔진 온 솔라나 메인넷."
* **의미**: "이번 주 우리는 솔라나 메인넷 상의 핵심 결정론적 보안 엔진 구축에 집중했습니다."

---

### [2단계: 모니터 비추며 실시간 라이브 시연 (0:20 ~ 0:50)]
*(스마트폰을 컴퓨터 모니터 터미널로 돌려서 비추고, 엔터를 쳐서 데모 실행)*  
*(명령어: `.venv\Scripts\python scripts/demo_colosseum_live.py --auto`)*

**English:**
> "Here is our live engine in action. When an agent receives a malicious prompt injection attempting to steal private keys, our local AST parser intercepts and blocks it in under 2.8 milliseconds—with zero external network calls."

* **한글 발음**: "히어 이즈 아워 라이브 엔진 인 액션. 웬 언 에이전트 리시브스 어 말리셔스 프롬프트 인젝션 어템프팅 투 스틸 프라이빗 키즈, 아워 로컬 에이에스티 파서 인터셉츠 앤드 블록스 잇 인 언더 투 포인트 에잇 밀리세컨즈—위드 제로 익스터널 네트워크 콜스."
* **의미**: "여기 라이브로 작동하는 엔진이 있습니다. 에이전트가 개인키를 훔치려는 악성 프롬프트 인젝션을 받았을 때, 우리의 로컬 AST 파서가 외부 통신 없이 2.8밀리초 이내로 가로채 차단합니다."

*(터미널에 솔라나 Revert 화면이 뜰 때 모니터를 클로즈업하며)*

**English:**
> "And if an agent hallucinates and attempts to transfer 150 SOL over its policy limit, our Solana Anchor Program deterministically reverts the transaction in 0.4 seconds."

* **한글 발음**: "앤드 이프 언 에이전트 할루시네이츠 앤드 어템프츠 투 트랜스퍼 원 헌드레드 피프티 솔 오버 잇츠 폴리시 리밋, 아워 솔라나 앵커 프로그램 디터미니스티컬리 리버츠 더 트랜잭션 인 지로 포인트 포 세컨즈."
* **의미**: "그리고 에이전트가 환각을 일으켜 정책 한도를 초과해 150 SOL을 이체하려 하면, 솔라나 앵커 프로그램이 0.4초 만에 트랜잭션을 강제 취소시킵니다."

---

### [3단계: 이번 주 배운 점 & 마무리 (0:50 ~ 1:15)]
*(모니터의 410 tests passing 화면을 비추거나 다시 얼굴을 비추며)*

**English:**
> "What we learned this week is clear: Secondary LLM guardrails add 400 milliseconds of latency, which breaks real-time agents. Deterministic local AST combined with Solana's 0.4-second finality is the only viable path."

* **한글 발음**: "왓 위 런드 디스 위크 이즈 클리어: 세컨더리 엘엘엠 가드레일스 애드 포 헌드레드 밀리세컨즈 오브 레이턴시, 위치 브레이크스 리얼-타임 에이전츠. 디터미니스틱 로컬 에이에스티 컴바인드 위드 솔라나스 지로 포인트 포-세컨드 파이널리티 이즈 디 온리 바이어블 패스."
* **의미**: "이번 주 우리가 배운 점은 명확합니다: 보조 LLM 가드레일은 400밀리초의 지연시간을 유발해 실시간 에이전트를 망가뜨립니다. 로컬 결정론적 AST와 솔라나의 0.4초 완결성의 결합만이 유일한 해법입니다."

**English:**
> "We have 410 tests passing on Solana Mainnet. See you in Week 2!"

* **한글 발음**: "위 해브 포 헌드레드 텐 테스트스 패싱 온 솔라나 메인넷. 씨 유 인 위크 투!"
* **의미**: "솔라나 메인넷에서 410개 테스트가 통과되었습니다. 2주차에 뵙겠습니다!"

---

## 🚀 스마트폰 제출 4단계 요약

1. 스마트폰 카메라 켜고 **동영상 녹화** (약 75초).
2. 스마트폰 갤러리에서 영상 선택 ➔ **[공유] ➔ [YouTube]** 터치.
3. 제목: `A.GRID - Colosseum Eternal Week 1 Update` / 공개 설정: **`일부공개 (Unlisted)`** 로 업로드.
4. 내일(11월 11일) 오후 Colosseum 제출 창구가 열리면 복사한 유튜브 주소를 붙여넣고 **[Submit week 1 update]** 클릭!

