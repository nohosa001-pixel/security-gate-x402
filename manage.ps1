param (
    [string]$Action = "",
    [string]$Node = ""
)

# Windows PowerShell UTF-8 인코딩 강제 설정 (한글 깨짐 방지)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
try { chcp 65001 > $null } catch {}

function Show-Banner {
    Clear-Host
    Write-Host "==================================================================" -ForegroundColor Cyan
    Write-Host "   [A.GRID] Security Gate x402 Sovereign Ops Manager (Windows)" -ForegroundColor Cyan
    Write-Host "   5-Node Mesh | ERC-4626 Shield Pool | EIP-3009 Batch Settler" -ForegroundColor Cyan
    Write-Host "==================================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Show-Status {
    Write-Host "[*] 9대 컨테이너 헬스체크 및 실행 상태 조회..." -ForegroundColor Cyan
    docker compose ps
    Write-Host ""
    Write-Host "[*] 컨테이너 리소스 사용량 (CPU / Memory)..." -ForegroundColor Cyan
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

function Show-Logs {
    Write-Host "[*] 게이트웨이 매출 수납 및 온체인 배치 정산 실시간 로그 모니터링..." -ForegroundColor Green
    Write-Host "(종료하려면 Ctrl+C를 누르세요)" -ForegroundColor Yellow
    docker compose logs -f --tail=50 mesh-gateway x402-batch-settler
}

function Show-AllLogs {
    Write-Host "[*] 전체 9대 서비스 로그 실시간 스트리밍..." -ForegroundColor Green
    Write-Host "(종료하려면 Ctrl+C를 누르세요)" -ForegroundColor Yellow
    docker compose logs -f --tail=30
}

function Update-System {
    Write-Host "[*] 전체 시스템 최신 코드 반영 및 무중단 롤링 빌드 시작..." -ForegroundColor Yellow
    if (Test-Path ".git") {
        Write-Host "[1/3] git pull 최신 소스코드 동기화..." -ForegroundColor Cyan
        git pull
    }
    Write-Host "[2/3] 도커 이미지 고속 빌드 (uv 캐시 활용)..." -ForegroundColor Cyan
    docker compose build
    Write-Host "[3/3] 무중단 컨테이너 교체 (Zero-Downtime)..." -ForegroundColor Cyan
    docker compose up -d
    Write-Host "[OK] 전체 시스템 무중단 업데이트 완료!" -ForegroundColor Green
    docker compose ps
}

function Update-SingleNode {
    param([string]$targetNode = "")
    if ($targetNode -eq "") {
        Write-Host "업데이트할 개별 노드를 선택하세요 (다른 노드는 끄지 않고 무중단 교체):" -ForegroundColor Cyan
        Write-Host " 1. mesh-gateway          (관문 라우터)"
        Write-Host " 2. security-gate-node    (AST/DLP 엔진)"
        Write-Host " 3. cleanweb-node         (웹 살균)"
        Write-Host " 4. eudr-oracle-node      (산림벌채 검증)"
        Write-Host " 5. minerals-oracle-node  (광물 시세)"
        Write-Host " 6. logistics-oracle-node (DCSA eBL 및 PoD)"
        Write-Host " 7. zk-egress-proxy       (비밀키 금고)"
        Write-Host " 8. x402-batch-settler    (블록체인 정산 데몬)"
        $idx = Read-Host "번호 입력 [1-8]"
        switch ($idx) {
            "1" { $targetNode = "mesh-gateway" }
            "2" { $targetNode = "security-gate-node" }
            "3" { $targetNode = "cleanweb-node" }
            "4" { $targetNode = "eudr-oracle-node" }
            "5" { $targetNode = "minerals-oracle-node" }
            "6" { $targetNode = "logistics-oracle-node" }
            "7" { $targetNode = "zk-egress-proxy" }
            "8" { $targetNode = "x402-batch-settler" }
            default { Write-Host "잘못된 입력입니다." -ForegroundColor Red; return }
        }
    }
    Write-Host "[*] $targetNode 단일 컨테이너 무중단 빌드 및 롤링 교체 시작..." -ForegroundColor Yellow
    docker compose up -d --build --no-deps $targetNode
    Write-Host "[OK] $targetNode 개별 무중단 업데이트 완료!" -ForegroundColor Green
}

function Restart-Specific {
    Write-Host "재시작할 서비스를 선택하세요:" -ForegroundColor Cyan
    Write-Host " 1. mesh-gateway          (관문 라우터)"
    Write-Host " 2. security-gate-node    (AST/DLP 엔진)"
    Write-Host " 3. cleanweb-node         (웹 살균)"
    Write-Host " 4. eudr-oracle-node      (산림벌채 검증)"
    Write-Host " 5. minerals-oracle-node  (광물 시세)"
    Write-Host " 6. logistics-oracle-node (DCSA eBL 및 PoD)"
    Write-Host " 7. zk-egress-proxy       (비밀키 금고)"
    Write-Host " 8. x402-batch-settler    (블록체인 정산 데몬)"
    Write-Host " 9. redis-ledger          (공유 세션 원장)"
    $idx = Read-Host "번호 입력 [1-9]"
    $target = ""
    switch ($idx) {
        "1" { $target = "mesh-gateway" }
        "2" { $target = "security-gate-node" }
        "3" { $target = "cleanweb-node" }
        "4" { $target = "eudr-oracle-node" }
        "5" { $target = "minerals-oracle-node" }
        "6" { $target = "logistics-oracle-node" }
        "7" { $target = "zk-egress-proxy" }
        "8" { $target = "x402-batch-settler" }
        "9" { $target = "redis-ledger" }
        default { Write-Host "잘못된 입력입니다." -ForegroundColor Red; return }
    }
    Write-Host "[*] $target 컨테이너 재시작 중..." -ForegroundColor Yellow
    docker compose restart $target
    Write-Host "[OK] $target 재시작 완료!" -ForegroundColor Green
}

function Run-Tests {
    Write-Host "[*] 파이썬 통합 및 단위 테스트 전체 실행..." -ForegroundColor Cyan
    if (Test-Path ".venv\Scripts\pytest.exe") {
        & .venv\Scripts\pytest.exe tests/test_agentic_shield_pool.py tests/test_logistics_pod_escrow.py
    } else {
        python -m pytest tests/test_agentic_shield_pool.py tests/test_logistics_pod_escrow.py
    }
}

function Start-All {
    Write-Host "[*] 전체 5-Node 메시 인프라 기동..." -ForegroundColor Cyan
    docker compose up -d --build
    Write-Host "[OK] 전체 인프라가 정상적으로 가동되었습니다!" -ForegroundColor Green
}

function Stop-All {
    Write-Host "[!] 경고: 5-Node 메시 시스템을 완전히 정지합니다." -ForegroundColor Yellow
    $confirm = Read-Host "정말 정지하시겠습니까? (y/N)"
    if ($confirm -match "^[Yy]$") {
        docker compose down
        Write-Host "[OK] 시스템이 안전하게 정지되었습니다." -ForegroundColor Green
    }
}

if ($Action -ne "") {
    switch ($Action) {
        "status"      { Show-Status }
        "logs"        { Show-Logs }
        "all-logs"    { Show-AllLogs }
        "update"      { Update-System }
        "update-node" { Update-SingleNode -targetNode $Node }
        "start"       { Start-All }
        "stop"        { Stop-All }
        "test"        { Run-Tests }
        default       { Write-Host "사용법: .\manage.ps1 -Action [status|logs|all-logs|update|update-node|start|stop|test]" -ForegroundColor Red }
    }
    exit 0
}

while ($true) {
    Show-Banner
    Write-Host "  [1] 전체 시스템 상태 및 자원 점검 (Status & Resource)" -ForegroundColor White
    Write-Host "  [2] 실시간 매출 및 온체인 정산 로그 모니터링 (Live Traffic)" -ForegroundColor White
    Write-Host "  [3] 전체 9개 컨테이너 상세 로그 보기 (All Logs)" -ForegroundColor White
    Write-Host "  [4] 깃 전체 동기화 및 전면 업데이트 (Full System Update)" -ForegroundColor White
    Write-Host "  [5] 🛠️  특정 노드 개별 무중단 업데이트 (Update Single Node)" -ForegroundColor Yellow
    Write-Host "  [6] 특정 노드 단순 재시작 (Restart Specific Node)" -ForegroundColor White
    Write-Host "  [7] 스마트 컨트랙트 및 오라클 테스트 검증 (Pytest)" -ForegroundColor White
    Write-Host "  [8] 전체 시스템 시작 (Docker Compose Up)" -ForegroundColor White
    Write-Host "  [9] 전체 시스템 정지 (Docker Compose Down)" -ForegroundColor White
    Write-Host "  [0] 나가기 (Exit)" -ForegroundColor Yellow
    Write-Host ""
    $choice = Read-Host "원하시는 작업 번호를 선택하세요 [0-9]"
    Write-Host ""
    switch ($choice) {
        "1" { Show-Status; Read-Host "엔터를 누르면 메뉴로 돌아갑니다..." }
        "2" { Show-Logs }
        "3" { Show-AllLogs }
        "4" { Update-System; Read-Host "엔터를 누르면 메뉴로 돌아갑니다..." }
        "5" { Update-SingleNode; Read-Host "엔터를 누르면 메뉴로 돌아갑니다..." }
        "6" { Restart-Specific; Read-Host "엔터를 누르면 메뉴로 돌아갑니다..." }
        "7" { Run-Tests; Read-Host "엔터를 누르면 메뉴로 돌아갑니다..." }
        "8" { Start-All; Read-Host "엔터를 누르면 메뉴로 돌아갑니다..." }
        "9" { Stop-All; Read-Host "엔터를 누르면 메뉴로 돌아갑니다..." }
        "0" { Write-Host "안전하게 종료합니다."; exit 0 }
        default { Write-Host "잘못된 번호입니다." -ForegroundColor Red; Start-Sleep -Seconds 1 }
    }
}
