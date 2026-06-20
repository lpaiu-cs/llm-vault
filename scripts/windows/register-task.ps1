#!/usr/bin/env pwsh
# scripts/windows/register-task.ps1
# ─────────────────────────────────────────────────────────────
# Windows 작업 스케줄러에 llm-vault 자동 동기화를 등록한다.
# 로그온 시 + 15분마다 scripts\sync.ps1 을 현재 사용자 세션에서 실행한다
# (자격증명 저장 불필요 — 사용자가 로그온해 있을 때 동작, launchd gui agent와 동일 개념).
#
# 실행(관리자 권한 불필요):
#   powershell -ExecutionPolicy Bypass -File scripts\windows\register-task.ps1
# 확인:
#   Get-ScheduledTask -TaskName 'llm-vault-sync'
#   Get-ScheduledTaskInfo -TaskName 'llm-vault-sync'   # LastRunResult 등
# 제거:
#   Unregister-ScheduledTask -TaskName 'llm-vault-sync' -Confirm:$false
#
# 자격증명: git push가 비대화식으로 되도록 Git Credential Manager(기본) 또는
#           PAT/SSH 키가 설정돼 있어야 한다.
$ErrorActionPreference = 'Stop'

$taskName = 'llm-vault-sync'

# 저장소 루트 = 이 스크립트(scripts\windows\) 의 2단계 상위
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$syncScript = Join-Path $repo 'scripts\sync.ps1'
if (-not (Test-Path $syncScript)) {
    Write-Error "sync.ps1 을 찾을 수 없습니다: $syncScript"
    exit 1
}

# 창 깜빡임 방지: powershell.exe 를 직접 띄우면 conhost 가 먼저 떠서 검은 창이
# 번쩍인다. wscript.exe 로 sync-hidden.vbs 를 실행하면 창이 아예 안 뜬다.
$vbs = Join-Path $PSScriptRoot 'sync-hidden.vbs'
if (-not (Test-Path $vbs)) {
    Write-Error "sync-hidden.vbs 를 찾을 수 없습니다: $vbs"
    exit 1
}
$action = New-ScheduledTaskAction -Execute 'wscript.exe' `
    -Argument "`"$vbs`"" `
    -WorkingDirectory $repo

# 트리거: 로그온 시 + 15분마다(아주 긴 기간 동안 반복)
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn
$triggerRepeat = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 15) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $taskName `
    -Action $action -Trigger @($triggerLogon, $triggerRepeat) -Settings $settings `
    -Description 'llm-vault git auto-sync (every 15 min + at logon); pushes to origin only' `
    -Force | Out-Null

Write-Host "[OK] registered scheduled task '$taskName'"
Write-Host "     repo : $repo"
Write-Host "     run  : $psExe -File $syncScript"
Write-Host "     check : Get-ScheduledTaskInfo -TaskName '$taskName'"
Write-Host "     remove: Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false"
