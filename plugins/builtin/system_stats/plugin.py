from typing import List
from src.plugins.base import BasePlugin
from src.tools.base import BaseTool
from src.tools.system_stats import SystemStatsTool

class SystemStatsPlugin(BasePlugin):
    def get_tools(self) -> List[BaseTool]:
        return [SystemStatsTool()]
