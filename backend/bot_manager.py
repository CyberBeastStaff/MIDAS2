import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from .model_inference import ModelInference, ModelConfig

logger = logging.getLogger(__name__)

class Bot:
    def __init__(self, id: str, name: str, system_prompt: str, base_model: str, parameters: Dict):
        self.id = id
        self.name = name
        self.system_prompt = system_prompt
        self.base_model = base_model
        self.parameters = parameters
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self._model_inference = ModelInference()
        self._model_loaded = False

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

    def load_model(self, model_path: str) -> bool:
        """Load the model for inference"""
        try:
            config = ModelConfig(
                model_path=model_path,
                n_ctx=2048,
                n_threads=None,  # Use all available threads
                n_batch=512
            )
            self._model_loaded = self._model_inference.load_model(model_path, config)
            return self._model_loaded
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False

    def unload_model(self) -> None:
        """Unload the model"""
        if self._model_loaded:
            self._model_inference.unload_model()
            self._model_loaded = False

    def generate_response(self, messages: List[Dict], parameters: Dict = None):
        """Generate a response using the bot's configuration and given parameters"""
        try:
            # Prepare the conversation history
            conversation = []
            
            # Add system prompt as the first message
            conversation.append({
                'role': 'system',
                'content': self.system_prompt
            })
            
            # Add the message history
            conversation.extend(messages)
            
            # Check if model is loaded
            if not self._model_loaded:
                yield {
                    'token': (
                        f"Error: Model {self.base_model} is not loaded. "
                        "Please ensure the model is downloaded and loaded before generating responses."
                    )
                }
                return
            
            # Use provided parameters or defaults
            params = {
                'temperature': parameters.get('temperature', self.parameters.get('temperature', 0.7)),
                'max_tokens': parameters.get('max_new_tokens', self.parameters.get('max_new_tokens', 1000)),
                'top_p': parameters.get('top_p', self.parameters.get('top_p', 0.95)),
                'top_k': parameters.get('top_k', self.parameters.get('top_k', 40)),
                'repeat_penalty': parameters.get('repetition_penalty', self.parameters.get('repetition_penalty', 1.1))
            }
            
            print("[DEBUG] Bot generating response with params:", params)
            print("[DEBUG] Using conversation history:", conversation)
            
            # Generate streaming response using the model
            try:
                for token in self._model_inference.generate_response(
                    messages=conversation,
                    **params
                ):
                    if token:
                        print(f"[DEBUG] Bot yielding token: {token}")
                        yield token
                        
            except Exception as e:
                print(f"[ERROR] Error in streaming response: {e}")
                yield {'token': f"Error generating response: {str(e)}"}
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            yield {'token': f"Error generating response: {str(e)}"}

