from src.plugins.base import BasePlugin

class HelloWorldPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "hello_world"

    @property
    def description(self) -> str:
        return "A simple example plugin."

    @BasePlugin.tool(name="hello", description="Says hello to the world.")
    async def say_hello(self, name: str = "World") -> str:
        """
        Says hello to the given name.
        """
        return f"Hello, {name}! The plugin system is working."
