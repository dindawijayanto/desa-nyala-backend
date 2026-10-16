$ErrorActionPreference = 'Stop'
$engine = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\engine\offgridders'))
$checks = @(
    @{Name='Offgridders.py'; Path=(Join-Path $engine 'Offgridders.py')},
    @{Name='src folder'; Path=(Join-Path $engine 'src')},
    @{Name='Source manifest'; Path=(Join-Path $engine 'SOURCE_MANIFEST.txt')}
)
$failed = $false
foreach ($check in $checks) {
    $ok = Test-Path $check.Path
    Write-Host (('{0,-32} {1}' -f $check.Name, $(if ($ok) {'OK'} else {'MISSING'})))
    if (-not $ok) { $failed = $true }
}
$licenseExists = (Test-Path (Join-Path $engine 'LICENSE')) -or (Test-Path (Join-Path $engine 'LICENSE.txt')) -or (Test-Path (Join-Path $engine 'COPYING')) -or (Test-Path (Join-Path $engine 'UPSTREAM_LICENSE_NOTICE.txt'))
Write-Host ('{0,-32} {1}' -f 'Upstream license', $(if ($licenseExists) {'OK'} else {'MISSING'}))
if (-not $licenseExists) { $failed = $true }
if ($failed) { throw 'Engine belum lengkap. Jalankan scripts/import_offgridders.ps1 dari folder backend.' }
Write-Host 'Source engine tersedia. Dependensi solver tetap perlu dicek di Python environment Offgridders.' -ForegroundColor Green