class BotManager:
    def __init__(self, bots_dir: str = "bots", models_dir: str = "models"):
        self.bots_dir = bots_dir
        self.models_dir = models_dir
        self.bots: Dict[str, Bot] = {}
        self._ensure_bots_directory()
        self._ensure_default_bot()
        self._load_bots()

    def _ensure_bots_directory(self):
        """Ensure the bots directory exists"""
        if not os.path.exists(self.bots_dir):
            os.makedirs(self.bots_dir)
            logger.info(f"Created bots directory: {self.bots_dir}")

    def _load_bots(self):
        """Load all bots from the bots directory"""
        try:
            for filename in os.listdir(self.bots_dir):
                if filename.endswith('.json'):
                    bot_id = filename[:-5]  # Remove .json extension
                    if bot_id not in self.bots:  # Only load if not already in memory
                        try:
                            bot_path = os.path.join(self.bots_dir, filename)
                            with open(bot_path, 'r') as f:
                                bot_data = json.load(f)
                                # Skip invalid bot files
                                if not all(key in bot_data for key in ['name', 'system_prompt', 'base_model', 'parameters']):
                                    logger.warning(f"Skipping invalid bot file: {filename}")
                                    continue
                                bot = Bot(
                                    id=bot_id,
                                    name=bot_data['name'],
                                    system_prompt=bot_data['system_prompt'],
                                    base_model=bot_data['base_model'],
                                    parameters=bot_data['parameters']
                                )
                                self.bots[bot_id] = bot
                                logger.info(f"Loaded bot: {bot_id}")
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.error(f"Error loading bot {filename}: {str(e)}")
                            # Remove corrupted bot file
                            os.remove(os.path.join(self.bots_dir, filename))
                            logger.info(f"Removed corrupted bot file: {filename}")
        except Exception as e:
            logger.error(f"Error loading bots: {str(e)}")

    def _ensure_default_bot(self):
        """Create default MIDAS40 bot if it doesn't exist"""
        try:
            default_bot = Bot(
                id='MIDAS40',
                name='MIDAS40',
                system_prompt=(
                    "You are MIDAS40, an advanced AI assistant created by Cyber Beast Tech. "
                    "You are helpful, knowledgeable, and precise in your responses. "
                    "You aim to provide accurate information and assist users with their tasks "
                    "while maintaining a professional and friendly demeanor."
                ),
                base_model='llama-2-7b-chat.q4_k_m',  # Updated to match actual model file name
                parameters={
                    'temperature': 0.7,
                    'max_new_tokens': 1000,
                    'top_p': 0.95,
                    'top_k': 50,
                    'repetition_penalty': 1.2
                }
            )
            self.bots['MIDAS40'] = default_bot
            self._save_bot(default_bot)
            logger.info("Created default MIDAS40 bot")
        except Exception as e:
            logger.error(f"Error creating default bot: {str(e)}")

    def _save_bot(self, bot: Bot):
        """Save a bot to file"""
        try:
            bot_path = os.path.join(self.bots_dir, f"{bot.id}.json")
            with open(bot_path, 'w') as f:
                json.dump(bot.to_dict(), f, indent=4)
            logger.info(f"Saved bot: {bot.id}")
        except Exception as e:
            logger.error(f"Error saving bot {bot.id}: {str(e)}")

    def get_bot(self, bot_id: str) -> Optional[Bot]:
        """Get a bot by ID and ensure its model is loaded"""
        bot = self.bots.get(bot_id)
        if bot is None:
            return None
            
        # Check if model needs to be loaded
        if not bot._model_loaded:
            # Use uppercase model name to match actual file
            model_filename = f"{bot.base_model.upper()}.gguf"
            model_path = os.path.join(os.path.abspath(self.models_dir), model_filename)
            logger.info(f"Attempting to load model from: {model_path}")
            
            if os.path.exists(model_path):
                logger.info(f"Found model file at: {model_path}")
                success = bot.load_model(model_path)
                if not success:
                    logger.error(f"Failed to load model for bot {bot_id}")
            else:
                logger.error(f"Model file not found: {model_path}")
                # Try alternate casing
                alt_model_path = os.path.join(os.path.abspath(self.models_dir), f"{bot.base_model}.gguf")
                if os.path.exists(alt_model_path):
                    logger.info(f"Found model file with alternate casing at: {alt_model_path}")
                    success = bot.load_model(alt_model_path)
                    if not success:
                        logger.error(f"Failed to load model for bot {bot_id}")
                else:
                    logger.error(f"Model file not found with alternate casing: {alt_model_path}")
                
        return bot

    def create_bot(self, bot_id: str, name: str, system_prompt: str, base_model: str, parameters: Dict) -> Optional[Bot]:
        """Create a new bot or update existing one"""
        try:
            # Create or update bot
            bot = Bot(
                id=bot_id,
                name=name,
                system_prompt=system_prompt,
                base_model=base_model,
                parameters=parameters
            )
            
            # Try to load the model with proper casing
            model_filename = f"{base_model.upper()}.gguf"
            model_path = os.path.join(os.path.abspath(self.models_dir), model_filename)
            logger.info(f"Attempting to load model from: {model_path}")
            
            if os.path.exists(model_path):
                logger.info(f"Found model file at: {model_path}")
                success = bot.load_model(model_path)
                if not success:
                    logger.error(f"Failed to load model for new bot {bot_id}")
            else:
                # Try alternate casing
                alt_model_path = os.path.join(os.path.abspath(self.models_dir), f"{base_model}.gguf")
                if os.path.exists(alt_model_path):
                    logger.info(f"Found model file with alternate casing at: {alt_model_path}")
                    success = bot.load_model(alt_model_path)
                    if not success:
                        logger.error(f"Failed to load model for new bot {bot_id}")
                else:
                    logger.error(f"Model file not found: {model_path} or {alt_model_path}")
            
            # Save and store the bot
            self.bots[bot_id] = bot
            self._save_bot(bot)
            return bot
            
        except Exception as e:
            logger.error(f"Error creating bot: {str(e)}")
            return None

    def update_bot(self, bot_id: str, **kwargs) -> Optional[Bot]:
        """Update an existing bot"""
        bot = self.bots.get(bot_id)
        if bot is None:
            return None
            
        try:
            # Update bot attributes
            for key, value in kwargs.items():
                if hasattr(bot, key):
                    setattr(bot, key, value)
            
            # If base_model changed, try to load new model
            if 'base_model' in kwargs:
                bot.unload_model()  # Unload old model
                model_filename = f"{kwargs['base_model'].upper()}.gguf"
                model_path = os.path.join(os.path.abspath(self.models_dir), model_filename)
                logger.info(f"Attempting to load new model from: {model_path}")
                
                if os.path.exists(model_path):
                    logger.info(f"Found new model file at: {model_path}")
                    success = bot.load_model(model_path)
                    if not success:
                        logger.error(f"Failed to load new model for bot {bot_id}")
                else:
                    # Try alternate casing
                    alt_model_path = os.path.join(os.path.abspath(self.models_dir), f"{kwargs['base_model']}.gguf")
                    if os.path.exists(alt_model_path):
                        logger.info(f"Found new model file with alternate casing at: {alt_model_path}")
                        success = bot.load_model(alt_model_path)
                        if not success:
                            logger.error(f"Failed to load new model for bot {bot_id}")
                    else:
                        logger.error(f"New model file not found: {model_path} or {alt_model_path}")
            
            bot.updated_at = datetime.now().isoformat()
            self._save_bot(bot)
            return bot
            
        except Exception as e:
            logger.error(f"Error updating bot: {str(e)}")
            return None

    def delete_bot(self, bot_id: str) -> bool:
        """Delete a bot"""
        try:
            bot = self.bots.pop(bot_id, None)
            if bot:
                bot.unload_model()  # Unload model before deletion
                bot_path = os.path.join(self.bots_dir, f"{bot_id}.json")
                if os.path.exists(bot_path):
                    os.remove(bot_path)
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting bot: {str(e)}")
            return False

    def list_bots(self) -> List[Dict]:
        """List all bots"""
        return [bot.to_dict() for bot in self.bots.values()]

    def chat(self, bot_id: str, message: str, parameters: Dict = None) -> Dict[str, Any]:
        """Generate a chat response from a bot"""
        try:
            # Get the bot
            bot = self.get_bot(bot_id)
            if not bot:
                raise ValueError(f"Bot {bot_id} not found")
            
            print(f"[DEBUG] Chat request for bot {bot_id}")
            print(f"[DEBUG] Message: {message[:50]}...")
            
            # Generate response
            if parameters is None:
                parameters = {}
            
            # Convert parameter names to match llama.cpp
            model_params = {
                'temperature': parameters.get('temperature', 0.7),
                'max_tokens': parameters.get('max_new_tokens', 1000),
                'top_p': parameters.get('top_p', 0.95),
                'top_k': parameters.get('top_k', 40),
                'repeat_penalty': parameters.get('repetition_penalty', 1.1)
            }
            
            print(f"[DEBUG] Using model parameters: {model_params}")
            
            # Create messages list with proper format
            messages = [{'role': 'user', 'content': message}]
            print(f"[DEBUG] Formatted messages: {messages}")
            
            # Generate response using model inference
            response = bot._model_inference.generate_response(
                messages=messages,
                **model_params
            )
            
            print("[DEBUG] Got response from model inference")
            
            # Process and return response
            if isinstance(response, str):
                print("[DEBUG] Got string response")
                return {'response': response}
            else:
                print("[DEBUG] Got streaming response")
                try:
                    # For streaming responses, yield each token
                    for token in response:
                        print(f"[DEBUG] Yielding token: {token[:20]}...")
                        yield {'token': token}
                except Exception as e:
                    print(f"[ERROR] Error in streaming response: {e}")
                    raise
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise
