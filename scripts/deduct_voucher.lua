-- KEYS[1]: session_key (예: "voucher:0xAgentWallet:0xSessionNonce")
-- ARGV[1]: new_signed_value (에이전트가 보낸 최신 EIP-3009 누적 서명 금액)
-- ARGV[2]: cost_to_deduct   (이번 오라클 호출 비용, 예: 10000)
-- ARGV[3]: oracle_namespace (예: "minerals", "eudr", "logistics")
-- ARGV[4]: raw_voucher_json (최신 서명 데이터 전체 JSON)

local current_max = tonumber(redis.call("HGET", KEYS[1], "cumulative_value") or "0")
local current_spent = tonumber(redis.call("HGET", KEYS[1], "total_spent") or "0")
local new_val = tonumber(ARGV[1])
local cost = tonumber(ARGV[2])

-- 1. High-Water Mark 갱신 (더 큰 금액의 바우처가 들어오면 덮어쓰기)
if new_val > current_max then
    current_max = new_val
    redis.call("HSET", KEYS[1], "cumulative_value", current_max)
    redis.call("HSET", KEYS[1], "latest_voucher_json", ARGV[4])
end

-- 2. 잔액 부족 여부 원자적 검사
local projected_spent = current_spent + cost
if projected_spent > current_max then
    return {-1, current_max - current_spent} -- 잔액 부족 에러 반환
end

-- 3. 총 사용액 및 개별 오라클 노드별 매출 기여도 동시 증가
redis.call("HSET", KEYS[1], "total_spent", projected_spent)
redis.call("HINCRBY", KEYS[1], "oracle:" .. ARGV[3], cost)
redis.call("SADD", "active_voucher_keys", KEYS[1])

return {1, current_max - projected_spent} -- 성공 및 남은 크레딧 반환
