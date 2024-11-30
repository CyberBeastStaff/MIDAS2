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
echo Starting the application...
echo Log messages will appear below:
echo ----------------------------------------
python app.py

pause
