"""
Agent Security Gate x402 - X (Twitter) Automated Promotion & Security Alert Bot
AI 에이전트 보안 게이트 & 환각 차단 시스템용 X(Twitter) 자동 홍보 및 알림 봇
"""

import os
import sys
import time
import urllib.parse
import webbrowser
import requests
from dotenv import load_dotenv

# Windows 콘솔 UTF-8 인코딩 설정
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# .env 로드
load_dotenv(override=True)

# Configuration & Links
GCP_URL = "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app"
DASHBOARD_URL = "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/dashboard"
PLAYGROUND_URL = "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/playground"
PYPI_URL = "https://pypi.org/project/agent-security-gate-x402/"
GITHUB_URL = "https://github.com/nohosa001-pixel/security-gate-x402"
GLAMA_URL = "https://glama.ai/mcp/servers/nohosa001-pixel/security-gate-x402"

# X API Credentials (from .env)
X_API_KEY = os.getenv("X_API_KEY", "")
X_API_SECRET = os.getenv("X_API_SECRET", "")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN", "")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET", "")

# 1. 한국어 사용자 서비스 & UI 중심 스레드 (Korean Launch Thread - The Sheriff Persona)
KOREAN_THREAD = [
    (
        "🚨 자율 에이전트 금융의 무법지대를 끝낼 보안관!!! 🤠\n\n"
        "AI 에이전트한테 지갑 개인키 쥐여주고 프롬프트에 '착하게 거래해'라고 적어두셨나요?\n"
        "죄송하지만 그건 보안이 아니라 '기도(Prayer)'입니다.\n\n"
        "보이지 않는 프롬프트 인젝션 한 줄이면 에이전트는 3초 만에 지갑 잔고를 공격자에게 송금합니다.\n"
        "The Sheriff of Agent Finance: Agent Security Gate x402 👇 (1/4)\n"
        "#AI보안 #AIAgent #프롬프트인젝션 #Web3 #MCP"
    ),
    (
        "🔒 에이전트 코드에 딱 3줄만 걸어두면 끝납니다:\n\n"
        "1. 악성 쉘 탈취(`os.system`, `eval`, 역방향 소켓) 5ms 즉각 차단\n"
        "2. 할루시네이션 가짜 수치/주소 조작 원천 봉쇄\n"
        "3. Bounded-Wallet: 에이전트가 폭주해도 1회 $0.05 / 일일 $1.00 이상 절대 못 쓰게 물리적 수갑 체결 🛡️\n\n"
        "(2/4)"
    ),
    (
        "📜 '착한 말'을 믿지 마세요. 우리는 암호화 서명만 믿습니다.\n\n"
        "이미 Polygon 메인넷에 배포된 스마트 컨트랙트가 오라클의 EIP-712 안전 보증서가 없는 에이전트 트랜잭션은 가스비 1원도 못 빼가도록 온체인에서 즉시 Revert(차단)합니다.\n\n"
        "지금 브라우저에서, 보안관의 활약상을 직접 보세요!\n"
        f"🖥️ 라이브 시뮬레이터: {DASHBOARD_URL} (3/4)"
    ),
    (
        "⚡ Cursor나 Claude Desktop 쓰시는 분들은 설치도 필요 없습니다.\n\n"
        "MCP에 한 줄 추가하면 에이전트 방화벽이 바로 켜집니다:\n"
        "👉 uvx agent-security-gate-x402\n\n"
        f"📦 PyPI: {PYPI_URL}\n"
        f"🌐 Glama 레지스트리 공식 승인: {GLAMA_URL}\n\n"
        "에이전트 통장을 지키는 보안관!!! 🤠 (4/4)"
    )
]

