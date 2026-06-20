' scripts/windows/sync-hidden.vbs
' ─────────────────────────────────────────────────────────────
' sync.ps1 을 "창 없이" 실행하는 래퍼. Windows 작업 스케줄러가 powershell.exe 를
' 직접 띄우면 -WindowStyle Hidden 을 줘도 conhost 가 먼저 떠서 검은 cmd 창이
' 깜빡인다. 이 .vbs 는 wscript.exe(콘솔 없는 GUI 호스트)로 실행되고, PowerShell 을
' 창 스타일 0(SW_HIDE)으로 생성하므로 창이 아예 뜨지 않는다.
'
' register-task.ps1 이 작업 동작(action)을  wscript.exe "<...>\sync-hidden.vbs"  로
' 등록한다. 경로는 이 파일 위치에서 스스로 유도하므로 인자가 필요 없다.

Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' 이 .vbs 는 <repo>\scripts\windows\ 에 있다 → repo = 2단계 상위
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
repo      = fso.GetParentFolderName(fso.GetParentFolderName(scriptDir))
ps1       = repo & "\scripts\sync.ps1"

cmd = "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File """ & ps1 & """"

' 두 번째 인자 0 = 숨김 창(SW_HIDE), 세 번째 False = 종료 대기 안 함
sh.Run cmd, 0, False
