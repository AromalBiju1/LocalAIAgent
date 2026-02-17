import psutil
import platform
import time
from datetime import datetime
from typing import Dict, Any

from src.tools.base import BaseTool

class SystemStatsTool(BaseTool):
    """
    Tool to retrieve current system statistics (CPU, Memory, uptime).
    Useful for the agent to have 'self-awareness' of its host.
    """
    
    @property
    def name(self) -> str:
        return "system_stats"

    @property
    def description(self) -> str:
        return "Get current system status including CPU usage, memory usage, platform info, and time."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, **kwargs) -> str:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        uptime_seconds = time.time() - psutil.boot_time()
        
        # Format uptime
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{int(hours)}h {int(minutes)}m"

        return (
            f"SYSTEM STATUS REPORT:\n"
            f"---------------------\n"
            f"TIME      : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"OS        : {platform.system()} {platform.release()}\n"
            f"CPU USAGE : {cpu_percent}%\n"
            f"RAM USAGE : {mem.percent}% ({round(mem.used / (1024**3), 2)}GB / {round(mem.total / (1024**3), 2)}GB)\n"
            f"UPTIME    : {uptime_str}\n"
            f"STATUS    : ONLINE\n"
        )
