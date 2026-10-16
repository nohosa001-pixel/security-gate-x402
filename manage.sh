#!/usr/bin/env bash
# ==============================================================================
# A.GRID Security Gate x402 - Production Operations Manager (manage.sh)
# ==============================================================================

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function print_banner() {
    clear 2>/dev/null || true
    echo -e "${CYAN}"
    echo "=================================================================="
    echo "   [A.GRID] Security Gate x402 Sovereign Ops Manager"
    echo "   5-Node Mesh | ERC-4626 Shield Pool | EIP-3009 Batch Settler"
    echo "=================================================================="
    echo -e "${NC}"
}

function show_status() {
    echo -e "${CYAN}[*] 9대 컨테이너 헬스체크 및 실행 상태 조회...${NC}"
    docker compose ps
    echo ""
    echo -e "${CYAN}[*] 컨테이너 리소스 사용량 (CPU / Memory)...${NC}"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

function show_logs() {
    echo -e "${GREEN}[*] 게이트웨이 매출 수납 및 온체인 배치 정산 실시간 로그 모니터링...${NC}"
    echo -e "${YELLOW}(종료하려면 Ctrl+C를 누르세요)${NC}"
    docker compose logs -f --tail=50 mesh-gateway x402-batch-settler
}

function show_all_logs() {
    echo -e "${GREEN}[*] 전체 9대 서비스 로그 실시간 스트리밍...${NC}"
    echo -e "${YELLOW}(종료하려면 Ctrl+C를 누르세요)${NC}"
    docker compose logs -f --tail=30
}

function update_system() {
    echo -e "${YELLOW}[*] 전체 시스템 최신 코드 반영 및 무중단 롤링 빌드 시작...${NC}"
    if [ -d ".git" ]; then
        echo -e "${CYAN}[1/3] git pull 최신 소스코드 동기화...${NC}"
        git pull || echo -e "${YELLOW}Warning: git pull failed or local changes present. Continuing build...${NC}"
    fi
    echo -e "${CYAN}[2/3] 도커 이미지 고속 빌드 (uv 캐시 활용)...${NC}"
    docker compose build
    echo -e "${CYAN}[3/3] 무중단 컨테이너 교체 (Zero-Downtime)...${NC}"
    docker compose up -d
    echo -e "${GREEN}[✔] 시스템 무중단 업데이트 완료!${NC}"
    docker compose ps
}

function update_single_node() {
    targetNode="$1"
    if [ -z "$targetNode" ]; then
        echo -e "${CYAN}업데이트할 개별 노드를 선택하세요 (다른 노드는 끄지 않고 무중단 교체):${NC}"
        echo " 1) mesh-gateway          (관문 라우터)"
        echo " 2) security-gate-node    (AST/DLP 엔진)"
        echo " 3) cleanweb-node         (웹 살균)"
        echo " 4) eudr-oracle-node      (산림벌채 검증)"
        echo " 5) minerals-oracle-node  (광물 시세)"
        echo " 6) logistics-oracle-node (DCSA eBL 및 PoD)"
        echo " 7) zk-egress-proxy       (비밀키 금고)"
        echo " 8) x402-batch-settler    (블록체인 정산 데몬)"
        read -p "번호 입력 [1-8]: " idx
        case $idx in
            1) targetNode="mesh-gateway" ;;
            2) targetNode="security-gate-node" ;;
            3) targetNode="cleanweb-node" ;;
            4) targetNode="eudr-oracle-node" ;;
            5) targetNode="minerals-oracle-node" ;;
            6) targetNode="logistics-oracle-node" ;;
            7) targetNode="zk-egress-proxy" ;;
            8) targetNode="x402-batch-settler" ;;
            *) echo -e "${RED}잘못된 입력입니다.${NC}"; return ;;
        esac
    fi
    echo -e "${YELLOW}[*] ${targetNode} 단일 컨테이너 무중단 빌드 및 롤링 교체 시작...${NC}"
    docker compose up -d --build --no-deps "$targetNode"
    echo -e "${GREEN}[✔] ${targetNode} 개별 무중단 업데이트 완료!${NC}"
}

function restart_specific() {
    echo -e "${CYAN}재시작할 서비스를 선택하세요:${NC}"
    echo " 1) mesh-gateway          (관문 라우터)"
    echo " 2) security-gate-node    (AST/DLP 엔진)"
    echo " 3) cleanweb-node         (웹 살균)"
    echo " 4) eudr-oracle-node      (산림벌채 검증)"
    echo " 5) minerals-oracle-node  (광물 시세)"
    echo " 6) logistics-oracle-node (DCSA eBL 및 PoD)"
    echo " 7) zk-egress-proxy       (비밀키 금고)"
    echo " 8) x402-batch-settler    (블록체인 정산 데몬)"
    echo " 9) redis-ledger          (공유 세션 원장)"
    read -p "번호 입력 [1-9]: " svc_idx
    case $svc_idx in
        1) target="mesh-gateway" ;;
        2) target="security-gate-node" ;;
        3) target="cleanweb-node" ;;
        4) target="eudr-oracle-node" ;;
        5) target="minerals-oracle-node" ;;
        6) target="logistics-oracle-node" ;;
        7) target="zk-egress-proxy" ;;
        8) target="x402-batch-settler" ;;
        9) target="redis-ledger" ;;
        *) echo -e "${RED}잘못된 입력입니다.${NC}"; return ;;
    esac
    echo -e "${YELLOW}[*] ${target} 컨테이너 재시작 중...${NC}"
    docker compose restart "$target"
    echo -e "${GREEN}[✔] ${target} 재시작 완료!${NC}"
}

