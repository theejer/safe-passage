[CmdletBinding()]
param(
  [ValidateSet("up", "down", "logs", "status", "rebuild")]
  [string]$Action = "up"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
$ComposeFile = Join-Path $RepoRoot "docker-compose.yml"
$EnvFile = Join-Path $RepoRoot "backend/.env"
$EnvExample = Join-Path $RepoRoot "backend/.env.example"

if (-not (Test-Path $ComposeFile)) {
  throw "docker-compose.yml was not found at $ComposeFile"
}

if (-not (Test-Path $EnvFile)) {
  if (Test-Path $EnvExample) {
    Copy-Item $EnvExample $EnvFile
    Write-Host "Created backend/.env from backend/.env.example. Update secrets before production use."
  }
  else {
    throw "Missing backend/.env and backend/.env.example."
  }
}

Push-Location $RepoRoot
try {
  switch ($Action) {
    "up" {
      docker compose up --build backend
    }
    "down" {
      docker compose down
    }
    "logs" {
      docker compose logs -f backend
    }
    "status" {
      docker compose ps
    }
    "rebuild" {
      docker compose build --no-cache backend
    }
  }
}
finally {
  Pop-Location
}