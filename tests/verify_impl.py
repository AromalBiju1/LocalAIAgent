import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.memory.memory import ConversationMemory
from src.tools.system_stats import SystemStatsTool

async def test_memory():
    print("Testing ConversationMemory...")
    mem = ConversationMemory(db_path=":memory:", memory_window=5)
    
    # Create conversation
    cid = mem.new_conversation("Test Chat")
    print(f"Created conversation: {cid}")
    
    # Add messages
    for i in range(10):
        mem.add_message("user", f"Message {i}", conversation_id=cid)
        mem.add_message("assistant", f"Response {i}", conversation_id=cid)
        
    # Test get_context_window (default limit 20, should get all 20)
    ctx = await mem.get_context_window(cid)
    print(f"Context window length (limit 20): {len(ctx)}")
    assert len(ctx) == 20
    
    # Test get_context_window (limit 5)
    ctx_small = await mem.get_context_window(cid, limit=5)
    print(f"Context window length (limit 5): {len(ctx_small)}")
    assert len(ctx_small) == 5
    assert ctx_small[-1]['content'] == "Response 9" # Last message
    
    # Test summary injection
    mem.update_summary(cid, "User and Assistant counted to 9.")
    ctx_summary = await mem.get_context_window(cid, limit=5)
    print(f"Context with summary length: {len(ctx_summary)}")
    # Should be 5 messages + 1 summary = 6
    assert len(ctx_summary) == 6
    assert ctx_summary[0]['role'] == 'system'
    assert "counted to 9" in ctx_summary[0]['content']
    
    print("Memory tests passed!")

async def test_tool():
    print("\nTesting SystemStatsTool...")
    tool = SystemStatsTool()
    res = await tool.execute()
    print("Tool Output:")
    print(res)
    assert "CPU USAGE" in res
    print("Tool tests passed!")

if __name__ == "__main__":
    asyncio.run(test_memory())
    asyncio.run(test_tool())
