# 🛡️ Gnosis Safe{Wallet} 앱 연동 및 공식 등록 가이드

본 문서는 `Agent Security Gate x402`를 [Safe{Wallet} (공식 웹앱)](https://app.safe.global)에 커스텀 앱으로 연동하여 즉시 테스트하고, 공식 Safe Apps 디렉토리에 등록 신청하는 전체 절차를 설명합니다.

---

## 1. 1분 만에 Safe{Wallet}에서 커스텀 앱으로 실행 및 테스트하기

우리 서버([Cloud Run](https://agent-security-gate-x402-212942243360.asia-northeast3.run.app))에는 이미 Gnosis Safe 표준 `manifest.json`과 `safe-icon.svg`, 그리고 Safe 임베딩을 허용하는 CSP 헤더(`frame-ancestors https://app.safe.global`)가 구현되어 있습니다.

### 단계별 실행 방법

1. 브라우저에서 **[https://app.safe.global](https://app.safe.global)** 에 접속합니다.
2. 상단 네트워크에서 지원 체인 중 하나를 선택합니다:
   - **Polygon**, **Base**, **Arbitrum**, 또는 **Ethereum**.
   - (실제 Safe 지갑이 없어도 읽기 모드나 테스트넷에서 확인 가능합니다.)
3. 좌측 사이드바 메뉴에서 **`Apps`** (또는 `Safe Apps`)를 클릭합니다.
4. 상단 탭에서 **`My custom apps`** (내 커스텀 앱)를 클릭합니다.
5. **`Add custom app`** (커스텀 앱 추가) 버튼을 누릅니다.
6. **App URL** 입력창에 아래 URL을 입력합니다:
   ```text
   https://agent-security-gate-x402-212942243360.asia-northeast3.run.app
   ```
7. Safe 인터페이스가 우리 서버의 매니페스트를 자동으로 조회하여 아래와 같이 채워집니다:
   - **App Name**: `Agent Security Gate x402`
   - **Description**: `Autonomous AI Agent Treasury Defense & FICO Credit Rating Oracle for Gnosis Safe`
   - **Icon**: 공식 보안관 SVG 아이콘 로드
8. 이용 동의 체크박스를 선택한 후 **`Add`** 버튼을 누릅니다.
9. **완료!** Safe 지갑 내부 프레임에서 실시간 차단 대시보드와 온체인 가드 상태가 매끄럽게 구동되는 것을 확인하실 수 있습니다.

---

## 2. Safe 공식 앱 디렉토리(safe-apps-list) 등재 신청

모든 Safe 전 세계 사용자가 검색창에서 바로 우리 앱을 찾아서 쓸 수 있도록 공식 디렉토리에 등록하는 방법입니다.

### 저장소 정보
- **공식 저장소**: [safe-global/safe-apps-list](https://github.com/safe-global/safe-apps-list)

### 제출 정보 템플릿
- **App Name**: `Agent Security Gate x402`
- **URL**: `https://agent-security-gate-x402-212942243360.asia-northeast3.run.app`
- **Description**: `Deterministic AI Agent Treasury Guard & Autonomous Transaction Micro-Oracle for Safe{Core}. Protects DAO multisigs against prompt injections and budget drains.`
- **Networks**: `1 (Ethereum), 137 (Polygon), 8453 (Base), 42161 (Arbitrum)`
- **Category**: `Security / Infrastructure / AI`
- **Repository**: `https://github.com/nohosa001-pixel/security-gate-x402`
- **Smart Contract (Guard)**: `contracts/SafeSecurityGateGuard.sol`
