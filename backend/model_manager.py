import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import requests
from tqdm import tqdm

logger = logging.getLogger(__name__)

@dataclass
class ModelInfo:
    name: str
    size: str
    type: str
    url: str
    local_path: str
    is_downloaded: bool = False
    is_loaded: bool = False

class ModelManager:
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        self.models_info_path = self.models_dir / "models_info.json"
        self.config_path = self.models_dir / "config.json"
        self.models: Dict[str, ModelInfo] = {}
        self.last_selected_model = None
        self._load_config()
        self._load_models_info()
        
        # Default models configuration
        self.default_models = {
            "llama-2-7b-chat.q4_k_m": {
                "name": "llama-2-7b-chat.Q4_K_M",
                "size": "3.83GB",
                "type": "GGUF",
                "url": "https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf"
            },
            "llama-2-13b-chat.q4_k_m": {
                "name": "llama-2-13b-chat.Q4_K_M",
                "size": "7.16GB",
                "type": "GGUF",
                "url": "https://huggingface.co/TheBloke/Llama-2-13B-Chat-GGUF/resolve/main/llama-2-13b-chat.Q4_K_M.gguf"
            }
        }
        
        # Add default models if not present
        for model_id, info in self.default_models.items():
            if model_id not in self.models:
                self.add_model(
                    name=info["name"],
                    size=info["size"],
                    type=info["type"],
                    url=info["url"]
                )

    def _load_config(self):
        """Load configuration including last selected model"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                self.last_selected_model = config.get('last_selected_model')
        else:
            self._save_config()

    def _save_config(self):
        """Save configuration including last selected model"""
        config = {
            'last_selected_model': self.last_selected_model
        }
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=4)

    def _load_models_info(self):
        """Load models information from JSON file"""
        if self.models_info_path.exists():
            with open(self.models_info_path, 'r') as f:
                models_data = json.load(f)
                self.models = {
                    model_id: ModelInfo(**data)
                    for model_id, data in models_data.items()
                }

    def _save_models_info(self):
        """Save models information to JSON file"""
        models_data = {
            model_id: {
                "name": model.name,
                "size": model.size,
                "type": model.type,
                "url": model.url,
                "local_path": model.local_path,
                "is_downloaded": model.is_downloaded,
                "is_loaded": model.is_loaded
            }
            for model_id, model in self.models.items()
        }
        with open(self.models_info_path, 'w') as f:
            json.dump(models_data, f, indent=4)

    def get_default_or_last_model(self) -> Optional[str]:
        """Get the ID of the last selected model or the default model"""
        if self.last_selected_model and self.last_selected_model in self.models:
            return self.last_selected_model
        
        # If no last selected model, try to get the first downloaded model
        downloaded_models = self.get_downloaded_models()
        if downloaded_models:
            return downloaded_models[0].name.lower()
            
        # If no downloaded models, return the default model
        return "llama-2-7b-chat.q4_k_m"

    def set_last_selected_model(self, model_id: str):
        """Update the last selected model"""
        self.last_selected_model = model_id
        self._save_config()

    def add_model(self, name: str, size: str, type: str, url: str) -> ModelInfo:
        """Add a new model to the manager"""
        model_id = name.lower()
        local_path = str(self.models_dir / f"{name}.{type.lower()}")
        
        model_info = ModelInfo(
            name=name,
            size=size,
            type=type,
            url=url,
            local_path=local_path,
            is_downloaded=os.path.exists(local_path)
        )
        
        self.models[model_id] = model_info
        self._save_models_info()
        return model_info

    def remove_model(self, model_id: str) -> bool:
        """Remove a model from the manager and delete its files"""
        if model_id not in self.models:
            return False
            
        model = self.models[model_id]
        if os.path.exists(model.local_path):
            os.remove(model.local_path)
        
        del self.models[model_id]
        self._save_models_info()
        return True

    def download_model(self, model_id: str, force: bool = False) -> bool:
        """Download a model from its URL"""
        if model_id not in self.models:
            logger.error(f"Model {model_id} not found")
            return False
            
        model = self.models[model_id]
        if model.is_downloaded and not force:
            logger.info(f"Model {model_id} already downloaded")
            return True
            
        try:
            logger.info(f"Downloading model {model_id} from {model.url}")
            response = requests.get(model.url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            with open(model.local_path, 'wb') as f, tqdm(
                desc=model.name,
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar:
                for data in response.iter_content(chunk_size=1024):
                    size = f.write(data)
                    pbar.update(size)
            
            model.is_downloaded = True
            self._save_models_info()
            logger.info(f"Model {model_id} downloaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading model {model_id}: {e}")
            if os.path.exists(model.local_path):
                os.remove(model.local_path)
            return False

    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get information about a specific model"""
        return self.models.get(model_id)

    def list_models(self) -> List[ModelInfo]:
        """List all available models"""
        return list(self.models.values())

    def get_downloaded_models(self) -> List[ModelInfo]:
        """Get list of downloaded models"""
        return [model for model in self.models.values() if model.is_downloaded]

    def get_loaded_models(self) -> List[ModelInfo]:
        """Get list of currently loaded models"""
        return [model for model in self.models.values() if model.is_loaded]

    def set_model_loaded(self, model_id: str, loaded: bool = True):
        """Update the loaded status of a model"""
        if model_id in self.models:
            self.models[model_id].is_loaded = loaded
            self._save_models_info()
