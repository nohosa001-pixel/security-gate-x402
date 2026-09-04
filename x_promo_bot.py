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
GCP_URL = "https://agent-security-gate-x402-7qxtp3324q-du.a.run.app"
DASHBOARD_URL = "https://agent-security-gate-x402-7qxtp3324q-du.a.run.app/dashboard"
PLAYGROUND_URL = "https://agent-security-gate-x402-7qxtp3324q-du.a.run.app/playground"
PYPI_URL = "https://pypi.org/project/agent-security-gate-x402/"
GITHUB_URL = "https://github.com/nohosa001-pixel/security-gate-x402"
GLAMA_URL = "https://glama.ai/mcp/servers/nohosa001-pixel/security-gate-x402"

# X API Credentials (from .env)
X_API_KEY = os.getenv("X_API_KEY", "")
X_API_SECRET = os.getenv("X_API_SECRET", "")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN", "")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET", "")

# 1. 한국어 사용자 서비스 & UI 중심 스레드 (Korean Launch Thread)
KOREAN_THREAD = [
    (
        "🤖 AI 에이전트 개발할 때 프롬프트 주입(탈옥), 위험 코드 실행, 환각(Hallucination) 때문에 불안하셨나요? 🛡️\n\n"
        "AI 응답을 5ms 안에 정밀 검증하고 온체인 EIP-712 보증서까지 발급해주는 'Agent Security Gate x402'가 출시되었습니다! ⚡\n\n"
        "브라우저에서 로그인 없이 즉시 시뮬레이션해 보세요 👇 (1/3)\n"
        "#AI보안 #AIAgent #프롬프트인젝션 #FastAPI #Web3"
    ),
    (
        "✨ 웹 대시보드 & 플레이그라운드에서 바로 체험 가능한 4대 핵심 기능:\n\n"
        "🛡️ 탈옥·인젝션 레이더: 시스템 프롬프트 탈취 & DAN 공격 5ms 차단\n"
        "⚡ 위험 AST 코드 분석: os.system, eval, 소켓 탈취 즉시 검출\n"
        "🔍 NLI 환각 검증: 원문 대비 허위 수치 및 거짓 주장 완벽 판별\n"
        "📜 EIP-712 온체인 서명: Polygon/Base 스마트 컨트랙트 보증 calldata 발급\n\n"
        "(2/3)"
    ),
    (
        "🚀 지금 바로 브라우저 UI에서 무료로 보안 테스트를 시작하세요!\n\n"
        f"🖥️ 라이브 대시보드: {DASHBOARD_URL}\n"
        f"⚡ 인터랙티브 샌드박스: {PLAYGROUND_URL}\n"
        f"📦 PyPI 패키지: {PYPI_URL}\n\n"
        "Claude Desktop 및 Cursor MCP 1-클릭 연동도 완벽 지원합니다 🌐 (3/3)\n"
        "#개발자도구 #인공지능 #보안게이트웨이 #MCP"
    )
]

# 2. 글로벌 사용자 서비스 & UI 중심 스레드 (Global Launch Thread)
GLOBAL_THREAD = [
    (
        "🛡️ Worried about prompt injections, malicious AST code execution, and hallucinations in your AI agents?\n\n"
        "Introducing Agent Security Gate x402 ⚡\n"
        "Ultra-low latency (<5ms) deterministic guardrails + EIP-712 cryptographic on-chain attestations on Polygon, Base & Arbitrum.\n\n"
        f"Test it live in your browser without login 👇 (1/3)\n"
        f"🌐 {DASHBOARD_URL}\n"
        "#AIAgents #CyberSecurity #Guardrails #Web3 #MCP"
    ),
    (
        "⚡ Key Features available directly on the Web UI:\n\n"
        "🛡️ Injection & Jailbreak Radar: Neutralize prompt breakouts in <5ms\n"
        "⚡ Dangerous AST Analyzer: Detect eval, subprocess, os.system & socket leaks\n"
        "🔍 NLI Hallucination Check: Surface unanchored numbers & false claims\n"
        "📜 EIP-712 On-Chain Attestation: Instant ABI calldata for EVM smart contracts\n\n"
        "(2/3)"
    ),
    (
        "🚀 Integrate in 1-Click with Claude Desktop, Cursor, and Python SDK!\n\n"
        f"🖥️ Interactive Dashboard: {DASHBOARD_URL}\n"
        f"🎮 Live Playground: {PLAYGROUND_URL}\n"
        f"📦 PyPI: pip install agent-security-gate-x402\n"
        f"🐙 GitHub: {GITHUB_URL}\n\n"
        "Securing autonomous agent economies at $0.002 per micro-audit 💎 (3/3)"
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
