param(
  [string]$ComposeFile = "docker-compose.review.yml",
  [switch]$ResetPasswords
)
$ErrorActionPreference = "Stop"
$arg = if ($ResetPasswords) { "--reset-passwords" } else { "" }
Write-Host "Repairing administrator role, country, facility, department and function matrices..."
docker compose -f $ComposeFile exec app python scripts/repair_admin_access.py $arg
if ($LASTEXITCODE -ne 0) { throw "Administrator access repair failed." }
Write-Host "Administrator access repair completed. Sign out and sign in again so the refreshed access token contains the repaired matrix."
