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

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.system_monitor import get_system_info
from backend.llm_interface import LLMInterface

# Load external CSS file
with open('frontend/static/styles.css', 'r') as f:
    CUSTOM_CSS = f.read()

CUSTOM_CSS += """
.title {
    font-size: 2.5em !important;
    font-weight: 700 !important;
    text-align: center;
    margin: 20px 0 !important;
    padding: 10px;
    color: rgb(34, 197, 94) !important;  /* Neon green color */
    text-shadow: 0 0 10px rgba(34, 197, 94, 0.3);  /* Subtle glow effect */
    border-bottom: 2px solid rgb(34, 197, 94);
}

.sidebar {
    padding: 20px;
    background-color: var(--background-fill-primary);
}

.chat-title {
    margin: 0;
    padding: 10px;
    display: flex;
    align-items: center;
}

.chat-title-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px;
    border-bottom: 1px solid var(--border-color-primary);
}

.chat-title-row button {
    margin-left: 10px;
}

.chat-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    max-height: 100vh;
    background-color: var(--background-fill-primary);
}

.chat-messages {
    flex-grow: 1;
    overflow-y: auto;
    padding: 20px;
    margin-bottom: 20px;
}

.chat-input {
    padding: 10px 20px;
    background-color: var(--background-fill-secondary);
    border-top: 1px solid var(--border-color-primary);
}

.chat-textbox {
    border-radius: 8px;
}

.send-btn {
    border-radius: 8px;
    padding: 8px;
    min-width: 40px;
}

.control-btn {
    border-radius: 8px;
    padding: 8px;
    min-width: 40px;
}
"""

