#!/usr/bin/env pwsh
# Omega_KG Post-Commit Hook (PowerShell Native)

$ErrorActionPreference = 'SilentlyContinue'  # Never block commits

# Locate session log
$sessionLog = if ($env:OMEGA_VAULT) {
    "$env:OMEGA_VAULT\Sessions\$(Get-Date -Format yyyy-MM-dd).md"
} else {
    "$env:USERPROFILE\Documents\OmegaVault.as\Sessions\$(Get-Date -Format yyyy-MM-dd).md"
}

# Abort if no session log
if (-not (Test-Path $sessionLog)) { exit 0 }

# Capture commit metadata
$commitHash = git rev-parse --short HEAD
$commitMsg = git log -1 --pretty=%B
$repoName = Split-Path -Leaf (git rev-parse --show-toplevel)
$timestamp = Get-Date -Format HH:mm:ss
$branch = git rev-parse --abbrev-ref HEAD

# Extract Linear ID (regex capture)
$linearMatch = [regex]::Match($commitMsg, '(LIN-\d+|#\d+)')
$linearId = if ($linearMatch.Success) { $linearMatch.Value } else { $null }

# Extract file changes
$filesChanged = git diff-tree --no-commit-id --name-status -r HEAD
$numFiles = ($filesChanged | Measure-Object -Line).Lines

# Detect commit type
$commitType = if ($commitMsg -match '^(feat|fix|docs|style|refactor|test|chore|perf|ci|build)') {
    $matches[1]
} else {
    'change'
}

# Build markdown entry
$entry = @"

#### [$timestamp] 🔨 Commit: ``$commitHash`` [$repoName]
**Branch:** ``$branch`` | **Type:** ``$commitType`` | **Files:** $numFiles
"@

if ($linearId) {
    $entry += " | **Linear:** [[$linearId]]"
}

$entry += @"
``````
$commitMsg
``````

<details>
<summary>Changed files</summary>
``````
$filesChanged
``````

</details>

"@

# Atomic append with mutex
$mutex = New-Object System.Threading.Mutex($false, "OmegaSessionLog")
try {
    $mutex.WaitOne() | Out-Null
    Add-Content -Path $sessionLog -Value $entry
} finally {
    $mutex.ReleaseMutex()
}

exit 0
