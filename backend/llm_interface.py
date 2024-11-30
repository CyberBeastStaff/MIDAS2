from llama_cpp import Llama
import logging
from threading import Thread
from queue import Queue
import time
import torch
from .model_manager import ModelManager

logger = logging.getLogger(__name__)

class LLMInterface:
    def __init__(self):
        self.model_manager = ModelManager()
        self.model = None
        self.current_model_id = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        
        # Load the last selected model or default
        model_id = self.model_manager.get_default_or_last_model()
        if model_id:
            self.load_model(model_id)

    def load_model(self, model_id: str) -> bool:
        """Load a specific model"""
        if self.current_model_id == model_id and self.model is not None:
            logger.info(f"Model {model_id} already loaded")
            return True

        model_info = self.model_manager.get_model_info(model_id)
        if not model_info:
            logger.error(f"Model {model_id} not found")
            return False

        if not model_info.is_downloaded:
            logger.info(f"Downloading model {model_id}")
            if not self.model_manager.download_model(model_id):
                return False

        try:
            # Unload current model if any
            if self.model is not None:
                self.model = None
                if self.current_model_id:
                    self.model_manager.set_model_loaded(self.current_model_id, False)

            logger.info(f"Loading model: {model_id}")
            n_gpu_layers = -1 if self.device == "cuda" else 0
            self.model = Llama(
                model_path=model_info.local_path,
                n_gpu_layers=n_gpu_layers,
                n_ctx=2048,
                n_batch=512,
            )
            
            self.current_model_id = model_id
            self.model_manager.set_model_loaded(model_id, True)
            self.model_manager.set_last_selected_model(model_id)
            logger.info("Model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model = None
            self.current_model_id = None
            return False

    def unload_model(self):
        """Unload the current model"""
        if self.model is not None:
            self.model = None
            if self.current_model_id:
                self.model_manager.set_model_loaded(self.current_model_id, False)
                self.current_model_id = None
            logger.info("Model unloaded")

    def get_available_models(self):
        """Get list of all available models"""
        return self.model_manager.list_models()

    def generate_response(self, message, history, temperature=0.7, max_new_tokens=1000, 
                        top_p=0.95, top_k=50, repetition_penalty=1.2):
        if not self.model:
            yield "Error: Model not loaded properly"
            return

        # Format conversation history
        conversation = ""
        if history:
            for h in history[-3:]:  # Last 3 turns
                conversation += f"User: {h[0]}\nAssistant: {h[1]}\n"
        conversation += f"User: {message}\nAssistant:"

        # Create a queue for streaming responses
        stream_queue = Queue()
        
        def generate():
            try:
                response = ""
                for chunk in self.model(
                    conversation,
                    max_tokens=min(max_new_tokens, 500),
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    repeat_penalty=repetition_penalty,
                    stream=True
                ):
                    if chunk.get("choices"):
                        text = chunk["choices"][0]["text"]
                        response += text
                        stream_queue.put(response)
                stream_queue.put(None)  # Signal completion
            except Exception as e:
                logger.error(f"Generation error: {e}")
                stream_queue.put(f"Error during generation: {str(e)}")
                stream_queue.put(None)

        # Start generation in a separate thread
        Thread(target=generate).start()

        # Stream the response
        while True:
            response = stream_queue.get()
            if response is None:
                break
            yield response.strip()

        logger.info("Response generation complete")
