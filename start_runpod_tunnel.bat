@echo off
REM SSH tunnel to RunPod for Ollama access
REM This forwards local port 11434 to the Ollama server on RunPod

set RUNPOD_IP=149.36.1.59
set RUNPOD_SSH_PORT=14404
set SSH_KEY=%USERPROFILE%\.ssh\id_ed25519
set LOCAL_PORT=11434
set REMOTE_PORT=11434

echo Starting SSH tunnel to RunPod Ollama server...
echo Local: localhost:%LOCAL_PORT% -^> Remote: %RUNPOD_IP%:%REMOTE_PORT%
echo.
echo Keep this terminal open while using Lloyd.
echo Press Ctrl+C to stop the tunnel.
echo.

REM First, ensure Ollama is running on the RunPod (RTX 5090 GPU)
echo Starting Ollama on RunPod (GPU mode)...
ssh -o StrictHostKeyChecking=no root@%RUNPOD_IP% -p %RUNPOD_SSH_PORT% -i %SSH_KEY% "export OLLAMA_HOST=0.0.0.0:11434 && pkill ollama 2>/dev/null; nohup ollama serve > /var/log/ollama.log 2>&1 &"

timeout /t 3 /nobreak >nul
echo Ollama started (qwen2.5:32b on RTX 5090). Establishing SSH tunnel...
echo.

REM Start the SSH tunnel (foreground so user can see it's running)
ssh -N -L %LOCAL_PORT%:localhost:%REMOTE_PORT% -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -o ServerAliveCountMax=3 root@%RUNPOD_IP% -p %RUNPOD_SSH_PORT% -i %SSH_KEY%
