import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import logging

class ChatManager:
    def __init__(self, history_dir: str = "chat_history"):
        self.history_dir = history_dir
        os.makedirs(history_dir, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def _get_chat_path(self, chat_id: str) -> str:
        return os.path.join(self.history_dir, f"{chat_id}.json")

    def create_chat(self, title: str = "New Chat") -> str:
        """Create a new chat history"""
        chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        chat_data = {
            "id": chat_id,
            "title": title,
            "created_at": datetime.now().isoformat(),
            "messages": []
        }
        
        try:
            with open(self._get_chat_path(chat_id), 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, ensure_ascii=False, indent=2)
            return chat_id
        except Exception as e:
            self.logger.error(f"Error creating chat: {e}")
            raise

    def add_message(self, chat_id: str, role: str, content: str) -> bool:
        """Add a message to an existing chat"""
        try:
            chat_data = self.get_chat(chat_id)
            if not chat_data:
                return False
            
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            chat_data["messages"].append(message)
            
            with open(self._get_chat_path(chat_id), 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Error adding message to chat {chat_id}: {e}")
            return False

    def get_chat(self, chat_id: str) -> Optional[Dict]:
        """Get a specific chat history"""
        try:
            chat_path = self._get_chat_path(chat_id)
            if not os.path.exists(chat_path):
                return None
            
            with open(chat_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error retrieving chat {chat_id}: {e}")
            return None

    def list_chats(self) -> List[Dict]:
        """List all available chats"""
        chats = []
        try:
            for filename in os.listdir(self.history_dir):
                if filename.endswith('.json'):
                    chat_id = filename[:-5]  # Remove .json extension
                    chat_data = self.get_chat(chat_id)
                    if chat_data:
                        chats.append({
                            "id": chat_data["id"],
                            "title": chat_data["title"],
                            "created_at": chat_data["created_at"]
                        })
            return sorted(chats, key=lambda x: x["created_at"], reverse=True)
        except Exception as e:
            self.logger.error(f"Error listing chats: {e}")
            return []

    def delete_chat(self, chat_id: str) -> bool:
        """Delete a specific chat history"""
        try:
            chat_path = self._get_chat_path(chat_id)
            if os.path.exists(chat_path):
                os.remove(chat_path)
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error deleting chat {chat_id}: {e}")
            return False

    def update_chat_title(self, chat_id: str, new_title: str) -> bool:
        """Update the title of a chat"""
        self.logger.info(f"Attempting to update chat {chat_id} title to: {new_title}")
        try:
            chat_data = self.get_chat(chat_id)
            if not chat_data:
                self.logger.error(f"Chat {chat_id} not found")
                return False
            
            old_title = chat_data["title"]
            chat_data["title"] = new_title
            chat_path = self._get_chat_path(chat_id)
            
            self.logger.info(f"Writing updated chat data to {chat_path}")
            self.logger.info(f"Title change: {old_title} -> {new_title}")
            
            with open(chat_path, 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Successfully updated chat {chat_id} title")
            return True
        except Exception as e:
            self.logger.error(f"Error updating chat title {chat_id}: {e}")
            return False
