import os
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass
from llama_cpp import Llama
import itertools

logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    model_path: str
    n_ctx: int = 2048
    n_threads: int = None  # Will use all available threads
    n_batch: int = 512
    top_k: int = 40
    top_p: float = 0.95
    temp: float = 0.7
    repeat_penalty: float = 1.1

class ModelInference:
    def __init__(self):
        self._model = None
        self._model_path = None
        
    def __del__(self):
        """Clean up model when object is deleted"""
        try:
            if hasattr(self, '_model') and self._model is not None:
                self._model = None
        except:
            pass
        
    def load_model(self, model_path: str, config: Optional[ModelConfig] = None) -> bool:
        """Load a model from the given path"""
        try:
            print(f"[DEBUG] Loading model from {model_path}...")
            if not os.path.exists(model_path):
                raise ValueError(f"Model path does not exist: {model_path}")
                
            if config is None:
                config = ModelConfig(model_path=model_path)
            
            # Unload current model if any
            self.unload_model()
            
            logger.info(f"Loading model from {model_path}")
            self._model = Llama(
                model_path=model_path,
                n_ctx=config.n_ctx,
                n_threads=config.n_threads,
                n_batch=config.n_batch
            )
            self._model_path = model_path
            logger.info(f"Model loaded successfully from {model_path}")
            print("[DEBUG] Model loaded successfully")
            print(f"[DEBUG] Model config: ctx={config.n_ctx}, threads={config.n_threads}, batch={config.n_batch}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to load model: {e}")
            logger.error(f"Error loading model: {e}")
            self._model = None
            return False
    
    def unload_model(self) -> None:
        """Unload the current model"""
        try:
            if self._model is not None:
                del self._model
                self._model = None
                self._model_path = None
                logger.info("Model unloaded")
        except:
            pass
    
    def generate_response(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        top_p: float = 0.95,
        top_k: int = 40,
        repeat_penalty: float = 1.1
    ):
        """Generate a streaming response using the loaded model"""
        try:
            if not self._model:
                raise ValueError("Model not loaded")

            print("\n[DEBUG] Starting response generation...")
            print(f"[DEBUG] Parameters: temp={temperature}, max_tokens={max_tokens}, top_p={top_p}, top_k={top_k}")

            # Format conversation history into prompt
            prompt = self._format_prompt(messages)
            print(f"[DEBUG] Formatted prompt: {prompt[:100]}...")
            
            # Set up generation parameters for llama.cpp
            params = {
                'temperature': temperature,
                'max_tokens': max_tokens,
                'top_p': top_p,
                'top_k': top_k,
                'repeat_penalty': repeat_penalty,
                'echo': False
            }
            
            print("[DEBUG] Starting token generation with params:", params)
            
            # Track full response for prefix removal
            full_response = ""
            prefix_removed = False
            token_count = 0
            
            # Generate streaming response
            try:
                print("[DEBUG] Calling model generate...")
                for output in self._model(prompt, stream=True, **params):
                    print(f"[DEBUG] Got output: {output}")
                    if isinstance(output, dict) and 'choices' in output and len(output['choices']) > 0:
                        token = output['choices'][0].get('text', '')
                        print(f"[DEBUG] Got token: {token}")
                        if token:
                            token_count += 1
                            if token_count % 10 == 0:  # Print every 10 tokens
                                print(f"[DEBUG] Generated {token_count} tokens...")
                                
                            # Add token to full response
                            full_response += token
                            
                            # Remove prefix once we have enough text
                            if not prefix_removed and len(full_response.strip()) > 10:
                                print(f"[DEBUG] Removing prefix from: {full_response[:50]}...")
                                full_response = self.process_response(full_response)
                                prefix_removed = True
                                print(f"[DEBUG] After prefix removal: {full_response[:50]}...")
                                # Yield the processed initial text
                                yield {'token': full_response}
                            elif prefix_removed:
                                # Format the token for markdown if needed
                                if '\n' in token or token.startswith('#') or token.startswith('`'):
                                    formatted_token = self.format_response(token)
                                    if formatted_token != token:
                                        print(f"[DEBUG] Formatted token: {formatted_token}")
                                        yield {'token': formatted_token}
                                        continue
                                
                                # Yield the raw token
                                yield {'token': token}
                    else:
                        print(f"[DEBUG] Unexpected output format: {output}")
            except Exception as e:
                print(f"[ERROR] Error in model generation: {e}")
                raise
            
            print(f"[DEBUG] Response generation complete. Total tokens: {token_count}")
                    
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            print(f"[ERROR] Response generation failed: {str(e)}")
            yield {'token': "I apologize, but I encountered an error while generating the response."}

    def _format_prompt(self, messages: List[Dict]) -> str:
        """Format conversation history into prompt"""
        formatted_messages = []
        
        # Add system message without role prefix
        system_msg = next((msg['content'] for msg in messages if msg['role'] == 'system'), None)
        if system_msg:
            formatted_messages.append(system_msg)
            
        # Format the conversation
        for msg in messages:
            if msg['role'] == 'system':
                continue  # Skip system message as we've already added it
                
            content = msg.get('content', '').strip()
            if msg['role'] == 'user':
                formatted_messages.append(f"Question: {content}")
            else:
                formatted_messages.append(f"Answer: {content}")
        
        # Add final prompt without role marker
        formatted_messages.append("Answer:")
        
        # Join with double newlines for better separation
        prompt = "\n\n".join(formatted_messages)
        print(f"[DEBUG] Final formatted prompt: {prompt}")
        return prompt

    def process_response(self, text: str) -> str:
        """Clean up and format the response text"""
        if not text:
            return text
            
        # Remove common prefixes
        prefixes_to_remove = [
            "Assistant:", "MIDAS:", "MIDAS40:", "AI:", "Bot:",
            "assistant:", "midas:", "midas40:", "ai:", "bot:",
            "Human:", "User:", "human:", "user:",
            "Question:", "Answer:", "question:", "answer:",
            "Let me help you with that.", "I'll help you with that.",
            "Here's what I can tell you:", "Here's what I found:",
            "Let me explain:", "Here's the answer:",
            "I'll", "I will", "Let me"
        ]
        
        # Sort prefixes by length (longest first) to handle overlapping prefixes
        prefixes_to_remove.sort(key=len, reverse=True)
        
        # Clean the text
        cleaned_text = text.strip()
        
        # First pass: remove prefixes at the start
        for prefix in prefixes_to_remove:
            if cleaned_text.lower().startswith(prefix.lower()):
                print(f"[DEBUG] Found prefix to remove: '{prefix}'")
                cleaned_text = cleaned_text[len(prefix):].strip()
        
        # Handle multi-line text with prefixes
        if '\n' in cleaned_text:
            lines = cleaned_text.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                # Check each line for prefixes
                for prefix in prefixes_to_remove:
                    if line.lower().startswith(prefix.lower()):
                        print(f"[DEBUG] Found prefix in line: '{prefix}'")
                        line = line[len(prefix):].strip()
                        break
                if line:  # Only add non-empty lines
                    cleaned_lines.append(line)
            cleaned_text = '\n'.join(cleaned_lines)
        
        # Second pass: clean up any remaining markers
        while True:
            original = cleaned_text
            for prefix in prefixes_to_remove:
                cleaned_text = cleaned_text.replace(f"\n{prefix}", "\n")
                cleaned_text = cleaned_text.replace(f" {prefix}", " ")
            if original == cleaned_text:
                break
        
        # Remove any "Answer:" that might appear at the end
        cleaned_text = cleaned_text.rstrip("Answer:").rstrip()
        
        print(f"[DEBUG] After prefix removal: '{cleaned_text[:50]}...'")
        return cleaned_text.strip()

    def format_response(self, response: str) -> str:
        """Format the response text to ensure proper markdown rendering and spacing"""
        # Handle empty response
        if not response:
            return response
            
        # Handle single newline
        if response == "\n":
            return "\n\n"
            
        # Remove extra newlines at the start and end
        response = response.strip()
        
        # Special handling for markdown elements that need spacing
        if response.startswith(('#', '-', '*', '>', '1.', '```')):
            # Add newline before headers, lists, quotes, and code blocks if they're at the start
            return f"\n{response}"
            
        # Handle code blocks
        if '```' in response:
            # Ensure proper spacing around code blocks
            response = response.replace("```", "\n```")
            return response
            
        # Handle lists
        if response.startswith(('- ', '* ', '+ ', '1. ')):
            # Add newline before list items
            return f"\n{response}"
            
        # Handle quotes
        if response.startswith('> '):
            # Add newline before quotes
            return f"\n{response}"
            
        # Handle multiple newlines
        if response.count('\n') > 1:
            # Preserve multiple newlines but normalize them
            lines = response.split('\n')
            return '\n\n'.join(line.strip() for line in lines if line.strip())
            
        return response
