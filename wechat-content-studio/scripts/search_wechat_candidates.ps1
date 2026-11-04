[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Topic,

    [string[]]$LongTail = @(),

    [int]$NumResults = 5,

    [string]$OutputPath
)

$ErrorActionPreference = "Stop"

if ($NumResults -lt 1 -or $NumResults -gt 20) {
    throw "NumResults must be between 1 and 20."
}

$nodeExe = "C:\Program Files\nodejs\node.exe"
$mcporterCli = "C:\Program Files\nodejs\node_modules\mcporter\dist\cli.js"
if (-not (Test-Path -LiteralPath $nodeExe) -or -not (Test-Path -LiteralPath $mcporterCli)) {
    throw "agent-reach Exa runtime is unavailable: node or mcporter was not found."
}

$cacheDir = Join-Path $env:TEMP "wechat-content-studio-npm-cache"
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
$env:NPM_CONFIG_CACHE = $cacheDir

$queries = [System.Collections.Generic.List[string]]::new()
$queries.Add("$Topic site:mp.weixin.qq.com/s")
$queries.Add("$Topic 案例 实操 site:mp.weixin.qq.com/s")
$queries.Add("$Topic 规范 标准 site:mp.weixin.qq.com/s")
foreach ($item in $LongTail) {
    if (-not [string]::IsNullOrWhiteSpace($item)) {
        $queries.Add("$item site:mp.weixin.qq.com/s")
    }
}

$seen = @{}
$candidates = [System.Collections.Generic.List[object]]::new()
$failures = [System.Collections.Generic.List[object]]::new()

foreach ($query in $queries) {
    $escapedQuery = $query.Replace('"', '""')
    $call = "exa.web_search_exa(query: `"$escapedQuery`", numResults: $NumResults)"
    $rawOutput = & $nodeExe $mcporterCli call $call 2>&1
    $exitCode = $LASTEXITCODE
    $rawText = ($rawOutput | Out-String).Trim()

    if ($exitCode -ne 0) {
        $failures.Add([ordered]@{
            query = $query
            error = $rawText
        })
        continue
    }

    $blocks = [regex]::Split($rawText, '(?m)^---\s*$')
    foreach ($block in $blocks) {
        $titleMatch = [regex]::Match($block, '(?m)^Title:\s*(.+)$')
        $urlMatch = [regex]::Match($block, '(?m)^URL:\s*(https://mp\.weixin\.qq\.com/s/\S+)\s*$')
        if (-not $titleMatch.Success -or -not $urlMatch.Success) {
            continue
        }

        $url = $urlMatch.Groups[1].Value.Trim()
        if ($seen.ContainsKey($url)) {
            continue
        }
        $seen[$url] = $true

        $publishedMatch = [regex]::Match($block, '(?m)^Published:\s*(.+)$')
        $authorMatch = [regex]::Match($block, '(?m)^Author:\s*(.+)$')
        $highlightsMatch = [regex]::Match($block, '(?s)Highlights:\s*(.+)$')
        $summary = if ($highlightsMatch.Success) { $highlightsMatch.Groups[1].Value } else { "" }
        $summary = (($summary -replace '\s*\.\.\.\s*', ' ') -replace '\s+', ' ').Trim()
        if ($summary.Length -gt 600) {
            $summary = $summary.Substring(0, 600)
        }

        $candidates.Add([ordered]@{
            title = $titleMatch.Groups[1].Value.Trim()
            url = $url
            source_account = if ($authorMatch.Success) { $authorMatch.Groups[1].Value.Trim() } else { "N/A" }
            publish_date = if ($publishedMatch.Success) { $publishedMatch.Groups[1].Value.Trim() } else { "N/A" }
            query = $query
            machine_summary = $summary
            source_role = "structure_reference"
            supported_claims = @()
            verification = "search_result_only"
            risk_flags = @("unverified_original", "possible_repost")
            status = "candidate"
        })
    }
}

$runStatus = if ($candidates.Count -eq 0) { "failed" } elseif ($failures.Count -gt 0) { "partial" } else { "ok" }
$result = [ordered]@{
    generated_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
    topic = $Topic
    backend = "agent-reach/exa"
    status = $runStatus
    queries = $queries
    candidate_count = $candidates.Count
    candidates = $candidates
    failures = $failures
}

$json = $result | ConvertTo-Json -Depth 8
if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
    $resolvedOutput = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)
    $parent = Split-Path -Parent $resolvedOutput
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    Set-Content -LiteralPath $resolvedOutput -Value $json -Encoding utf8
}

$json
if ($candidates.Count -eq 0) {
    exit 2
}
