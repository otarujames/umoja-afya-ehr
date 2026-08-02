$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force -Path secrets | Out-Null
function New-RandomSecret([string]$Path,[int]$Bytes){
  if(-not (Test-Path $Path) -or (Get-Item $Path).Length -eq 0){
    $buffer=New-Object byte[] $Bytes
    [Security.Cryptography.RandomNumberGenerator]::Fill($buffer)
    ([Convert]::ToHexString($buffer)).ToLowerInvariant() | Set-Content -NoNewline -Encoding ascii $Path
    Write-Host "Created $Path"
  }
}
New-RandomSecret "secrets/review_postgres_password" 32
New-RandomSecret "secrets/review_security_secret" 64
python scripts/generate_preloaded_users.py --output secrets/review_preloaded_users.json
Write-Host "Review secrets and the preloaded user roster are ready."
Write-Host "Temporary credentials: secrets/review_preloaded_users.json"
Write-Host "All accounts require a password change and MFA enrollment."