# 2. 글로벌 사용자 서비스 & UI 중심 스레드 (Global Launch Thread - The Sheriff Persona)
GLOBAL_THREAD = [
    (
        "🤠 Giving an autonomous AI agent your wallet's private key without spend guardrails is like handing a Ferrari to a toddler and whispering 'drive carefully.'\n\n"
        "Prompt injections bypass system tags in 1 prompt.\n"
        "Hallucinations fabricate addresses.\n"
        "Infinite loops drain wallets.\n\n"
        "The Wild West is over. Meet The Sheriff of Agent Finance: Agent Security Gate x402 👇 (1/4)\n"
        "#AIAgents #Web3 #CyberSecurity #Guardrails #MCP"
    ),
    (
        "🔒 Protect any Python / LangChain / ElizaOS agent in 3 lines of code:\n\n"
        "• Deterministic <5ms prompt injection & breakout radar\n"
        "• In-memory AST sandbox killing os.system & eval\n"
        "• BoundedAgentWallet: Hard daily spend ceiling + recipient whitelist 🛡️\n\n"
        "No complex enterprise sales calls. Pure plug-and-play code. (2/4)"
    ),
    (
        "📜 We don't trust LLM vibes. We trust cryptographic signatures.\n\n"
        "Every inspection issues an EIP-712/EIP-191 attestation.\n"
        "Deployed on Polygon Mainnet (0x9E3dEE18D8139E1d20f9f7D1F6673c75727F1DDA):\n"
        "If the Sheriff hasn't signed it, the smart contract strictly reverts. Zero balance drain.\n\n"
        f"Test your malicious payloads live without login:\n"
        f"🖥️ {DASHBOARD_URL} (3/4)"
    ),
    (
        "⚡ Connect to Cursor IDE or Claude Desktop in 5 seconds via MCP:\n\n"
        "👉 uvx agent-security-gate-x402\n\n"
        f"📦 PyPI: pip install agent-security-gate-x402\n"
        f"🌐 Verified on Glama MCP Registry: {GLAMA_URL}\n"
        f"🐙 GitHub: {GITHUB_URL}\n\n"
        "Put an on-chain seatbelt on your autonomous agent before it's too late. 💎 (4/4)"
    )
]

def build_status_alert_tweet() -> str:
    """실시간 서비스 보안 상태 및 대시보드 소개 단일 트윗"""
    return (
        "🛡️ [Agent Security Gate x402 실시간 보안 알림]\n\n"
        "자율 AI 에이전트의 프롬프트 탈옥, 악성 파이썬 코드, 수치 환각을 5ms 만에 차단하는 마이크로 보안 게이트!\n\n"
        "✅ EIP-712 온체인 암호화 보증서\n"
        "✅ Claude / Cursor MCP 1-클릭 연동\n"
        "✅ 0.002 USDC 초소액 온체인 정산\n\n"
        f"👉 웹 대시보드 바로가기: {DASHBOARD_URL}\n"
        "#AI에이전트 #보안게이트웨이 #AIGuardrails"
    )

def build_security_bulletin_tweet() -> str:
    """보안 브리핑 및 실시간 검증 트윗"""
    return (
        "⚡ [AI Security Bulletin] 프롬프트 인젝션 및 허위 정보 차단 가이드\n\n"
        "DAN 탈옥 시도나 백도어 subprocess 코드가 포함된 AI 출력물, 아직도 육안으로 확인하시나요?\n\n"
        "Security Gate x402로 API 파이프라인 앞단에서 100% 결정론적(Deterministic)으로 필터링하세요.\n\n"
        f"🎮 라이브 플레이그라운드: {PLAYGROUND_URL}\n"
        "#정보보안 #AI안전 #AgentSecurity"
    )

