@echo off
echo Starting Local LLM Platform...
echo.
echo Setting up Python environment...
set PYTHONUNBUFFERED=1
set GRADIO_DEBUG=1

echo.
echo Checking GPU availability...
python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'GPU Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"}')"

echo.
echo Starting the Flask backend server...
start cmd /k "title MIDAS Backend && python backend/server.py"

echo Waiting for backend to start...
timeout /t 2 /nobreak > nul

echo.
echo Starting the Gradio frontend...
echo Log messages will appear below:
echo ----------------------------------------
start cmd /k "title MIDAS Frontend && python frontend/interface.py"

echo.
echo MIDAS 2.0 is starting up...
echo - Backend server: http://127.0.0.1:7860
echo - Frontend interface: http://127.0.0.1:7861
echo.
echo Press any key to shut down all servers...
pause

echo.
echo Shutting down servers...
taskkill /FI "WindowTitle eq MIDAS Backend" /T /F > nul 2>&1
taskkill /FI "WindowTitle eq MIDAS Frontend" /T /F > nul 2>&1
echo Done.
