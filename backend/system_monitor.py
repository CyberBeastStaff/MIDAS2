import psutil
import GPUtil
import torch

def get_system_info():
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    if hasattr(psutil, "sensors_temperatures"):
        temps = psutil.sensors_temperatures()
    else:
        temps = {}
    
    # GPU Information
    if torch.cuda.is_available():
        gpu_info = ""
        try:
            gpus = GPUtil.getGPUs()
            for gpu in gpus:
                gpu_info += f"\nGPU {gpu.id}: {gpu.name}"
                gpu_info += f"\n - Memory Used: {gpu.memoryUsed}MB/{gpu.memoryTotal}MB"
                gpu_info += f"\n - GPU Load: {gpu.load*100}%"
        except:
            gpu_info = "\nGPU information unavailable"
    else:
        gpu_info = "\nNo GPU available"
    
    return f"""
    CPU Usage: {cpu_percent}%
    RAM Usage: {memory.percent}%
    Used RAM: {memory.used / (1024**3):.1f}GB
    Total RAM: {memory.total / (1024**3):.1f}GB
    {gpu_info}
    """