function check_tests() {
    echo -e "${CYAN}[*] 파이썬 통합 및 단위 테스트 전체 실행...${NC}"
    if [ -f ".venv/bin/pytest" ]; then
        .venv/bin/pytest tests/test_agentic_shield_pool.py tests/test_logistics_pod_escrow.py
    elif command -v pytest &> /dev/null; then
        pytest tests/test_agentic_shield_pool.py tests/test_logistics_pod_escrow.py
    else
        python -m pytest tests/test_agentic_shield_pool.py tests/test_logistics_pod_escrow.py
    fi
}

function backup_redis() {
    echo -e "${CYAN}[*] Redis EIP-3009 바우처 원장 데이터 백업...${NC}"
    mkdir -p backups
    docker compose exec redis-ledger redis-cli bgsave || true
    echo -e "${GREEN}[✔] Redis 백업 신호 전달 완료 (AOF 영속성 활성화 상태).${NC}"
}

function start_all() {
    echo -e "${CYAN}[*] 전체 5-Node 메시 인프라 기동...${NC}"
    chmod 600 .env .env.secrets 2>/dev/null || true
    docker compose up -d --build
    echo -e "${GREEN}[✔] 전체 인프라가 정상적으로 가동되었습니다!${NC}"
}

function stop_all() {
    echo -e "${YELLOW}[!] 경고: 5-Node 메시 시스템을 완전히 정지합니다.${NC}"
    read -p "정말 정지하시겠습니까? (y/N): " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        docker compose down
        echo -e "${GREEN}[✔] 시스템이 안전하게 정지되었습니다.${NC}"
    fi
}

# ==============================================================================
# CLI Argument Dispatch or Interactive Menu
# ==============================================================================
if [ -n "$1" ]; then
    case "$1" in
        status) show_status ;;
        logs) show_logs ;;
        all-logs) show_all_logs ;;
        update) update_system ;;
        update-node) update_single_node "$2" ;;
        restart) restart_specific ;;
        start) start_all ;;
        stop) stop_all ;;
        test) check_tests ;;
        backup) backup_redis ;;
        *)
            echo "사용법: $0 {status|logs|all-logs|update|update-node <node>|restart|start|stop|test|backup}"
            exit 1
            ;;
    esac
    exit 0
fi

while true; do
    print_banner
    echo "  [1] 전체 시스템 상태 및 자원 점검 (Status & Resource)"
    echo "  [2] 실시간 매출 및 온체인 정산 로그 모니터링 (Live Traffic)"
    echo "  [3] 전체 9개 컨테이너 상세 로그 보기 (All Logs)"
    echo "  [4] 깃 전체 동기화 및 전면 업데이트 (Full System Update)"
    echo -e "  ${YELLOW}[5] 🛠️  특정 노드 개별 무중단 업데이트 (Update Single Node)${NC}"
    echo "  [6] 특정 노드 단순 재시작 (Restart Specific Node)"
    echo "  [7] 스마트 컨트랙트 및 오라클 테스트 검증 (Pytest)"
    echo "  [8] 전체 시스템 시작 (Docker Compose Up)"
    echo "  [9] 전체 시스템 정지 (Docker Compose Down)"
    echo -e "  ${YELLOW}[0] 나가기 (Exit)${NC}"
    echo ""
    read -p "원하시는 작업 번호를 선택하세요 [0-9]: " choice
    echo ""
    case $choice in
        1) show_status; read -p "엔터를 누르면 메뉴로 돌아갑니다..." ;;
        2) show_logs ;;
        3) show_all_logs ;;
        4) update_system; read -p "엔터를 누르면 메뉴로 돌아갑니다..." ;;
        5) update_single_node; read -p "엔터를 누르면 메뉴로 돌아갑니다..." ;;
        6) restart_specific; read -p "엔터를 누르면 메뉴로 돌아갑니다..." ;;
        7) check_tests; read -p "엔터를 누르면 메뉴로 돌아갑니다..." ;;
        8) start_all; read -p "엔터를 누르면 메뉴로 돌아갑니다..." ;;
        9) stop_all; read -p "엔터를 누르면 메뉴로 돌아갑니다..." ;;
        0) echo "안전하게 종료합니다."; exit 0 ;;
        *) echo -e "${RED}잘못된 번호입니다.${NC}"; sleep 1 ;;
    esac
done
