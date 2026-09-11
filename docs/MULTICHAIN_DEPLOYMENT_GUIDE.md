# 🌐 MetaMask & Remix 기반 멀티체인 (Polygon · Base · Arbitrum) 배포 및 등록 가이드

본 문서는 **MetaMask(메타마스크)** 지갑을 사용하여 `contracts/SecurityGateConsumer.sol` 가드 컨트랙트를 **Base**, **Arbitrum**, **Polygon** 메인넷 및 테스트넷에 수수료 100원 수준으로 손쉽게 배포하고 등록하는 방법을 안내합니다.

---

## 📌 체인별 기본 네트워크 정보

| 체인 명 | Chain ID | 기본 통화 | 공식 Circle Native USDC 컨트랙트 | 블록 탐색기 |
| :--- | :--- | :--- | :--- | :--- |
| **Polygon Mainnet** | `137` | POL | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` | [PolygonScan](https://polygonscan.com) |
| **Base Mainnet** | `8453` | ETH | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | [BaseScan](https://basescan.org) |
| **Arbitrum One** | `42161` | ETH | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | [Arbiscan](https://arbiscan.io) |
| **Base Sepolia (테스트)** | `84532` | ETH | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` | [Base Sepolia Scan](https://sepolia.basescan.org) |
| **Arbitrum Sepolia (테스트)**| `421614` | ETH | `0x75faf114eafb1BDbe2F0316DF893fd58CE46AA4d` | [Arbiscan Sepolia](https://sepolia.arbiscan.io) |

---

## 🚀 방법 A: 웹 브라우저 Remix IDE + 메타마스크 클릭 배포 (가장 추천)

코딩 없이 브라우저에서 메타마스크 팝업 승인만 눌러 배포하는 가장 직관적인 방식입니다.

### 1단계. 메타마스크 네트워크 확인 및 가스비 준비
1. 메타마스크 상단 좌측 네트워크 드롭다운에서 **Base** 또는 **Arbitrum One**을 선택합니다.
   - *목록에 없는 경우: '네트워크 추가' 버튼을 누르면 기본 목록에서 클릭 한 번으로 추가됩니다.*
2. 배포 트랜잭션 가스비용으로 **약 0.0005 ETH (약 1,500원 ~ 2,000원)**를 지갑에 준비합니다.

### 2단계. Remix Ethereum IDE 접속 및 코드 복사
1. 웹 브라우저에서 [Remix IDE (https://remix.ethereum.org)](https://remix.ethereum.org)에 접속합니다.
2. 좌측 탐색기 `contracts/` 폴더 우클릭 → `New File` 클릭 후 `SecurityGateConsumer.sol`을 생성합니다.
3. 우리 프로젝트의 [`contracts/SecurityGateConsumer.sol`](file:///c:/Users/nohos/OneDrive/바탕%20화면/security-gate-x402/contracts/SecurityGateConsumer.sol) 전체 코드를 복사하여 붙여넣습니다.

### 3단계. 컴파일러 설정
1. 좌측 3번째 아이콘 **Solidity Compiler**를 클릭합니다.
2. **Compiler**: `0.8.20` 이상을 선택합니다.
3. **Advanced Configurations** → `Enable optimization` 체크 (Runs: 200).
4. **Compile SecurityGateConsumer.sol** 파란색 버튼을 누릅니다 (초록색 체크 표시 확인).

### 4단계. 메타마스크 연결 및 배포(Deploy)
1. 좌측 4번째 아이콘 **Deploy & Run Transactions**를 클릭합니다.
2. **ENVIRONMENT**: 드롭다운에서 **`Injected Provider - MetaMask`**를 선택합니다.
   - 메타마스크 팝업이 뜨면 계정 연결을 승인합니다.
   - Remix 화면에 `Custom (8453) network` (Base) 또는 `Custom (42161) network` (Arbitrum)이 표시됩니다.
3. **Contract**: `SecurityGateConsumer`가 선택되어 있는지 확인합니다.
4. **Deploy 입력란**:
   - `_oracleSigner` 인자에 **우리 서버의 서명자 지갑 주소** (또는 본인 관리자 지갑 주소 `0x...`)를 입력합니다.
5. 주황색 **Deploy** 버튼을 누릅니다.
6. 메타마스크 승인 창이 뜨면 가스비(약 100원 수준)를 확인하고 **[확인/승인]**을 누릅니다.

### 5단계. 주소 등록
1. 약 2~5초 뒤 하단 `Deployed Contracts`에 배포된 컨트랙트가 표시됩니다.
2. 컨트랙트 주소 옆 복사 버튼을 눌러 주소를 복사합니다.
3. 프로젝트의 [`app/multi_chain.py`](file:///c:/Users/nohos/OneDrive/바탕%20화면/security-gate-x402/app/multi_chain.py) 파일의 `consumer_contract_address` 항목에 붙여넣으면 등록이 완료됩니다!

---

## ⚡ 방법 B: CLI 파이썬 자동화 스크립트로 1초 만에 배포하기

메타마스크의 개인키를 `.env` 파일에 기재하고 명령어 1회로 배포·검증·설정 저장까지 마치는 방식입니다.

### 1단계. 메타마스크 개인키 복사
1. 메타마스크 우측 상단 메뉴 `⋮` → **계정 세부 정보** → **개인키 표시**.
2. 비밀번호 입력 후 개인키(`0x...`)를 복사합니다.

### 2단계. `.env` 파일에 설정
```env
DEPLOYER_PRIVATE_KEY=0x내_메타마스크_개인키
SERVER_WALLET_ADDRESS=0x오라클_서명자_지갑주소
```

### 3단계. 원클릭 배포 실행
터미널에서 원하는 체인을 지정하여 실행합니다:

```bash
# 🔵 Base 메인넷에 배포
python scripts/deploy_multichain.py --chain base

# 🔷 Arbitrum One 메인넷에 배포
python scripts/deploy_multichain.py --chain arbitrum

# 🟣 Polygon 메인넷에 배포
python scripts/deploy_multichain.py --chain polygon

# 🧪 Base Sepolia 테스트넷에 배포
python scripts/deploy_multichain.py --chain base-sepolia
```

실행 결과로 배포 주소 및 블록 넘버, 온체인 검증 결과가 터미널에 출력되고, `deployed_contracts_base.json` 또는 `deployed_contracts_arbitrum.json` 파일이 자동 생성됩니다.

---

## 🛡️ 등록 후 멀티체인 정상 작동 확인

배포 완료 후 FastAPI 서버를 실행하고 다음 명령으로 확인할 수 있습니다:

```bash
# 1. 등록된 모든 체인 확인
curl http://localhost:8080/api/v1/gate/chains

# 2. Base 네트워크의 x402 챌린지 및 네이티브 USDC 주소 확인
curl "http://localhost:8080/api/v1/gate/challenge?network=base"

# 3. Arbitrum 네트워크의 x402 챌린지 확인
curl "http://localhost:8080/api/v1/gate/challenge?network=arbitrum"
```
