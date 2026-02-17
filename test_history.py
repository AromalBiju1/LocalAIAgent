
import requests
import json
import sys

BASE_URL = "http://localhost:8000/api"

def test_history():
    print("📜 Testing Chat History Persistence...")
    
    # 1. Create Conversation
    print("1. Creating conversation...")
    res = requests.post(f"{BASE_URL}/memory/conversations", json={"title": "Test Chat"})
    if res.status_code != 200:
        print(f"❌ Failed to create conversation: {res.text}")
        return
    conv_id = res.json()["id"]
    print(f"✅ Conversation created: {conv_id}")

    # 2. Send Message (Stream)
    print("2. Sending message...")
    payload = {
        "messages": [{"role": "user", "content": "Hello, remember this!"}],
        "stream": True,
        "conversation_id": conv_id
    }
    
    # We don't need to consume the stream fully, just trigger it
    try:
        with requests.post(f"{BASE_URL}/chat/stream", json=payload, stream=True) as r:
            for line in r.iter_lines():
                pass # Consume stream
        print("✅ Message sent and stream consumed")
    except Exception as e:
        print(f"❌ Failed to send message: {e}")
        return

    # 3. Check History
    print("3. Checking history...")
    res = requests.get(f"{BASE_URL}/memory/conversations/{conv_id}")
    if res.status_code != 200:
        print(f"❌ Failed to get history: {res.text}")
        return
    
    data = res.json()
    messages = data.get("messages", [])
    print(f"   Found {len(messages)} messages.")
    
    user_msg = next((m for m in messages if m["role"] == "user"), None)
    asst_msg = next((m for m in messages if m["role"] == "assistant"), None)
    
    if user_msg and "remember this" in user_msg["content"]:
        print("✅ User message persisted")
    else:
        print("❌ User message NOT found")

    if asst_msg:
        print("✅ Assistant message persisted")
    else:
        print("❌ Assistant message NOT found (might be empty if model failed)")

if __name__ == "__main__":
    test_history()
