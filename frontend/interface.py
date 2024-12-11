import os
import sys
import json
import time
import torch
import gradio as gr
import requests
import threading
from datetime import datetime
from queue import Queue

# Constants
BACKEND_URL = "http://localhost:7860"

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.system_monitor import get_system_info
from backend.llm_interface import LLMInterface

# Load external CSS file
with open('frontend/static/styles.css', 'r') as f:
    CUSTOM_CSS = f.read()

CUSTOM_CSS += """
.title {
    text-align: center;
    color: #10a37f;
    font-size: 2.5em;
    margin: 20px 0;
    font-weight: 600;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
}

.chat-title {
    text-align: left;
    color: #e5e7eb;
    font-size: 1.2em;
    margin: 0;
    flex-grow: 1;
}

.chat-controls {
    display: flex;
    gap: 8px;
    align-items: center;
}

.chat-controls button {
    min-width: 60px;
}

.control-btn {
    border-radius: 8px;
    padding: 6px 12px;
    min-width: 40px;
    background-color: #2d3748;
    color: #e5e7eb;
    border: 1px solid #4a5568;
}

.control-btn:hover {
    background-color: #4a5568;
}

.small-btn {
    padding: 4px 8px;
    min-width: 30px;
    font-size: 0.9em;
}

/* Dark theme overrides */
.dark {
    background-color: #1a202c;
    color: #e5e7eb;
}

.dark input, .dark textarea, .dark select {
    background-color: #2d3748;
    color: #e5e7eb;
    border-color: #4a5568;
}

.dark button {
    background-color: #2d3748;
    color: #e5e7eb;
    border-color: #4a5568;
}

.dark button:hover {
    background-color: #4a5568;
}

.dark .tabs {
    border-color: #4a5568;
}

.dark .tab-selected {
    border-color: #10a37f;
    color: #10a37f;
}

.dark .markdown {
    color: #e5e7eb;
}

.dark .table {
    background-color: #2d3748;
    color: #e5e7eb;
    border-color: #4a5568;
}

.dark .table th {
    background-color: #1a202c;
    color: #e5e7eb;
    border-color: #4a5568;
}

.dark .table td {
    border-color: #4a5568;
}

"""

