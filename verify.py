
import asyncio
import os
import sys

# Add src to path
sys.path.append(os.getcwd())

from src.core.llm_factory import LLMFactory
from src.plugins.plugin_loader import PluginLoader
from src.channels.channel_manager import ChannelManager

async def test_browser():
    print("\n🌐 Testing Browser Plugin...")
    loader = PluginLoader()
    await loader.load_all()
    
    browser_plugin = loader.get_plugin("browser")
    if not browser_plugin:
        print("❌ Browser plugin not found!")
        return

    print("✅ Browser Plugin Loaded")
    
    # Get tools
    tools = browser_plugin.get_tools()
    open_tool = next((t for t in tools if t.name == "browser_open"), None)
    
    if open_tool:
        print("✅ Found 'browser_open' tool")
        try:
            print("   Running: browser_open('https://example.com')...")
            result = await open_tool.execute(url="https://example.com")
            print(f"   Result: {result[:100]}...") 
            print("✅ Browser navigation successful!")
        except Exception as e:
            print(f"❌ Browser navigation failed: {e}")
    else:
        print("❌ 'browser_open' tool missing")

    await loader.unload_all()

async def test_channels():
    print("\n📡 Testing Channel Manager...")
    cm = ChannelManager()
    
    # Mock config
    config = {
        "channels": {
            "telegram": {"enabled": True, "bot_token": "TEST_TOKEN"},
            "discord": {"enabled": False}
        }
    }
    
    # We expect verify to fail on start because token is fake, but creation should work
    try:
        count = cm.setup_from_config(config)
        print(f"✅ Configured {count} channels from config")
        
        tg = cm.get_channel("telegram")
        if tg:
             print("✅ Telegram channel created successfully")
        else:
             print("❌ Failed to create Telegram channel")
             
    except Exception as e:
        print(f"❌ Channel setup failed: {e}")

async def main():
    print("🚀 ElyssiaAgent Feature Verification 🚀")
    await test_browser()
    await test_channels()
    print("\n✨ Verification Complete")

if __name__ == "__main__":
    asyncio.run(main())
