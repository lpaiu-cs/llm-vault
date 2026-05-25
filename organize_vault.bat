@echo off
REM ─────────────────────────────────────────────────────────────
REM organize_vault.bat — Windows용 1회성 정리 스크립트
REM
REM 사용법:
REM   1. 이 파일을 E:\vv\llm-vault\에 복사
REM   2. 더블클릭 또는 cmd에서 실행: organize_vault.bat
REM   3. 완료 후 이 .bat 파일 삭제
REM ─────────────────────────────────────────────────────────────

setlocal enabledelayedexpansion
echo.
echo === Karpathy LLM Framework Vault - 폴더 정리 ===
echo.

REM 폴더 생성
for %%D in (00_System 10_MOC 20_Concepts 90_Engine .obsidian) do (
    if not exist "%%D" mkdir "%%D"
    echo   [+] %%D\
)

REM Obsidian 설정 이동 (이름 변경)
if exist "obsidian-app.json" (
    move /Y "obsidian-app.json" ".obsidian\app.json" >nul
    echo   [+] .obsidian\app.json
)
if exist "obsidian-graph.json" (
    move /Y "obsidian-graph.json" ".obsidian\graph.json" >nul
    echo   [+] .obsidian\graph.json
)

REM 시뮬레이션 산출물 삭제
if exist "Test Violation Note.md" (
    del /Q "Test Violation Note.md"
    echo   [x] Test Violation Note.md 삭제
)

REM System 노트
if exist "Ontology Specification.md" (
    move /Y "Ontology Specification.md" "00_System\" >nul
    echo   [+] 00_System\Ontology Specification.md
)

REM MOC 노트
for %%F in (
    "Karpathy LLM Framework MOC.md"
    "Philosophy MOC.md"
    "Architecture MOC.md"
    "Implementation MOC.md"
) do (
    if exist %%F (
        move /Y %%F "10_MOC\" >nul
        echo   [+] 10_MOC\%%~F
    )
)

REM Engine 파일
for %%F in (indexer.py retriever.py mcp_server.py mock_ollama.py) do (
    if exist %%F (
        move /Y %%F "90_Engine\" >nul
        echo   [+] 90_Engine\%%F
    )
)

REM 나머지 .md 파일을 모두 20_Concepts로 (단 README/SETUP/LICENSE 제외)
for %%F in (*.md) do (
    if /I not "%%F"=="README.md" if /I not "%%F"=="SETUP.md" (
        move /Y "%%F" "20_Concepts\" >nul 2>&1
        echo   [+] 20_Concepts\%%F
    )
)

echo.
echo === 최종 구조 ===
echo.
dir /B
echo.
echo [완료] 이제 Obsidian에서 'Open folder as vault'로 E:\vv\llm-vault 폴더 선택하세요.
echo        이 organize_vault.bat 파일은 안전하게 삭제하셔도 됩니다.
echo.
pause
