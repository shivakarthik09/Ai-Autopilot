@echo off
SET "BASE_URL=http://localhost:8000"

ECHO.
ECHO ==============================
ECHO   Running Example A: Direct Execution
ECHO ==============================
ECHO.

SET "REQUEST_A=Diagnose why Windows Server 2019 VM cpu01 hits 95%+ CPU, generate a PowerShell script to collect perfmon logs, and draft an email to management summarising findings."

REM Execute Example A and extract task_id
powershell -Command "$body = @{ request = '%REQUEST_A%'; require_approval = $false } | ConvertTo-Json -Compress; $response = Invoke-RestMethod -Uri '%BASE_URL%/api/v1/execute' -Method Post -Body $body -ContentType 'application/json'; $response | ConvertTo-Json; $response.task_id.Trim() | Out-File -FilePath 'task_id.txt' -Encoding ASCII"

SET /P TASK_ID_A=<task_id.txt
DEL task_id.txt

ECHO.
ECHO Task ID: %TASK_ID_A%
ECHO Polling status for Example A...

:POLL_A
powershell -Command "$response = Invoke-RestMethod -Uri '%BASE_URL%/api/v1/tasks/%TASK_ID_A%' -Method Get; $status = $response.status; Write-Host $status; if ($status -eq 'completed' -or $status -eq 'failed') { $response | ConvertTo-Json; exit 0 } else { exit 1 }"
IF %ERRORLEVEL% NEQ 0 (
    ECHO Task not completed yet. Waiting...
    TIMEOUT /T 5 /NOBREAK >NUL
    GOTO POLL_A
) ELSE (
    ECHO Task %TASK_ID_A% finished.
    ECHO.
)


ECHO.
ECHO ==============================
ECHO   Running Example B: Approval Flow
ECHO ==============================
ECHO.

SET "REQUEST_B=Create Azure CLI commands to lock RDP (3389) on my three production VMs to 10.0.0.0/24 and pause for approval before outputting the commands."

REM Execute Example B and extract task_id
powershell -Command "$body = @{ request = '%REQUEST_B%'; require_approval = $true } | ConvertTo-Json -Compress; $response = Invoke-RestMethod -Uri '%BASE_URL%/api/v1/execute' -Method Post -Body $body -ContentType 'application/json'; $response | ConvertTo-Json; $response.task_id.Trim() | Out-File -FilePath 'task_id.txt' -Encoding ASCII"

SET /P PLAN_ID=<task_id.txt
DEL task_id.txt

ECHO.
ECHO Plan ID: %PLAN_ID%
ECHO Polling status for Example B...

:POLL_B_WAITING
powershell -Command "$response = Invoke-RestMethod -Uri '%BASE_URL%/api/v1/tasks/%PLAN_ID%' -Method Get; $status = $response.status; Write-Host $status; if ($status -eq 'waiting_approval') { $response | ConvertTo-Json; exit 0 } else { exit 1 }"
IF %ERRORLEVEL% NEQ 0 (
    ECHO Task not waiting for approval yet. Waiting...
    TIMEOUT /T 5 /NOBREAK >NUL
    GOTO POLL_B_WAITING
) ELSE (
    ECHO Task %PLAN_ID% is waiting for approval.
    ECHO.
)

ECHO.
ECHO Approving the plan...
powershell -Command "Invoke-RestMethod -Uri '%BASE_URL%/api/v1/plans/%PLAN_ID%/approve' -Method Post"

ECHO.
ECHO Waiting for plan execution...
TIMEOUT /T 5 /NOBREAK >NUL

ECHO.
ECHO Polling status for Example B after approval...

:POLL_B_COMPLETED
powershell -Command "$response = Invoke-RestMethod -Uri '%BASE_URL%/api/v1/tasks/%PLAN_ID%' -Method Get; $status = $response.status; Write-Host $status; if ($status -eq 'completed' -or $status -eq 'failed') { $response | ConvertTo-Json; exit 0 } else { exit 1 }"
IF %ERRORLEVEL% NEQ 0 (
    ECHO Task not completed yet. Waiting...
    TIMEOUT /T 5 /NOBREAK >NUL
    GOTO POLL_B_COMPLETED
) ELSE (
    ECHO Task %PLAN_ID% finished.
    ECHO.
)

ECHO.
ECHO All examples finished. 