def create_interface():
    llm = LLMInterface()
    
    def get_downloaded_models():
        try:
            response = requests.get(f'{BACKEND_URL}/api/models/downloaded')
            if response.status_code == 200:
                models = response.json()
                return [model['name'] for model in models]
            return []
        except Exception as e:
            print(f"[ERROR] Failed to get downloaded models: {e}")
            return []

    def update_base_model_choices():
        downloaded_models = get_downloaded_models()
        if not downloaded_models:  # If no models are downloaded, provide default choices
            downloaded_models = ["mistral", "llama2", "codellama"]
        return gr.update(choices=downloaded_models, value=downloaded_models[0] if downloaded_models else None)

    # Model Management Functions
    def list_available_models():
        try:
            response = requests.get(f'{BACKEND_URL}/api/models')
            if response.status_code == 200:
                models = response.json()
                return [
                    [
                        model['name'],
                        model['size'],
                        "✓" if model['is_downloaded'] else "✗",
                        "✓" if model['is_loaded'] else "✗"
                    ]
                    for model in models
                ]
            return []
        except Exception as e:
            print(f"[ERROR] Failed to list models: {e}")
            return []

    def download_model(model_name):
        try:
            response = requests.post(f'{BACKEND_URL}/api/models/{model_name.lower()}/download')
            if response.status_code == 200:
                return f"Successfully started downloading {model_name}"
            return f"Failed to download {model_name}: {response.text}"
        except Exception as e:
            return f"Error downloading model: {str(e)}"

    def remove_model(model_name):
        try:
            response = requests.delete(f'{BACKEND_URL}/api/models/{model_name.lower()}')
            if response.status_code == 200:
                return f"Successfully removed {model_name}"
            return f"Failed to remove {model_name}: {response.text}"
        except Exception as e:
            return f"Error removing model: {str(e)}"

    def add_custom_model(name, size, type, url):
        try:
            if not all([name, size, type, url]):
                return "All fields are required"
            
            data = {
                "name": name,
                "size": size,
                "type": type,
                "url": url
            }
            
            response = requests.post(
                f'{BACKEND_URL}/api/models',
                json=data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                return "Successfully added new model"
            return f"Failed to add model: {response.text}"
        except Exception as e:
            return f"Error adding model: {str(e)}"

    def refresh_model_list():
        return gr.update(value=list_available_models())

    def list_chats():
        """Get list of available chats"""
        try:
            response = requests.get('http://127.0.0.1:7860/api/chats')
            if response.status_code == 200:
                chats = response.json()
                # Sort chats by timestamp if available
                if chats and 'timestamp' in chats[0]:
                    chats.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                # Store chat_id in the value but only show title in display
                choices = {chat['title']: f"{chat['title']} ({chat['id']})" for chat in chats}
                return list(choices.keys())  # Only return the titles
            else:
                print(f"[ERROR] Failed to get chats: {response.status_code}")
                print(f"[ERROR] Response: {response.text}")
                return []
        except Exception as e:
            print(f"[ERROR] Exception in list_chats: {str(e)}")
            return []

    def refresh_chat_list():
        """Refresh the chat list dropdown"""
        print("[DEBUG] Refreshing chat list")
        choices = list_chats()
        print(f"[DEBUG] Updated chat list: {choices}")
        return gr.update(choices=choices)

    def create_title_from_message(message, max_words=3):
        """Create a concise 2-3 word title from the user's message"""
        # Remove special characters and extra spaces
        clean_msg = ' '.join(message.split())
        words = clean_msg.split()
        if len(words) <= max_words:
            return clean_msg
        return ' '.join(words[:max_words]) + '...'

    def create_new_chat():
        """Create a new chat and return its title"""
        try:
            # Create new chat with headers
            headers = {'Content-Type': 'application/json'}
            initial_title = f"Chat {datetime.now().strftime('%I:%M %p')}"
            
            response = requests.post(
                'http://127.0.0.1:7860/api/chats',
                json={'title': initial_title, 'temporary': True},  # Mark as temporary
                headers=headers
            )
            
            if response.status_code == 200:
                chat_data = response.json()
                chat_id = chat_data['id']
                
                # Update chat list and return new state
                choices = list_chats()
                return gr.update(choices=choices, value=initial_title), [], f"### {initial_title}"
            else:
                print(f"[ERROR] Failed to create chat: {response.status_code}")
                print(f"[ERROR] Response: {response.text}")
                return gr.update(), [], "### Error creating chat"
        except Exception as e:
            print(f"[ERROR] Failed to create chat: {e}")
            return gr.update(), [], "### Error creating chat"

    def submit_message(msg, history, chat_selection, bot_selection, temperature, max_new_tokens, top_p, top_k, repetition_penalty):
        """Submit a message and get streaming response"""
        if not msg or not chat_selection:
            return history, ""
            
        print("\n[DEBUG] Processing new message...")
        print(f"[DEBUG] Message: {msg[:50]}...")
        print(f"[DEBUG] Selected bot: {bot_selection}")
        
        # Format user message
        formatted_msg = msg.strip()
        history = history + [[formatted_msg, ""]]  # Initialize with empty response
        print("[DEBUG] Added user message to history")
        yield history, ""  # Show user message immediately
        
        try:
            # Get chat ID from selection
            print("[DEBUG] Fetching chat information...")
            response = requests.get('http://127.0.0.1:7860/api/chats')
            chats = response.json() if response.status_code == 200 else []
            selected_chat = next((chat for chat in chats if chat['title'] == chat_selection), None)
            
            if not selected_chat:
                print(f"[ERROR] Could not find chat for title: {chat_selection}")
                history[-1][1] = "Error: Could not find chat"
                yield history, ""
                return
                
            chat_id = selected_chat['id']
            print(f"[DEBUG] Using chat ID: {chat_id}")
            
            # Save the user's message
            headers = {'Content-Type': 'application/json'}
            if chat_id:
                try:
                    print("[DEBUG] Saving user message to chat history...")
                    # Mark chat as permanent since a message was sent
                    requests.put(
                        f'http://127.0.0.1:7860/api/chats/{chat_id}',
                        json={'temporary': False},
                        headers=headers
                    )
                    
                    # Save the message
                    response = requests.post(
                        f'http://127.0.0.1:7860/api/chats/{chat_id}/messages',
                        json={'role': 'user', 'content': formatted_msg},
                        headers=headers
                    )
                    print(f"[DEBUG] Message saved. Status: {response.status_code}")
                except Exception as e:
                    print(f"[ERROR] Failed to save user message: {e}")
            
            # Get streaming response
            try:
                print("[DEBUG] Requesting bot response...")
                print(f"[DEBUG] Parameters: temp={temperature}, tokens={max_new_tokens}, top_p={top_p}, top_k={top_k}")
                
                response = requests.post(
                    f'http://127.0.0.1:7860/api/bots/{bot_selection}/chat',
                    json={
                        'message': formatted_msg,
                        'parameters': {
                            'temperature': temperature,
                            'max_new_tokens': max_new_tokens,
                            'top_p': top_p,
                            'top_k': top_k,
                            'repetition_penalty': repetition_penalty
                        }
                    },
                    headers=headers,
                    stream=True
                )
                
                if response.status_code == 200:
                    print("[DEBUG] Starting to process streaming response...")
                    token_count = 0
                    current_response = ""
                    
                    # Process streaming response
                    for line in response.iter_lines():
                        if line and line.startswith(b'data: '):
                            try:
                                # Remove 'data: ' prefix and parse JSON
                                json_str = line.decode()[6:]
                                print(f"[DEBUG] Raw JSON: {json_str}")
                                data = json.loads(json_str)
                                print(f"[DEBUG] Decoded data: {data}")
                                
                                if 'token' in data:
                                    token = data['token']
                                    print(f"[DEBUG] Got token: {token}")
                                    token_count += 1
                                    if token_count % 20 == 0:
                                        print(f"[DEBUG] Received {token_count} tokens...")
                                    
                                    current_response += token
                                    history[-1][1] = current_response
                                    yield history, ""
                                    
                            except json.JSONDecodeError as e:
                                print(f"[ERROR] Failed to decode JSON: {e}")
                                print(f"[DEBUG] Problem line: {line}")
                                continue
                            except Exception as e:
                                print(f"[ERROR] Error processing token: {e}")
                                continue
                    
                    print(f"[DEBUG] Response complete. Total tokens: {token_count}")
                    print(f"[DEBUG] Final response: {current_response[:100]}...")
                    
                    # Save the complete response
                    if chat_id and current_response:
                        print("[DEBUG] Saving complete response to chat history...")
                        save_response = requests.post(
                            f'http://127.0.0.1:7860/api/chats/{chat_id}/messages',
                            json={'role': 'assistant', 'content': current_response},
                            headers=headers
                        )
                        print(f"[DEBUG] Response saved. Status: {save_response.status_code}")
                        
                else:
                    error_msg = f"Error: Failed to get response (Status: {response.status_code})"
                    print(f"[ERROR] {error_msg}")
                    history[-1][1] = error_msg
                    yield history, ""
                    
            except Exception as e:
                print(f"[ERROR] Error in streaming response: {e}")
                history[-1][1] = f"Error: {str(e)}"
                yield history, ""
                
        except Exception as e:
            print(f"[ERROR] Error in submit_message: {e}")
            history[-1][1] = f"Error: {str(e)}"
            yield history, ""

    def load_selected_chat(chat_selection):
        """Load a selected chat from the dropdown menu"""
        if not chat_selection:
            return None, "### New Chat"
        
        try:
            # Get chat ID mapping
            response = requests.get('http://127.0.0.1:7860/api/chats')
            chats = response.json() if response.status_code == 200 else []
            title_to_id = {chat['title']: chat['id'] for chat in chats}
            chat_id = title_to_id.get(chat_selection)
            
            if not chat_id:
                print(f"[ERROR] Could not find chat ID for title: {chat_selection}")
                return None, "### Error Loading Chat"
            
            print(f"\n[DEBUG] Loading chat {chat_id}")
            
            response = requests.get(f'http://127.0.0.1:7860/api/chats/{chat_id}')
            if response.status_code != 200:
                print(f"[ERROR] Failed to load chat: {response.status_code}")
                return None, "### Error Loading Chat"
            
            chat_data = response.json()
            history = []
            messages = chat_data.get('messages', [])
            
            # Sort messages by timestamp if available
            if messages and 'timestamp' in messages[0]:
                messages.sort(key=lambda x: x.get('timestamp', ''))
            
            # Group messages into pairs
            current_user_msg = None
            for msg in messages:
                role = msg.get('role')
                content = msg.get('content', '')
                
                if role == 'user':
                    current_user_msg = content
                elif role == 'assistant' and current_user_msg is not None:
                    history.append([current_user_msg, content])
                    current_user_msg = None
                elif role == 'assistant' and not history:
                    # First message is from assistant (greeting)
                    history.append([None, content])
                elif role == 'assistant':
                    # Standalone assistant message
                    history.append([None, content])
            
            # Add any remaining unpaired user message
            if current_user_msg is not None:
                history.append([current_user_msg, None])
            
            if not history:
                # If no messages, show greeting
                history = [[None, "Hello! I'm MIDAS, your AI assistant. How can I help you today?"]]
            
            title = chat_data.get('title', 'Chat')
            print(f"[DEBUG] Loaded chat with {len(history)} messages")
            return history, f"### {title}"
            
        except Exception as e:
            print(f"[ERROR] Error loading chat: {e}")
            return None, "### Error Loading Chat"

    def delete_chat(chat_selection):
        if not chat_selection:
            return gr.update(), None, "### New Chat"
        try:
            # Get chat ID mapping
            response = requests.get('http://127.0.0.1:7860/api/chats')
            chats = response.json() if response.status_code == 200 else []
            title_to_id = {chat['title']: chat['id'] for chat in chats}
            chat_id = title_to_id.get(chat_selection)
            
            if not chat_id:
                print(f"[ERROR] Could not find chat ID for title: {chat_selection}")
                return None, None, "### Error"
            
            print(f"Deleting chat: {chat_id}")  # Debug print
            response = requests.delete(f'http://127.0.0.1:7860/api/chats/{chat_id}')
            if response.status_code != 200:
                print(f"Error deleting chat: {response.status_code} - {response.text}")
                return None, None, "### Error"
            # Update choices after deletion
            choices = list_chats()
            print(f"Available chats after deletion: {choices}")  # Debug print
            return gr.update(choices=choices, value=None), None, "### New Chat"
        except Exception as e:
            print(f"Error deleting chat: {e}")
            return None, None, "### Error"

    def rename_chat(chat_selection):
        if not chat_selection:
            return gr.update(), None
        try:
            # Get chat ID mapping
            response = requests.get('http://127.0.0.1:7860/api/chats')
            chats = response.json() if response.status_code == 200 else []
            title_to_id = {chat['title']: chat['id'] for chat in chats}
            chat_id = title_to_id.get(chat_selection)
            
            if not chat_id:
                print(f"[ERROR] Could not find chat ID for title: {chat_selection}")
                return None, None
            
            print(f"Renaming chat: {chat_id}")  # Debug print
            new_title = create_title_from_message("New Title")
            response = requests.put(
                f'http://127.0.0.1:7860/api/chats/{chat_id}',
                json={'title': new_title},
                headers={'Content-Type': 'application/json'}
            )
            if response.status_code != 200:
                print(f"Error renaming chat: {response.status_code} - {response.text}")
            # Update choices after renaming
            choices = list_chats()
            print(f"Available chats after renaming: {choices}")  # Debug print
            return gr.update(choices=choices, value=new_title), f"### {new_title}"
        except Exception as e:
            print(f"Error renaming chat: {e}")
            return None, None

    def bot(history, temperature, max_new_tokens, top_p, top_k, rep_pen, chat_selection):
        if not history:
            return history
        
        try:
            # Get chat ID mapping
            response = requests.get('http://127.0.0.1:7860/api/chats')
            chats = response.json() if response.status_code == 200 else []
            title_to_id = {chat['title']: chat['id'] for chat in chats}
            chat_id = title_to_id.get(chat_selection)
            
            if not chat_id:
                print(f"[ERROR] Could not find chat ID for title: {chat_selection}")
                return history
            
            print(f"\n[DEBUG] Processing message for chat {chat_id}")
            history[-1][1] = ""
            last_response = ""
            headers = {'Content-Type': 'application/json'}
            
            title_updated = False
            current_title = None
            
            # First save the user's message and check if title update is needed
            if chat_id:
                try:
                    print(f"[DEBUG] Saving user message: '{history[-1][0][:50]}...'")
                    response = requests.post(
                        f'http://127.0.0.1:7860/api/chats/{chat_id}/messages',
                        json={'role': 'user', 'content': history[-1][0]},
                        headers=headers
                    )
                    print(f"[DEBUG] User message saved. Status: {response.status_code}")
                    
                    # Check if title update is needed
                    messages_response = requests.get(f'http://127.0.0.1:7860/api/chats/{chat_id}/messages')
                    if messages_response.status_code == 200:
                        messages = messages_response.json()
                        user_messages = [m for m in messages if m.get('role') == 'user']
                        print(f"[DEBUG] Found {len(user_messages)} user messages")
                        
                        if len(user_messages) == 1:  # First user message
                            # Generate title from the actual message content
                            new_title = create_title_from_message(history[-1][0])
                            current_title = new_title
                            print(f"[DEBUG] Starting title update to: {new_title}")
                            # Update title immediately
                            response = requests.put(
                                f'http://127.0.0.1:7860/api/chats/{chat_id}',
                                json={'title': new_title},
                                headers=headers
                            )
                            if response.status_code == 200:
                                print("[DEBUG] Title updated successfully")
                                # Update frontend
                                choices = list_chats()
                                chat_history_dropdown.update(choices=choices, value=new_title)
                                chat_title_display.update(value=f"### {new_title}")
                                title_updated = True
                except Exception as e:
                    print(f"[ERROR] Failed to save user message or update title: {e}")
            
            print("[DEBUG] Starting response generation...")
            for response in llm.generate_response(
                history[-1][0],
                history[:-1],
                temperature=temperature,
                max_new_tokens=max_new_tokens,
                top_p=top_p,
                top_k=top_k,
                repetition_penalty=rep_pen
            ):
                last_response = response
                history[-1][1] = response
                
                # Update title during generation if not yet updated
                if current_title and not title_updated:
                    try:
                        print(f"[DEBUG] Updating title during generation to: {current_title}")
                        chat_history_dropdown.update(choices=list_chats(), value=current_title)
                        chat_title_display.update(value=f"### {current_title}")
                        title_updated = True
                    except Exception as e:
                        print(f"[ERROR] Failed to update title during generation: {e}")
                
                yield history

            print("[DEBUG] Response generation complete")
            # Save the final response
            if chat_id and last_response:
                try:
                    print(f"[DEBUG] Saving assistant response")
                    response = requests.post(
                        f'http://127.0.0.1:7860/api/chats/{chat_id}/messages',
                        json={'role': 'assistant', 'content': last_response},
                        headers=headers,
                        timeout=5
                    )
                    print(f"[DEBUG] Assistant response saved. Status: {response.status_code}")
                except Exception as e:
                    print(f"[ERROR] Failed to save assistant message: {e}")
            
            # Final title update check
            if current_title and not title_updated:
                try:
                    print(f"[DEBUG] Final title update to: {current_title}")
                    chat_history_dropdown.update(choices=list_chats(), value=current_title)
                    chat_title_display.update(value=f"### {current_title}")
                except Exception as e:
                    print(f"[ERROR] Failed final title update: {e}")
            
            print("[DEBUG] Message processing complete\n")
        except Exception as e:
            print(f"[ERROR] Error in bot function: {e}")
            history[-1][1] = "Error generating response. Please try again."
            yield history

    def list_bots():
        """Get list of available bots"""
        try:
            response = requests.get(f"{BACKEND_URL}/api/bots")
            if response.status_code == 200:
                bots = response.json()
                return [bot["name"] for bot in bots]
            return []
        except Exception as e:
            print(f"Error listing bots: {e}")
            return []

    def get_bot_details(bot_name):
        """Get details for a specific bot"""
        try:
            # Find bot ID from name
            response = requests.get(f"{BACKEND_URL}/api/bots")
            if response.status_code == 200:
                bots = response.json()
                bot = next((b for b in bots if b["name"] == bot_name), None)
                if bot:
                    return bot
            return None
        except Exception as e:
            print(f"Error getting bot details: {e}")
            return None

    def create_new_bot(name, description, greeting, base_model, system_prompt, temp, max_tokens, top_p_val, top_k_val, rep_pen):
        """Create a new bot or update an existing one"""
        try:
            # Check if we're editing an existing bot
            existing_bot = get_bot_details(name)
            is_update = existing_bot is not None
            
            data = {
                "name": name,
                "description": description or "No description provided",
                "greeting_message": greeting,
                "base_model": base_model,
                "system_prompt": system_prompt,
                "parameters": {
                    "temperature": temp,
                    "max_new_tokens": max_tokens,
                    "top_p": top_p_val,
                    "top_k": top_k_val,
                    "repetition_penalty": rep_pen
                }
            }
            
            if is_update:
                # Update existing bot
                response = requests.put(
                    f"{BACKEND_URL}/api/bots/{name.lower()}",
                    json=data,
                    headers={'Content-Type': 'application/json'}
                )
            else:
                # Create new bot
                response = requests.post(
                    f"{BACKEND_URL}/api/bots",
                    json=data,
                    headers={'Content-Type': 'application/json'}
                )
            
            if response.status_code == 200:
                message = "Bot updated successfully" if is_update else "Bot created successfully"
                gr.Info(message)
                return gr.update(value=""), gr.update(choices=list_bots(), value=name)
            else:
                error_msg = response.json().get('error', 'Unknown error')
                gr.Warning(f"Failed to {'update' if is_update else 'create'} bot: {error_msg}")
                return gr.update(), gr.update()
                
        except Exception as e:
            gr.Warning(f"Error {'updating' if is_update else 'creating'} bot: {str(e)}")
            return gr.update(), gr.update()

    def delete_current_bot(bot_name):
        """Delete the currently selected bot"""
        if not bot_name or bot_name == "MIDAS40":
            return gr.Warning("Cannot delete the default MIDAS40 bot"), bot_dropdown.choices
            
        try:
            # Get bot ID from name
            bot = get_bot_details(bot_name)
            if not bot:
                return gr.Warning("Bot not found"), bot_dropdown.choices
                
            response = requests.delete(f"{BACKEND_URL}/api/bots/{bot['id']}")
            if response.status_code == 200:
                return gr.Info("Bot deleted successfully"), list_bots()
            else:
                return gr.Warning(f"Failed to delete bot: {response.json().get('error', 'Unknown error')}"), bot_dropdown.choices
        except Exception as e:
            return gr.Warning(f"Error deleting bot: {str(e)}"), bot_dropdown.choices

    def update_parameters(bot_name):
        if not bot_name:
            return [0.7, 4096, 0.95, 50, 1.1]  # Default values
            
        bot = get_bot_details(bot_name)
        if not bot:
            return None
                
        return [
            bot["parameters"]["temperature"],
            bot["parameters"]["max_new_tokens"],
            bot["parameters"]["top_p"],
            bot["parameters"]["top_k"],
            bot["parameters"]["repetition_penalty"]
        ]

    def process_message(message, history, bot_name, temp, max_tokens, top_p_val, top_k_val, rep_penalty):
        """Process a chat message using the selected bot and parameters"""
        if not message or not bot_name:
            return history
            
        try:
            # Get bot details
            bot = get_bot_details(bot_name)
            if not bot:
                history.append((message, "Error: Selected bot not found"))
                return history
                
            # Prepare the chat request
            data = {
                "messages": [{"role": "user", "content": message}],
                "bot_id": bot["id"],
                "parameters": {
                    "temperature": temp,
                    "max_new_tokens": max_tokens,
                    "top_p": top_p_val,
                    "top_k": top_k_val,
                    "repetition_penalty": rep_penalty
                }
            }
            
            # Add chat history
            for user_msg, assistant_msg in history:
                data["messages"].insert(0, {"role": "assistant", "content": assistant_msg})
                data["messages"].insert(0, {"role": "user", "content": user_msg})
            
            # Send chat request
            response = requests.post(f"{BACKEND_URL}/api/chat", json=data)
            if response.status_code != 200:
                history.append((message, f"Error: {response.json().get('error', 'Failed to process message')}"))
                return history
                
            # Add response to history
            assistant_message = response.json().get("response", "Error: No response received")
            history.append((message, assistant_message))
            
        except Exception as e:
            history.append((message, f"Error: {str(e)}"))
            
        return history

    def switch_to_bot_config():
        return {
            chat_panel: gr.update(visible=False),
            bot_config_panel: gr.update(visible=True)
        }
            
    def switch_to_chat():
        return {
            chat_panel: gr.update(visible=True),
            bot_config_panel: gr.update(visible=False)
        }
            
    def update_bot_config(bot_name):
        if not bot_name or bot_name == "Create New Bot":
            return {
                new_bot_name: gr.update(value=""),
                bot_description: gr.update(value=""),
                greeting_message: gr.update(value="Hello! How can I help you today?"),
                base_model: gr.update(value="mistral"),
                system_prompt: gr.update(value=""),
                temperature: gr.update(value=0.7),
                max_new_tokens: gr.update(value=4096),
                top_p: gr.update(value=0.95),
                top_k: gr.update(value=50),
                repetition_penalty: gr.update(value=1.1),
                save_bot_btn: gr.update(value="Create Bot")
            }
            
        bot = get_bot_details(bot_name)
        if not bot:
            return None
                
        return {
            new_bot_name: gr.update(value=bot["name"]),
            bot_description: gr.update(value=bot.get("description", "")),
            greeting_message: gr.update(value=bot.get("greeting_message", "Hello! How can I help you today?")),
            base_model: gr.update(value=bot.get("base_model", "mistral")),
            system_prompt: gr.update(value=bot["system_prompt"]),
            temperature: gr.update(value=bot["parameters"]["temperature"]),
            max_new_tokens: gr.update(value=bot["parameters"]["max_new_tokens"]),
            top_p: gr.update(value=bot["parameters"]["top_p"]),
            top_k: gr.update(value=bot["parameters"]["top_k"]),
            repetition_penalty: gr.update(value=bot["parameters"]["repetition_penalty"]),
            save_bot_btn: gr.update(value="Update Bot")
        }

    def process_response(response):
        # Process and format the response
        # Add your response processing logic here
        return response

    # Create the interface
    with gr.Blocks(
        css=CUSTOM_CSS,
        theme=gr.themes.Soft(
            primary_hue="green",
            neutral_hue="slate",
            font=["Inter", "ui-sans-serif", "system-ui"],
            text_size=gr.themes.sizes.text_md
        )
    ) as interface:
        gr.HTML("<h1 class='title'>MIDAS 2.0</h1>")
        
        with gr.Tabs() as tabs:
            with gr.Tab("Chat"):
                with gr.Row():
                    # Left sidebar
                    with gr.Column(scale=1):
                        # Bot selection
                        bot_dropdown = gr.Dropdown(
                            choices=list_bots(),
                            label="Select Bot",
                            value="MIDAS40" if "MIDAS40" in list_bots() else None
                        )
                        edit_bot_btn = gr.Button("✏️ Edit/Create New Bot")
                        
                        # Chat history
                        with gr.Accordion("Chat History", open=False):
                            chat_history_dropdown = gr.Dropdown(
                                choices=list_chats(),
                                label="Select Chat",
                                interactive=True,
                                allow_custom_value=False,
                                value=None
                            )
                            chat_title_display = gr.Markdown("### New Chat", elem_id="chat-title")
                            with gr.Row():
                                new_chat_btn = gr.Button("New", size="sm")
                                rename_btn = gr.Button("Rename", size="sm")
                                delete_btn = gr.Button("Delete", size="sm", variant="stop")
                        
                    # Main area - switchable between chat and bot config
                    with gr.Column(scale=3):
                        # Chat Panel
                        with gr.Column(visible=True) as chat_panel:
                            # Chat title and controls
                            with gr.Row():
                                chat_title_display = gr.Markdown("### New Chat", elem_id="chat-title", elem_classes="chat-title")
                                with gr.Row():
                                    rename_btn = gr.Button("Rename", size="sm")
                                    delete_btn = gr.Button("Delete", size="sm", variant="stop")

                            # Chat interface
                            chatbot = gr.Chatbot(
                                [],
                                elem_id="chatbot",
                                height=700,
                                render_markdown=True,
                                show_copy_button=True,
                                bubble_full_width=False,
                                show_share_button=False
                            )
                            with gr.Row():
                                with gr.Column(scale=20):
                                    msg = gr.Textbox(
                                        show_label=False,
                                        placeholder="Type your message here...",
                                        container=False
                                    )
                                with gr.Column(scale=1, min_width=50):
                                    submit_btn = gr.Button("Send", variant="primary")
                            with gr.Row():
                                clear = gr.Button("Clear", size="sm", scale=0.15)
                            
                        # Bot Configuration Panel
                        with gr.Column(visible=False) as bot_config_panel:
                            gr.Markdown("## Bot Configuration")
                            config_bot_dropdown = gr.Dropdown(
                                choices=["Create New Bot"] + list_bots(),
                                label="Select Bot to Edit",
                                value="Create New Bot"
                            )
                            
                            with gr.Row():
                                with gr.Column():
                                    new_bot_name = gr.Textbox(
                                        label="Bot Name",
                                        placeholder="Enter a name for your bot..."
                                    )
                                    bot_description = gr.Textbox(
                                        label="Bot Description",
                                        placeholder="Describe what this bot is designed for...",
                                        lines=2
                                    )
                                    greeting_message = gr.Textbox(
                                        label="Greeting Message",
                                        placeholder="Enter the message the bot will use to greet users...",
                                        value="Hello! How can I help you today?"
                                    )
                                    base_model = gr.Dropdown(
                                        choices=get_downloaded_models() or ["mistral", "llama2", "codellama"],
                                        label="Base Model",
                                        value=lambda: (get_downloaded_models() or ["mistral"])[0]
                                    )
                                
                            with gr.Accordion("Advanced Settings", open=False):
                                system_prompt = gr.Textbox(
                                    label="System Prompt",
                                    lines=3,
                                    placeholder="Enter the detailed system prompt for the bot..."
                                )
                                
                                with gr.Row():
                                    with gr.Column():
                                        gr.Markdown("### Response Style")
                                        temperature = gr.Slider(
                                            minimum=0.1,
                                            maximum=2.0,
                                            value=0.7,
                                            step=0.1,
                                            label="Creativity Level",
                                            info="Higher values make responses more creative but less focused"
                                        )
                                        top_p = gr.Slider(
                                            minimum=0.1,
                                            maximum=1.0,
                                            value=0.95,
                                            step=0.05,
                                            label="Response Focus",
                                            info="Lower values make responses more focused on the most likely options"
                                        )
                                        repetition_penalty = gr.Slider(
                                            minimum=1.0,
                                            maximum=2.0,
                                            value=1.1,
                                            step=0.1,
                                            label="Repetition Prevention",
                                            info="Higher values help prevent the bot from repeating itself"
                                        )
                                    with gr.Column():
                                        gr.Markdown("### Response Length")
                                        max_new_tokens = gr.Slider(
                                            minimum=64,
                                            maximum=4096,
                                            value=4096,
                                            step=64,
                                            label="Maximum Length",
                                            info="Maximum number of words in the response"
                                        )
                                        top_k = gr.Slider(
                                            minimum=1,
                                            maximum=100,
                                            value=50,
                                            step=1,
                                            label="Response Variety",
                                            info="Higher values allow for more varied word choices"
                                        )
                                
                            with gr.Row():
                                back_to_chat = gr.Button("← Back to Chat")
                                save_bot_btn = gr.Button("Create Bot", variant="primary")
                                delete_bot_btn = gr.Button("Delete Bot", variant="stop")
            
            with gr.Tab("Model Management"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Available Models")
                        models_table = gr.Dataframe(
                            headers=["Name", "Size", "Downloaded", "Loaded"],
                            value=list_available_models(),
                            interactive=False,
                            elem_classes="dark table"
                        )
                        with gr.Row():
                            refresh_btn = gr.Button("🔄 Refresh", size="sm", scale=0.2)
                            download_btn = gr.Button("⬇️ Download", size="sm", scale=0.2)
                            remove_btn = gr.Button("🗑️ Remove", size="sm", scale=0.2)
                    
                    with gr.Column():
                        gr.Markdown("### Add Custom Model")
                        model_name = gr.Textbox(label="Model Name")
                        model_size = gr.Textbox(label="Size (e.g., '3.83GB')")
                        model_type = gr.Dropdown(
                            choices=["GGUF", "GGML", "PyTorch", "SafeTensors"],
                            label="Model Type"
                        )
                        model_url = gr.Textbox(label="Download URL")
                        add_model_btn = gr.Button("➕ Add Model", size="sm", scale=0.2)
                        add_result = gr.Markdown()

                # Event handlers
                refresh_btn.click(
                    fn=refresh_model_list,
                    outputs=[models_table]
                ).then(  # Update base_model choices after refreshing model list
                    fn=update_base_model_choices,
                    outputs=[base_model]
                )
                
                def handle_download(data):
                    if not data or len(data) == 0:
                        return "Please select a model first"
                    model_name = data[0][0]  # Get name from first column
                    result = download_model(model_name)
                    refresh_model_list()
                    return result

                def handle_remove(data):
                    if not data or len(data) == 0:
                        return "Please select a model first"
                    model_name = data[0][0]  # Get name from first column
                    result = remove_model(model_name)
                    refresh_model_list()
                    return result

                download_btn.click(
                    fn=handle_download,
                    inputs=[models_table],
                    outputs=[add_result]
                ).then(  # Update base_model choices after downloading
                    fn=update_base_model_choices,
                    outputs=[base_model]
                )
                
                remove_btn.click(
                    fn=handle_remove,
                    inputs=[models_table],
                    outputs=[add_result]
                ).then(  # Update base_model choices after removing
                    fn=update_base_model_choices,
                    outputs=[base_model]
                )
                
                add_model_btn.click(
                    fn=add_custom_model,
                    inputs=[model_name, model_size, model_type, model_url],
                    outputs=[add_result]
                ).then(
                    fn=refresh_model_list,
                    outputs=[models_table]
                ).then(  # Update base_model choices after adding custom model
                    fn=update_base_model_choices,
                    outputs=[base_model]
                )

        # Event handlers for chat
        submit_btn.click(
            submit_message,
            inputs=[
                msg,
                chatbot,
                chat_history_dropdown,
                bot_dropdown,
                temperature,
                max_new_tokens,
                top_p,
                top_k,
                repetition_penalty
            ],
            outputs=[chatbot, msg],
            api_name=False
        ).then(
            lambda: None,
            None,
            [msg],
            api_name=False
        )

        msg.submit(
            submit_message,
            inputs=[
                msg,
                chatbot,
                chat_history_dropdown,
                bot_dropdown,
                temperature,
                max_new_tokens,
                top_p,
                top_k,
                repetition_penalty
            ],
            outputs=[chatbot, msg],
            api_name=False
        ).then(
            lambda: None,
            None,
            [msg],
            api_name=False
        )

        # Event handlers for bot configuration
        edit_bot_btn.click(
            switch_to_bot_config,
            None,
            [chat_panel, bot_config_panel]
        )
        
        back_to_chat.click(
            switch_to_chat,
            None,
            [chat_panel, bot_config_panel]
        )
        
        config_bot_dropdown.change(
            update_bot_config,
            inputs=[config_bot_dropdown],
            outputs=[new_bot_name, bot_description, greeting_message, base_model, system_prompt, temperature, max_new_tokens, 
                    top_p, top_k, repetition_penalty, save_bot_btn]
        )
        
        save_bot_btn.click(
            create_new_bot,
            inputs=[new_bot_name, bot_description, greeting_message, base_model, system_prompt, temperature, max_new_tokens, top_p, top_k, repetition_penalty],
            outputs=[new_bot_name, bot_dropdown]
        ).then(
            switch_to_chat,
            None,
            [chat_panel, bot_config_panel]
        )
        
        delete_bot_btn.click(
            delete_current_bot,
            inputs=[config_bot_dropdown],
            outputs=[bot_dropdown, config_bot_dropdown]
        ).then(
            switch_to_chat,
            None,
            [chat_panel, bot_config_panel]
        )

        # Chat history handlers
        new_chat_btn.click(
            create_new_chat,
            None,
            [chat_history_dropdown, chatbot, chat_title_display]
        )

        delete_btn.click(
            delete_chat,
            inputs=[chat_history_dropdown],
            outputs=[chat_history_dropdown, chatbot, chat_title_display]
        )

        rename_btn.click(
            rename_chat,
            inputs=[chat_history_dropdown],
            outputs=[chat_history_dropdown, chat_title_display]
        )

        chat_history_dropdown.change(
            load_selected_chat,
            inputs=[chat_history_dropdown],
            outputs=[chatbot, chat_title_display]
        )

    return interface

if __name__ == "__main__":
    interface = create_interface()
    interface.launch(server_name="127.0.0.1", server_port=7861, share=False)
