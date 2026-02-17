import sys
import os

# Ensure src is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from src.memory.memory import ConversationMemory
    print("Imported ConversationMemory")
    memory = ConversationMemory(db_path="test_db.db")
    print("Initialized ConversationMemory")
    print(memory.stats())
except Exception as e:
    print(f"ERROR: {e}")
