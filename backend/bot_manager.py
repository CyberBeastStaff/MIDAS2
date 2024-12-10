import os
import json
from typing import Dict, List, Optional
from datetime import datetime

class Bot:
    def __init__(self, id: str, name: str, system_prompt: str, base_model: str, parameters: Dict):
        self.id = id
        self.name = name
        self.system_prompt = system_prompt
        self.base_model = base_model
        self.parameters = parameters
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "system_prompt": self.system_prompt,
            "base_model": self.base_model,
            "parameters": self.parameters,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

class BotManager:
    def __init__(self, bots_dir: str = "bots"):
        self.bots_dir = bots_dir
        self.bots: Dict[str, Bot] = {}
        self._ensure_bots_directory()
        self._load_bots()
        self._ensure_default_bot()

    def _ensure_bots_directory(self):
        """Ensure the bots directory exists"""
        os.makedirs(self.bots_dir, exist_ok=True)

    def _load_bots(self):
        """Load all bots from the bots directory"""
        if not os.path.exists(self.bots_dir):
            return

        for filename in os.listdir(self.bots_dir):
            if filename.endswith('.json'):
                bot_path = os.path.join(self.bots_dir, filename)
                with open(bot_path, 'r') as f:
                    bot_data = json.load(f)
                    bot = Bot(
                        id=bot_data['id'],
                        name=bot_data['name'],
                        system_prompt=bot_data['system_prompt'],
                        base_model=bot_data['base_model'],
                        parameters=bot_data['parameters']
                    )
                    self.bots[bot.id] = bot

    def _ensure_default_bot(self):
        """Create default MIDAS40 bot if it doesn't exist"""
        if 'MIDAS40' not in self.bots:
            default_bot = Bot(
                id='MIDAS40',
                name='MIDAS40',
                system_prompt=(
                    "You are MIDAS40, an advanced AI assistant created by Cyber Beast Tech. "
                    "You are helpful, knowledgeable, and precise in your responses. "
                    "You aim to provide accurate information and assist users with their tasks "
                    "while maintaining a professional and friendly demeanor."
                ),
                base_model='llama2-70b',
                parameters={
                    'temperature': 0.7,
                    'max_new_tokens': 1000,
                    'top_p': 0.95,
                    'top_k': 50,
                    'repetition_penalty': 1.2
                }
            )
            self.create_bot(default_bot)

    def _save_bot(self, bot: Bot):
        """Save a bot to file"""
        bot_path = os.path.join(self.bots_dir, f"{bot.id}.json")
        with open(bot_path, 'w') as f:
            json.dump(bot.to_dict(), f, indent=4)

    def get_bot(self, bot_id: str) -> Optional[Bot]:
        """Get a bot by ID"""
        return self.bots.get(bot_id)

    def list_bots(self) -> List[Dict]:
        """List all bots"""
        return [bot.to_dict() for bot in self.bots.values()]

    def create_bot(self, bot: Bot) -> Bot:
        """Create a new bot"""
        if bot.id in self.bots:
            raise ValueError(f"Bot with ID {bot.id} already exists")
        
        self.bots[bot.id] = bot
        self._save_bot(bot)
        return bot

    def update_bot(self, bot_id: str, **kwargs) -> Bot:
        """Update a bot's properties"""
        if bot_id not in self.bots:
            raise ValueError(f"Bot with ID {bot_id} does not exist")
        
        bot = self.bots[bot_id]
        for key, value in kwargs.items():
            if hasattr(bot, key):
                setattr(bot, key, value)
        
        bot.updated_at = datetime.now().isoformat()
        self._save_bot(bot)
        return bot

    def delete_bot(self, bot_id: str):
        """Delete a bot"""
        if bot_id == 'MIDAS40':
            raise ValueError("Cannot delete the default bot")
        
        if bot_id not in self.bots:
            raise ValueError(f"Bot with ID {bot_id} does not exist")
        
        bot_path = os.path.join(self.bots_dir, f"{bot_id}.json")
        if os.path.exists(bot_path):
            os.remove(bot_path)
        
        del self.bots[bot_id]
