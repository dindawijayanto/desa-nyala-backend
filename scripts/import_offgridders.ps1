[CmdletBinding()]
param(
    [string]$SourceRoot = (Join-Path $PSScriptRoot "..\..\offgridders"),
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
$source = (Resolve-Path $SourceRoot -ErrorAction Stop).Path
$target = (Join-Path $PSScriptRoot '..\engine\offgridders')
$target = [System.IO.Path]::GetFullPath($target)

if (-not (Test-Path (Join-Path $source 'Offgridders.py'))) {
    throw "Offgridders.py tidak ditemukan di '$source'. Berikan -SourceRoot ke folder clone yang benar."
}
if (-not (Test-Path (Join-Path $source 'src'))) {
    throw "Folder src tidak ditemukan di '$source'. Pastikan ini root repo Offgridders."
}
$licensePath = @('LICENSE','LICENSE.txt','COPYING') | ForEach-Object { Join-Path $source $_ } | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $licensePath) {
    throw "File lisensi upstream tidak ditemukan. Hentikan import agar lisensi dan atribusi tidak hilang."
}
if ((Test-Path $target) -and ((Get-ChildItem $target -Force | Measure-Object).Count -gt 0) -and -not $Force) {
    $marker = Join-Path $target 'UPSTREAM_SOURCE_PENDING.txt'
    if (-not (Test-Path $marker)) {
        throw "Target '$target' sudah berisi file. Gunakan -Force hanya jika memang ingin mengganti salinan engine yang ada."
    }
}

if (Test-Path $target) {
    Get-ChildItem $target -Force | Remove-Item -Recurse -Force
} else {
    New-Item -ItemType Directory -Path $target -Force | Out-Null
}

$excludedDirs = @('.git','.venv','venv','env','offgridders_env','__pycache__','simulation_results','simulation_results_365days','simulation_results_365days_detail')
$excludedPatterns = @('*.pyc','results.csv','results_*.csv','micro_grid_design_logfile.log','*.log')
function Copy-FilteredTree([string]$From, [string]$To) {
    New-Item -ItemType Directory -Path $To -Force | Out-Null
    foreach ($item in Get-ChildItem $From -Force) {
        if ($item.PSIsContainer -and ($excludedDirs -contains $item.Name -or $item.Name -like 'simulation_results*')) { continue }
        if (-not $item.PSIsContainer -and ($excludedPatterns | Where-Object { $item.Name -like $_ })) { continue }
        $dest = Join-Path $To $item.Name
        if ($item.PSIsContainer) { Copy-FilteredTree $item.FullName $dest }
        else { Copy-Item $item.FullName $dest -Force }
    }
}
Copy-FilteredTree $source $target
if (-not (Test-Path (Join-Path $target 'LICENSE')) -and (Split-Path $licensePath -Leaf) -ne 'LICENSE') {
    Copy-Item $licensePath (Join-Path $target 'UPSTREAM_LICENSE_NOTICE.txt') -Force
}
$commit = 'unknown'
$remote = 'unknown'
try { $commit = (git -C $source rev-parse HEAD 2>$null).Trim() } catch {}
try { $remote = (git -C $source remote get-url origin 2>$null).Trim() } catch {}
@"
source_path=$source
source_remote=$remote
source_commit=$commit
imported_at=$(Get-Date -Format o)
license_source=$(Split-Path $licensePath -Leaf)
"@ | Set-Content -Encoding UTF8 (Join-Path $target 'SOURCE_MANIFEST.txt')
Remove-Item (Join-Path $target 'UPSTREAM_SOURCE_PENDING.txt') -ErrorAction SilentlyContinue
Write-Host "Offgridders diimpor ke: $target" -ForegroundColor Green
Write-Host "Commit: $commit"
Write-Host "Remote: $remote"
Write-Host 'Periksa LICENSE dan README upstream sebelum distribusi ulang.'
