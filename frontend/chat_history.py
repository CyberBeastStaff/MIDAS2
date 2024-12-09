import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Union

class ChatHistory:
    def __init__(self, history_dir: str = "chat_history"):
        self.history_dir = history_dir
        os.makedirs(history_dir, exist_ok=True)
        
    def _migrate_chat_data(self, data: Union[List, Dict]) -> Dict:
        """Migrate old chat data format to new format"""
        if isinstance(data, list):
            # Old format: just a list of messages
            return {
                "messages": data,
                "title": data[0][0][:50] + "..." if data and len(data[0]) > 0 else "New Chat",
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
            }
        return data
        
    def save_chat(self, messages: List[List[str]], title: Optional[str] = None) -> str:
        """Save a chat session to a file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate title from first message if not provided
        if not title and messages and len(messages) > 0:
            first_msg = messages[0][0] if isinstance(messages[0], list) else messages[0]
            title = first_msg[:50] + "..." if len(first_msg) > 50 else first_msg
        
        chat_data = {
            "id": timestamp,
            "title": title or "New Chat",
            "timestamp": timestamp,
            "messages": messages
        }
        
        filename = f"{timestamp}.json"
        filepath = os.path.join(self.history_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(chat_data, f, ensure_ascii=False, indent=2)
            
        return timestamp
    
    def load_chat(self, chat_id: str) -> Dict:
        """Load a specific chat session"""
        filepath = os.path.join(self.history_dir, f"{chat_id}.json")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data = self._migrate_chat_data(data)
                return {
                    "id": chat_id,
                    "title": data.get("title", "Untitled Chat"),
                    "timestamp": data.get("timestamp", chat_id),
                    "messages": data.get("messages", [])
                }
        except FileNotFoundError:
            return {"id": None, "title": "Chat not found", "timestamp": None, "messages": []}
        except json.JSONDecodeError:
            return {"id": None, "title": "Invalid chat data", "timestamp": None, "messages": []}
    
    def list_chats(self) -> List[Dict]:
        """List all chat sessions"""
        chats = []
        for filename in sorted(os.listdir(self.history_dir), reverse=True):
            if filename.endswith('.json'):
                chat_id = filename[:-5]  # Remove .json extension
                filepath = os.path.join(self.history_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        data = self._migrate_chat_data(data)
                        chats.append({
                            "id": chat_id,
                            "title": data.get("title", "Untitled Chat"),
                            "timestamp": data.get("timestamp", chat_id)
                        })
                except (json.JSONDecodeError, KeyError, FileNotFoundError):
                    continue
        return chats
    
    def delete_chat(self, chat_id: str) -> bool:
        """Delete a chat session"""
        filepath = os.path.join(self.history_dir, f"{chat_id}.json")
        try:
            os.remove(filepath)
            return True
        except FileNotFoundError:
            return False