def create_interface():
    llm = LLMInterface()
    available_models = [model.name for model in llm.get_available_models()]
    
    def create_new_chat():
        try:
            response = requests.post('http://127.0.0.1:7860/api/chats',
                                  json={'title': 'New Chat'},
                                  headers={'Content-Type': 'application/json'})
            if response.status_code == 200:
                chat_data = response.json()
                choices = list_chats()
                return (
                    gr.update(choices=choices, value=f"New Chat ({chat_data['id']})"),
                    [[None, "Hello! I'm MIDAS, your AI assistant. How can I help you today?"]],
                    "### New Chat"
                )
            else:
                print(f"Error creating chat: {response.status_code} - {response.text}")
                return None, None, None
        except Exception as e:
            print(f"Error creating chat: {e}")
            return None, None, None

    def list_chats():
        try:
            response = requests.get('http://127.0.0.1:7860/api/chats')
            if response.status_code == 200:
                chats = response.json()
                # Sort chats by last modified time, newest first
                return [f"{chat['title']} ({chat['id']})" for chat in reversed(chats)]
            print(f"[ERROR] Failed to list chats: {response.status_code}")
            return []
        except Exception as e:
            print(f"[ERROR] Error listing chats: {e}")
            return []

    def refresh_chat_list():
        print("[DEBUG] Refreshing chat list")
        choices = list_chats()
        print(f"[DEBUG] Updated chat list: {choices}")
        return gr.update(choices=choices)

    def create_title_from_message(message, max_words=3):
        """Create a concise 2-3 word title from the user's message"""
        try:
            # Remove special characters and extra spaces
            clean_msg = ' '.join(''.join(c if c.isalnum() or c.isspace() else ' ' for c in message).split())
            
            # Extract key words (skip common words)
            common_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
                'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can', 'me', 'my',
                'mine', 'you', 'your', 'yours', 'he', 'him', 'his', 'she', 'her', 'hers', 'it', 'its',
                'we', 'us', 'our', 'ours', 'they', 'them', 'their', 'theirs', 'this', 'that', 'these',
                'those', 'what', 'which', 'who', 'whom', 'whose', 'when', 'where', 'why', 'how'
            }
            
            # Split into words and filter out common words and short words
            words = [word for word in clean_msg.split() 
                    if word.lower() not in common_words 
                    and len(word) > 2]  # Skip very short words
            
            # Take first 2-3 meaningful words
            title_words = words[:max_words]
            
            # Capitalize each word
            title = ' '.join(word.capitalize() for word in title_words)
            
            # If no meaningful words found or title too short, use first few words of message
            if len(title) < 3:
                # Take first few words of original message
                title = ' '.join(message.split()[:max_words]).capitalize()
            
            # Ensure title isn't too long
            if len(title) > 30:
                title = title[:27] + "..."
            
            print(f"[DEBUG] Generated title from message: {title}")
            return title
        except Exception as e:
            print(f"[ERROR] Failed to generate title from message: {e}")
            return f"Chat {datetime.now().strftime('%I:%M %p')}"

    def update_chat_title_async(chat_id, new_title, update_queue):
        """Update chat title in a separate thread"""
        print(f"[DEBUG] Async title update started for chat {chat_id}")
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.put(
                f'http://127.0.0.1:7860/api/chats/{chat_id}',
                json={'title': new_title},
                headers=headers
            )
            print(f"[DEBUG] Async title update response: {response.status_code}")
            
            if response.status_code == 200:
                print("[DEBUG] Title updated successfully in background")
                # Put the update info in the queue
                update_queue.put(('title_update', new_title, chat_id))
            else:
                print(f"[ERROR] Failed to update title: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"[ERROR] Error in async title update: {e}")

    def update_chat_title(chat_id, new_title):
        """Update chat title and refresh the dropdown"""
        print(f"[DEBUG] Updating chat {chat_id} title to: {new_title}")
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.put(
                f'http://127.0.0.1:7860/api/chats/{chat_id}',
                json={'title': new_title},
                headers=headers
            )
            print(f"[DEBUG] Title update response: {response.status_code}")
            
            if response.status_code == 200:
                print("[DEBUG] Title updated successfully, refreshing chat list")
                choices = list_chats()
                return gr.update(choices=choices, value=f"{new_title} ({chat_id})")
            else:
                print(f"[ERROR] Failed to update title: {response.status_code} - {response.text}")
                return gr.update()
        except Exception as e:
            print(f"[ERROR] Error updating chat title: {e}")
            return gr.update()

    def load_chat(chat_selection):
        if not chat_selection:
            print("No chat selected")  # Debug print
            return None
        try:
            chat_id = chat_selection.split('(')[-1].rstrip(')')
            print(f"Loading chat: {chat_id}")  # Debug print
            response = requests.get(f'http://127.0.0.1:7860/api/chats/{chat_id}')
            if response.status_code != 200:
                print(f"Error loading chat: {response.status_code} - {response.text}")
                return None
            chat_data = response.json()
            history = []
            messages = chat_data.get('messages', [])
            
            # Sort messages by timestamp if available
            if messages and 'timestamp' in messages[0]:
                messages.sort(key=lambda x: x.get('timestamp', 0))
            
            for i, msg in enumerate(messages):
                role = msg.get('role')
                content = msg.get('content', '')
                
                if role == 'user':
                    history.append([content, None])
                elif role == 'assistant':
                    if history and history[-1][1] is None:
                        history[-1][1] = content
                    else:
                        history.append([None, content])
            
            print(f"Loaded chat history: {history}")  # Debug print
            return history
        except Exception as e:
            print(f"Error loading chat: {e}")
            return None

    def delete_chat(chat_selection):
        if not chat_selection:
            return gr.update(), None, "### New Chat"
        try:
            chat_id = chat_selection.split('(')[-1].rstrip(')')
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
            chat_id = chat_selection.split('(')[-1].rstrip(')')
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
            return gr.update(choices=choices, value=f"{new_title} ({chat_id})"), f"### {new_title}"
        except Exception as e:
            print(f"Error renaming chat: {e}")
            return None, None

    def bot(history, temperature, max_new_tokens, top_p, top_k, rep_pen, chat_selection):
        if not history:
            return history
        
        try:
            chat_id = chat_selection.split('(')[-1].rstrip(')') if chat_selection else None
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
                                choices = list_chats()
                                chat_history_dropdown.update(choices=choices, value=f"{new_title} ({chat_id})")
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
                        chat_history_dropdown.update(choices=list_chats(), value=f"{current_title} ({chat_id})")
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
                    chat_history_dropdown.update(choices=list_chats(), value=f"{current_title} ({chat_id})")
                    chat_title_display.update(value=f"### {current_title}")
                except Exception as e:
                    print(f"[ERROR] Failed final title update: {e}")
            
            print("[DEBUG] Message processing complete\n")
        except Exception as e:
            print(f"[ERROR] Error in bot function: {e}")
            history[-1][1] = "Error generating response. Please try again."
            yield history

    def change_model(model_name):
        if llm.load_model(model_name.lower()):
            return f"Model: {model_name}\nStatus: Active ●"
        return f"Failed to load {model_name}"

    def refresh_system_information():
        return get_system_info()

    def get_chat_title(chat_selection):
        """Extract title from chat selection"""
        if not chat_selection:
            return ""
        # Remove the chat ID in parentheses
        return chat_selection.rsplit(' (', 1)[0]

    def user(user_message, history, chat_selection):
        try:
            print(f"\n[DEBUG] Processing user message: {user_message[:50]}...")
            current_title = "### New Chat"
            dropdown_update = gr.update()
            headers = {'Content-Type': 'application/json'}
            base_url = 'http://127.0.0.1:7860/api'
            
            if not chat_selection:
                print("[DEBUG] No chat selected, creating new chat")
                dropdown_update, history, current_title = create_new_chat()
                chat_selection = dropdown_update.value
            
            chat_id = chat_selection.split('(')[-1].rstrip(')')
            print(f"[DEBUG] Using chat ID: {chat_id}")
            
            # Get current chat data
            chat_response = requests.get(f'{base_url}/chats/{chat_id}')
            if chat_response.status_code != 200:
                print(f"[ERROR] Failed to get chat: {chat_response.status_code}")
                print(f"[ERROR] Response: {chat_response.text}")
                return "", history + [[user_message, None]], dropdown_update, current_title
                
            chat_data = chat_response.json()
            messages = chat_data.get('messages', [])
            user_messages = [m for m in messages if m.get('role') == 'user']
            print(f"[DEBUG] Found {len(user_messages)} existing user messages")
            
            # Add new message
            print("[DEBUG] Adding message to chat history")
            message_response = requests.post(
                f'{base_url}/chats/{chat_id}/messages',
                json={'role': 'user', 'content': user_message},
                headers=headers
            )
            if message_response.status_code != 200:
                print(f"[ERROR] Failed to save message: {message_response.status_code}")
                print(f"[ERROR] Response: {message_response.text}")
                return "", history + [[user_message, None]], dropdown_update, current_title
            
            # Update title if this is the first message
            if len(user_messages) == 0:
                new_title = create_title_from_message(user_message)
                print(f"[DEBUG] Generated new title: {new_title}")
                
                # Update title in backend
                print(f"[DEBUG] Updating title in backend")
                title_response = requests.put(
                    f'{base_url}/chats/{chat_id}',
                    json={'title': new_title},
                    headers=headers
                )
                
                if title_response.status_code == 200:
                    print("[DEBUG] Title updated successfully")
                    # Update frontend
                    choices = list_chats()
                    dropdown_update = gr.update(choices=choices, value=f"{new_title} ({chat_id})")
                    current_title = f"### {new_title}"
                else:
                    print(f"[ERROR] Failed to update title: {title_response.status_code}")
                    print(f"[ERROR] Response: {title_response.text}")
            
            print(f"[DEBUG] Returning updates - Title: {current_title}")
            return "", history + [[user_message, None]], dropdown_update, current_title
            
        except Exception as e:
            print(f"[ERROR] Error in user function: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return "", history + [[user_message, None]], gr.update(), "### New Chat"

    with gr.Blocks(
        css=CUSTOM_CSS,
        theme=gr.themes.Base(primary_hue="green", neutral_hue="slate", font=["Inter", "ui-sans-serif", "system-ui"]),
        title="MIDAS 2.0"
    ) as interface:
        # Create initial chat
        initial_response = requests.post('http://127.0.0.1:7860/api/chats',
                                      json={'title': 'New Chat'},
                                      headers={'Content-Type': 'application/json'})
        initial_chat_id = initial_response.json()['id'] if initial_response.status_code == 200 else None
        initial_choices = list_chats()
        
        # Left sidebar
        with gr.Row():
            with gr.Column(scale=1, elem_classes="sidebar"):
                gr.Markdown("# MIDAS 2.0", elem_classes="title")
                
                # Chat History Section
                new_chat_btn = gr.Button("+ New Chat")
                chat_history_dropdown = gr.Dropdown(
                    choices=initial_choices,
                    value=f"New Chat ({initial_chat_id})" if initial_chat_id else None,
                    label="Chat History",
                    container=True
                )
                
                gr.Markdown("#### Model Selection")
                model_dropdown = gr.Dropdown(
                    choices=available_models,
                    value=available_models[0] if available_models else None,
                    label="",
                    container=True
                )
                
                with gr.Accordion("System Status", open=False):
                    system_info = gr.TextArea(
                        value=get_system_info(),
                        label="",
                        interactive=False,
                        container=True
                    )
                    refresh_sys_info = gr.Button("↻ Refresh", size="sm")
                
                with gr.Accordion("Generation Settings", open=False):
                    temperature = gr.Slider(
                        minimum=0.1, maximum=2.0, value=0.7, step=0.1,
                        label="Temperature",
                        container=True
                    )
                    max_new_tokens = gr.Slider(
                        minimum=50, maximum=2000, value=1000, step=50,
                        label="Max Length",
                        container=True
                    )
                    top_p = gr.Slider(
                        minimum=0.1, maximum=1.0, value=0.95, step=0.05,
                        label="Top P",
                        container=True
                    )
                    top_k = gr.Slider(
                        minimum=1, maximum=100, value=50, step=1,
                        label="Top K",
                        container=True
                    )
                    rep_pen = gr.Slider(
                        minimum=1.0, maximum=2.0, value=1.2, step=0.1,
                        label="Repetition Penalty",
                        container=True
                    )

            # Main chat area
            with gr.Column(scale=4):
                # Chat title and action buttons row
                with gr.Row(elem_classes="chat-title-row"):
                    chat_title_display = gr.Markdown("### New Chat")
                    delete_btn = gr.Button("Delete", size="sm", variant="secondary")
                    rename_btn = gr.Button("Rename", size="sm", variant="secondary")

                # Chat interface
                chatbot = gr.Chatbot(
                    value=[[None, "Hello! I'm MIDAS, your AI assistant. How can I help you today?"]],
                    height="70vh",
                    show_label=False,
                    container=False,
                    elem_classes=["chat-messages", "dark"],
                    bubble_full_width=False,
                    render_markdown=True
                )
                
                with gr.Row(elem_classes="chat-input"):
                    with gr.Column(scale=10):
                        msg = gr.Textbox(
                            show_label=False,
                            placeholder="Type your message here...",
                            container=False,
                            elem_classes="chat-textbox"
                        )
                    with gr.Column(scale=1, min_width=50):
                        clear = gr.Button("↺", variant="secondary", elem_classes="control-btn")
                    with gr.Column(scale=1, min_width=50):
                        submit = gr.Button("→", variant="primary", elem_classes="send-btn")
                
                with gr.Row(elem_classes="chat-controls"):
                    pass
        
        def create_new_chat():
            try:
                response = requests.post('http://127.0.0.1:7860/api/chats',
                                      json={'title': 'New Chat'},
                                      headers={'Content-Type': 'application/json'})
                if response.status_code == 200:
                    chat_data = response.json()
                    choices = list_chats()
                    return (
                        gr.update(choices=choices, value=f"New Chat ({chat_data['id']})"),
                        [[None, "Hello! I'm MIDAS, your AI assistant. How can I help you today?"]],
                        "### New Chat"
                    )
                else:
                    print(f"Error creating chat: {response.status_code} - {response.text}")
                    return None, None, None
            except Exception as e:
                print(f"Error creating chat: {e}")
                return None, None, None

        # Event handlers
        new_chat_btn.click(
            create_new_chat,
            outputs=[chat_history_dropdown, chatbot, chat_title_display]
        )

        msg.submit(
            user,
            [msg, chatbot, chat_history_dropdown],
            [msg, chatbot, chat_history_dropdown, chat_title_display]
        ).then(
            bot,
            [chatbot, temperature, max_new_tokens, top_p, top_k, rep_pen, chat_history_dropdown],
            chatbot
        )

        submit.click(
            user,
            [msg, chatbot, chat_history_dropdown],
            [msg, chatbot, chat_history_dropdown, chat_title_display]
        ).then(
            bot,
            [chatbot, temperature, max_new_tokens, top_p, top_k, rep_pen, chat_history_dropdown],
            chatbot
        )

        chat_history_dropdown.change(
            lambda x: (load_chat(x), f"### {get_chat_title(x)}") if x else (None, "### New Chat"),
            inputs=[chat_history_dropdown],
            outputs=[chatbot, chat_title_display]
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

        clear.click(lambda: None, None, chatbot, queue=False)
        model_dropdown.change(change_model, model_dropdown, system_info)
        refresh_sys_info.click(refresh_system_information, None, system_info)

    return interface

if __name__ == "__main__":
    interface = create_interface()
    interface.launch(server_name="127.0.0.1", server_port=7861, share=False)