def post_tweet_api(text: str, in_reply_to_tweet_id: str = None) -> dict:
    """X API v2를 사용하여 트윗 게시"""
    if not (X_API_KEY and X_API_SECRET and X_ACCESS_TOKEN and X_ACCESS_TOKEN_SECRET):
        return {"success": False, "error": "MISSING_API_KEYS"}

    try:
        from requests_oauthlib import OAuth1
        auth = OAuth1(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET)
        url = "https://api.twitter.com/2/tweets"
        payload = {"text": text}
        if in_reply_to_tweet_id:
            payload["reply"] = {"in_reply_to_tweet_id": in_reply_to_tweet_id}

        resp = requests.post(url, json=payload, auth=auth, headers={"Content-Type": "application/json"})
        if resp.status_code in (200, 201):
            return {"success": True, "data": resp.json()}
        else:
            return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
    except ImportError:
        return {"success": False, "error": "requests_oauthlib_not_installed"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def open_intent_tweet(text: str):
    """트위터 웹 브라우저 인텐트를 열어 1초 만에 트윗 작성창 띄우기"""
    encoded_text = urllib.parse.quote(text)
    intent_url = f"https://twitter.com/intent/tweet?text={encoded_text}"
    print(f"\n🌐 [X Web Intent URL 생성 완료]")
    print(f"👉 브라우저를 열어 트윗을 게시합니다...")
    try:
        webbrowser.open(intent_url)
    except Exception:
        pass
    print(f"직접 링크: {intent_url}\n")

def run_post_thread(thread_tweets: list, name: str):
    """스레드 포스팅 실행 (API 우선 시도 -> 미설정 시 Web Intent 안내)"""
    print(f"\n==================================================")
    print(f" 🚀 X(Twitter) [{name}] 프로모션 발송 시작")
    print(f"==================================================")

    has_api_keys = bool(X_API_KEY and X_API_SECRET and X_ACCESS_TOKEN and X_ACCESS_TOKEN_SECRET)

    if has_api_keys:
        print("🔑 X API V2 인증키 감지! 완전 자동 API 스레드 포스팅을 진행합니다...")
        parent_id = None
        for idx, tweet_text in enumerate(thread_tweets, 1):
            print(f"\n[{idx}/{len(thread_tweets)}] 트윗 전송 중...")
            result = post_tweet_api(tweet_text, in_reply_to_tweet_id=parent_id)
            if result.get("success"):
                tweet_id = result["data"]["data"]["id"]
                print(f"  ✅ 전송 성공! Tweet ID: {tweet_id}")
                print(f"  🔗 확인 링크: https://x.com/nohosa_1250/status/{tweet_id}")
                parent_id = tweet_id
                time.sleep(2)
            else:
                print(f"  ❌ API 전송 실패: {result.get('error')}")
                print("  ℹ️ 브라우저 원클릭 Intent로 전환합니다.")
                open_intent_tweet(tweet_text)
        print("\n🎉 모든 스레드 포스팅 완료!")
        print("👉 내 프로필에서 전체 확인하기: https://x.com/nohosa_1250")

    else:
        print("💡 X API Key가 .env에 설정되지 않았습니다.")
        print("🌐 브라우저 1-클릭 트윗 작성창을 자동으로 띄웁니다.")
        for idx, tweet_text in enumerate(thread_tweets, 1):
            print(f"\n--- [스레드 {idx}/{len(thread_tweets)}] ---")
            print(tweet_text)
            print("-" * 50)
            open_intent_tweet(tweet_text)
            if idx < len(thread_tweets):
                input(f"👉 {idx}번 트윗 게시 후 다음 트윗 작성을 위해 [Enter]를 누르세요...")

def run_scheduler(interval_hours: int = 6):
    """주기적 자동 알림 모드"""
    print(f"\n⏰ Security Gate X 자동 알림 스케줄러 가동 (주기: {interval_hours}시간)")
    print("종료하려면 Ctrl+C를 누르세요.\n")

    while True:
        status_tweet = build_status_alert_tweet()
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 정기 홍보 트윗 발송 시도...")

        has_api_keys = bool(X_API_KEY and X_API_SECRET and X_ACCESS_TOKEN and X_ACCESS_TOKEN_SECRET)
        if has_api_keys:
            res = post_tweet_api(status_tweet)
            if res.get("success"):
                print(f"✅ 정기 트윗 발송 성공: {res['data']['data']['id']}")
            else:
                print(f"❌ 발송 실패: {res.get('error')}")
        else:
            print("📢 발송할 트윗 내용:\n" + status_tweet)
            open_intent_tweet(status_tweet)

        print(f"\n⏳ 다음 발송까지 {interval_hours}시간 대기합니다...")
        time.sleep(interval_hours * 3600)

def main():
    print("==========================================================")
    print(" 🛡️ Agent Security Gate x402 - X (Twitter) Promo & Alert Bot")
    print(" (AI 에이전트 보안 게이트웨이 & 온체인 보증서)")
    print("==========================================================")
    print(" 1. 🇰🇷 한국어 서비스 소개 & 대시보드 스레드 게시")
    print(" 2. 🌐 글로벌(영문) 런칭 & 기능 소개 스레드 게시")
    print(" 3. 🛡️ 실시간 보안 알림 단일 트윗 게시")
    print(" 4. ⚡ AI 보안 브리핑 단일 트윗 게시")
    print(" 5. ⏰ 백그라운드 정기 자동 알림 스케줄러 실행")
    print(" 6. ⚙️ X API 연동 안내 및 상태 확인")
    print("==========================================================")

    choice = input("👉 원하시는 작업 번호를 입력하세요 (기본값 1): ").strip() or "1"

    if choice == "1":
        run_post_thread(KOREAN_THREAD, "한국어 서비스 스레드")
    elif choice == "2":
        run_post_thread(GLOBAL_THREAD, "글로벌 런칭 스레드")
    elif choice == "3":
        tweet = build_status_alert_tweet()
        print("\n" + tweet)
        if X_API_KEY and X_API_SECRET:
            res = post_tweet_api(tweet)
            if res.get("success"):
                print("✅ 트윗 전송 성공!")
            else:
                print("❌ API 전송 실패, 브라우저로 엽니다.")
                open_intent_tweet(tweet)
        else:
            open_intent_tweet(tweet)
    elif choice == "4":
        tweet = build_security_bulletin_tweet()
        print("\n" + tweet)
        if X_API_KEY and X_API_SECRET:
            res = post_tweet_api(tweet)
            if res.get("success"):
                print("✅ 트윗 전송 성공!")
            else:
                print("❌ API 전송 실패, 브라우저로 엽니다.")
                open_intent_tweet(tweet)
        else:
            open_intent_tweet(tweet)
    elif choice == "5":
        hours = input("알림 주기(시간)를 입력하세요 (기본값 6): ").strip() or "6"
        run_scheduler(int(hours))
    elif choice == "6":
        print("\n[X API 연동 상태]")
        print(f" - X_API_KEY: {'✅ 설정됨' if X_API_KEY else '❌ 미설정 (Web Intent로 작동)'}")
        print(f" - X_API_SECRET: {'✅ 설정됨' if X_API_SECRET else '❌ 미설정'}")
        print(f" - X_ACCESS_TOKEN: {'✅ 설정됨' if X_ACCESS_TOKEN else '❌ 미설정'}")
        print(f" - X_ACCESS_TOKEN_SECRET: {'✅ 설정됨' if X_ACCESS_TOKEN_SECRET else '❌ 미설정'}")
        print("\n💡 .env 파일에 X API 키를 입력하시면 완전 자동 무인 포스팅이 활성화됩니다.")
    else:
        print("잘못된 입력입니다.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--auto-korean":
            run_post_thread(KOREAN_THREAD, "한국어 서비스 스레드")
        elif arg == "--auto-global":
            run_post_thread(GLOBAL_THREAD, "글로벌 런칭 스레드")
        elif arg == "--status":
            t = build_status_alert_tweet()
            print(t)
            open_intent_tweet(t)
        elif arg == "--bulletin":
            t = build_security_bulletin_tweet()
            print(t)
            open_intent_tweet(t)
        elif arg == "--schedule":
            run_scheduler(6)
        else:
            main()
    else:
        main()
