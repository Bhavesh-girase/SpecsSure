# ============================================================
# SpecSure API Test Script
# Run from: PS C:\coding\SpecSure>  .\test_api.ps1
# Prerequisites: docker compose up -d  (site must be running)
# ============================================================

# Auto-detect active port (8000 for local dev or 8001 for docker/forwarder)
$PORT = 8000
try {
    $null = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/health" -TimeoutSec 1 -ErrorAction Stop
    $PORT = 8001
} catch {
    $PORT = 8000
}
$BASE = "http://localhost:$PORT/api/v1"
$pass = 0
$fail = 0
$total = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Url,
        [string]$Body,
        [string]$ContentType,
        [string]$ExpectContains
    )
    $script:total++
    Write-Host ""
    Write-Host "-----------------------------------------------" -ForegroundColor DarkGray
    Write-Host "TEST $script:total : $Name" -ForegroundColor Cyan
    Write-Host "  $Method $Url" -ForegroundColor DarkGray

    try {
        $params = @{
            Method = $Method
            Uri    = $Url
            UseBasicParsing = $true
            TimeoutSec = 120
        }
        if ($Body -and $ContentType) {
            $params.Body = $Body
            $params.ContentType = $ContentType
        }

        $response = Invoke-RestMethod @params
        $json = $response | ConvertTo-Json -Depth 10 -Compress

        # Truncate for display
        if ($json.Length -gt 500) {
            $display = $json.Substring(0, 500) + "..."
        } else {
            $display = $json
        }
        Write-Host "  Response: $display" -ForegroundColor DarkGray

        if ($ExpectContains -and ($json -notlike "*$ExpectContains*")) {
            Write-Host "  FAIL - expected to contain: $ExpectContains" -ForegroundColor Red
            $script:fail++
        } else {
            Write-Host "  PASS" -ForegroundColor Green
            $script:pass++
        }
    }
    catch {
        Write-Host "  FAIL - $($_.Exception.Message)" -ForegroundColor Red
        $script:fail++
    }
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Yellow
Write-Host "  SpecSure API Test Suite" -ForegroundColor Yellow
Write-Host "  Base URL: $BASE" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Yellow

# ── 1. HEALTH CHECK ──
Test-Endpoint -Name "Health Check" -Method "GET" -Url "$BASE/health" -ExpectContains "total_standards"

# ── 2. LIST ALL STANDARDS ──
Test-Endpoint -Name "List Standards (first 20)" -Method "GET" -Url "$BASE/standards"

# ── 3. FILTER BY DIVISION ──
$divUrl = "$BASE/standards?division=CED" + "&" + "limit=5"
Test-Endpoint -Name "Filter Standards by Division (CED)" -Method "GET" -Url $divUrl

# ── 4. SEARCH BY KEYWORD ──
$searchUrl = "$BASE/standards?search=cement" + "&" + "limit=5"
Test-Endpoint -Name "Search Standards keyword (cement)" -Method "GET" -Url $searchUrl -ExpectContains "cement"

# ── 5. GET SINGLE STANDARD DETAIL ──
Test-Endpoint -Name "Get Standard Detail (IS 269:2015)" -Method "GET" -Url "$BASE/standards/IS 269:2015" -ExpectContains "269"

# ── 6. KNOWLEDGE GRAPH - Cement ──
Test-Endpoint -Name "Knowledge Graph for IS 269:2015 (depth=2)" -Method "GET" -Url "$BASE/standards/IS 269:2015/graph?depth=2" -ExpectContains "nodes"

# ── 7. KNOWLEDGE GRAPH - Steel ──
Test-Endpoint -Name "Knowledge Graph for IS 1786:2008 (depth=2)" -Method "GET" -Url "$BASE/standards/IS 1786:2008/graph?depth=2" -ExpectContains "edges"

# ── 8. SEMANTIC SEARCH - HDPE ──
Test-Endpoint -Name "Semantic Search (HDPE pipe)" -Method "POST" -Url "$BASE/search" -Body '{"query":"HDPE pipe for water supply","top_k":5}' -ContentType "application/json" -ExpectContains "results"

# ── 9. SEMANTIC SEARCH - Cement ──
Test-Endpoint -Name "Semantic Search (Portland cement)" -Method "POST" -Url "$BASE/search" -Body '{"query":"Ordinary Portland Cement 43 grade for concrete","top_k":5}' -ContentType "application/json" -ExpectContains "results"

# ── 10. SEMANTIC SEARCH - Electrical ──
Test-Endpoint -Name "Semantic Search (PVC copper wire)" -Method "POST" -Url "$BASE/search" -Body '{"query":"PVC insulated copper wire 1100V for building wiring","top_k":5}' -ContentType "application/json" -ExpectContains "results"

# ── 11. QUICK ANALYZE ──
Test-Endpoint -Name "Quick Analyze (TMT steel bars)" -Method "POST" -Url "$BASE/analyze/quick" -Body '{"query":"High strength TMT steel bars for RCC construction","top_k":5}' -ContentType "application/json" -ExpectContains "results"

# ── SUMMARY ──
Write-Host ""
Write-Host "================================================" -ForegroundColor Yellow
Write-Host "  TEST RESULTS" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Yellow
Write-Host "  Total:  $total" -ForegroundColor White
Write-Host "  Passed: $pass" -ForegroundColor Green
if ($fail -gt 0) {
    Write-Host "  Failed: $fail" -ForegroundColor Red
} else {
    Write-Host "  Failed: $fail" -ForegroundColor Green
}
Write-Host "================================================" -ForegroundColor Yellow
Write-Host ""
