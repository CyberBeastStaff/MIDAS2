import gradio as gr
from backend.system_monitor import get_system_info
from backend.llm_interface import LLMInterface

# Custom CSS for MIDAS 2.0 theme
CUSTOM_CSS = """
:root {
    --primary-color: #00ff9d;
    --background-dark: #1a1a1a;
    --background-light: #2d2d2d;
    --text-color: #ffffff;
    --border-color: #3d3d3d;
}

body {
    background-color: var(--background-dark) !important;
    color: var(--text-color) !important;
}

.gradio-container {
    background-color: var(--background-dark) !important;
    color: var(--text-color) !important;
    max-width: 100% !important;
    padding: 0 !important;
}

.chat-message {
    padding: 1rem;
    margin: 0.5rem 0;
    border-radius: 8px;
    background-color: var(--background-light) !important;
    border: 1px solid var(--border-color) !important;
    color: var(--text-color) !important;
}

.message-wrap {
    background-color: var(--background-light) !important;
    border: 1px solid var(--border-color) !important;
    color: var(--text-color) !important;
}

.message-wrap .bot {
    background-color: var(--background-light) !important;
}

.message-wrap .user {
    background-color: var(--primary-color) !important;
}

button.primary {
    background-color: var(--primary-color) !important;
    color: var(--background-dark) !important;
}

.sidebar-container {
    min-width: 300px !important;
    max-width: 350px !important;
    position: sticky !important;
    top: 0 !important;
    height: 100vh !important;
    align-self: flex-start !important;
}

.sidebar {
    background-color: var(--background-light) !important;
    border-radius: 10px;
    padding: 1rem;
    margin: 0.5rem;
    color: var(--text-color) !important;
    max-height: calc(100vh - 2rem);
    overflow-y: auto;
    width: auto !important;
    height: calc(100vh - 2rem) !important;
}

.sidebar > * {
    width: 100% !important;
}

.sidebar .gr-box {
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

.sidebar .gr-accordion {
    border: 1px solid var(--border-color) !important;
    border-radius: 8px !important;
    background-color: var(--background-dark) !important;
    margin: 0.5rem 0 !important;
}

.sidebar .gr-accordion-header {
    padding: 0.75rem !important;
    border-radius: 7px !important;
    background-color: var(--background-dark) !important;
    border: none !important;
    transition: all 0.2s ease-in-out !important;
}

.sidebar .gr-accordion-header:hover {
    background-color: rgba(0, 255, 157, 0.1) !important;
}

.sidebar .gr-accordion-content {
    padding: 0.75rem !important;
    background-color: var(--background-dark) !important;
    border-top: 1px solid var(--border-color) !important;
}

.sidebar h3 {
    color: var(--primary-color) !important;
    margin: 0 0 0.5rem 0 !important;
    font-size: 1.5rem !important;
}

.sidebar h4 {
    color: var(--text-color) !important;
    margin: 1rem 0 0.5rem 0 !important;
    font-size: 1rem !important;
    opacity: 0.9;
}

.sidebar .gr-form {
    background-color: transparent !important;
    border: none !important;
    gap: 0.5rem !important;
}

.sidebar .gr-input,
.sidebar .gr-dropdown {
    background-color: var(--background-dark) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 6px !important;
    padding: 0.5rem !important;
    margin: 0.25rem 0 !important;
}

.sidebar .gr-input:focus,
.sidebar .gr-dropdown:focus {
    border-color: var(--primary-color) !important;
    box-shadow: 0 0 0 1px var(--primary-color) !important;
}

.sidebar .gr-button {
    background-color: var(--background-dark) !important;
    border: 1px solid var(--border-color) !important;
    color: var(--text-color) !important;
    border-radius: 6px !important;
    padding: 0.5rem 1rem !important;
    transition: all 0.2s ease-in-out !important;
}

.sidebar .gr-button:hover {
    border-color: var(--primary-color) !important;
    color: var(--primary-color) !important;
    background-color: rgba(0, 255, 157, 0.1) !important;
}

/* Custom scrollbar for sidebar */
.sidebar::-webkit-scrollbar {
    width: 8px;
}

.sidebar::-webkit-scrollbar-track {
    background: var(--background-dark);
    border-radius: 4px;
}

.sidebar::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 4px;
}

.sidebar::-webkit-scrollbar-thumb:hover {
    background: var(--primary-color);
}

/* Chat interface styling */
.chat-container {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    background-color: var(--background-dark) !important;
    padding: 0 1rem;
    gap: 1rem;
}

.chat-messages {
    flex-grow: 1;
    overflow-y: auto;
    padding: 1rem;
    background-color: var(--background-dark) !important;
    border-radius: 10px;
    margin-bottom: 1rem;
}

/* Remove default Gradio chatbot styling */
.chat-messages > div {
    border: none !important;
    background: transparent !important;
    padding: 0 !important;
}

.chat-messages .wrapper {
    border: none !important;
    background: transparent !important;
    padding: 0 !important;
}

/* Message styling */
.message-wrap {
    margin: 0.75rem 0 !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 0.75rem !important;
    border: none !important;
    background: transparent !important;
}

.message-wrap > div {
    border: none !important;
    background: transparent !important;
}

.message-wrap .bot,
.message-wrap .user {
    padding: 1rem !important;
    border-radius: 12px !important;
    max-width: 85% !important;
    width: fit-content !important;
    line-height: 1.5 !important;
    font-size: 1rem !important;
    white-space: pre-wrap !important;
    box-shadow: none !important;
}

.message-wrap .bot {
    background-color: var(--background-light) !important;
    border: 1px solid var(--border-color) !important;
    border-top-left-radius: 4px !important;
    margin-right: auto !important;
    color: var(--text-color) !important;
}

.message-wrap .user {
    background-color: var(--primary-color) !important;
    color: var(--background-dark) !important;
    border-top-right-radius: 4px !important;
    margin-left: auto !important;
    font-weight: 500 !important;
}

/* Remove any additional Gradio wrappers */
.message-wrap .user-message,
.message-wrap .bot-message {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

.message-wrap .user-message > div,
.message-wrap .bot-message > div {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* Code block styling */
.message-wrap .bot pre,
.message-wrap .bot code {
    background-color: var(--background-dark) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 6px !important;
    padding: 0.5rem !important;
    margin: 0.5rem 0 !important;
    font-family: 'Consolas', 'Monaco', monospace !important;
    font-size: 0.9rem !important;
    overflow-x: auto !important;
    color: var(--text-color) !important;
}

/* Input area styling */
.chat-input {
    background-color: var(--background-light) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 10px;
    padding: 0.75rem;
    margin-bottom: 1rem;
    display: flex;
    gap: 0.5rem;
    align-items: center;
}

.chat-input textarea {
    background-color: var(--background-dark) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 8px !important;
    padding: 0.75rem !important;
    min-height: 40px !important;
    max-height: 200px !important;
    resize: none !important;
    font-size: 1rem !important;
    line-height: 1.5 !important;
    color: var(--text-color) !important;
    transition: all 0.2s ease-in-out !important;
    box-shadow: none !important;
}

.chat-input textarea:focus {
    border-color: var(--primary-color) !important;
    outline: none !important;
    box-shadow: 0 0 0 2px rgba(0, 255, 157, 0.1) !important;
}

.chat-input textarea::placeholder {
    color: rgba(255, 255, 255, 0.5) !important;
}

/* Button styling */
.chat-input .send-btn,
.chat-input .control-btn {
    min-width: 40px !important;
    height: 40px !important;
    border-radius: 20px !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 1.2rem !important;
    border: none !important;
    cursor: pointer !important;
    transition: all 0.2s ease-in-out !important;
}

.chat-input .send-btn {
    background-color: var(--primary-color) !important;
    color: var(--background-dark) !important;
    font-weight: bold !important;
}

.chat-input .control-btn {
    background-color: var(--background-dark) !important;
    color: var(--text-color) !important;
    border: 1px solid var(--border-color) !important;
}

.chat-input .send-btn:hover {
    transform: scale(1.05) !important;
    box-shadow: 0 0 10px rgba(0, 255, 157, 0.3) !important;
}

.chat-input .control-btn:hover {
    transform: scale(1.05) !important;
    border-color: var(--primary-color) !important;
    color: var(--primary-color) !important;
}

/* Scrollbar styling */
.chat-messages::-webkit-scrollbar {
    width: 10px !important;
}

.chat-messages::-webkit-scrollbar-track {
    background: var(--background-dark) !important;
    border-radius: 10px !important;
}

.chat-messages::-webkit-scrollbar-thumb {
    background: var(--background-light) !important;
    border: 2px solid var(--background-dark) !important;
    border-radius: 10px !important;
    transition: background-color 0.2s ease !important;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
    background: var(--primary-color) !important;
}

/* Firefox scrollbar styling */
.chat-messages {
    scrollbar-width: thin !important;
    scrollbar-color: var(--background-light) var(--background-dark) !important;
}

/* Ensure smooth scrolling */
.chat-messages {
    scroll-behavior: smooth !important;
}

/* Override default Gradio theme colors */
:root {
    --primary-color: #00ff9d;
    --background-dark: #1a1a1a;
    --background-light: #2d2d2d;
    --text-color: #ffffff;
    --border-color: #3d3d3d;
}

body {
    background-color: var(--background-dark) !important;
    color: var(--text-color) !important;
}

.gradio-container {
    background-color: var(--background-dark) !important;
    color: var(--text-color) !important;
    max-width: 100% !important;
    padding: 0 !important;
}

.dark {
    background-color: var(--background-dark) !important;
    color: var(--text-color) !important;
}

.dark input, 
.dark textarea,
.dark .gr-box,
.dark .gr-input {
    background-color: var(--background-light) !important;
    border-color: var(--border-color) !important;
    color: var(--text-color) !important;
}

.dark input, 
.dark textarea,
.dark .gr-box,
.dark .gr-input {
    box-shadow: none !important;
}

.dark button:not(.send-btn) {
    background-color: var(--background-light) !important;
    border-color: var(--border-color) !important;
    color: var(--text-color) !important;
}

.dark button:hover:not(.send-btn) {
    border-color: var(--primary-color) !important;
    color: var(--primary-color) !important;
}

.dark .gr-button-primary {
    background-color: var(--primary-color) !important;
    color: var(--background-dark) !important;
}

.dark .gr-button-primary:hover {
    background-color: var(--primary-color) !important;
    filter: brightness(1.1) !important;
}

.dark .gr-box {
    border-color: var(--border-color) !important;
}

.dark select {
    background-color: var(--background-light) !important;
    border-color: var(--border-color) !important;
    color: var(--text-color) !important;
}

.dark option {
    background-color: var(--background-dark) !important;
    color: var(--text-color) !important;
}

/* Override Gradio's default chatbot styling */
.wrap.svelte-byatnx {
    background: transparent !important;
    border: none !important;
}

.message-wrap .user,
.message-wrap .user > div,
.message-wrap .user span,
.message-wrap .user p {
    background-color: var(--primary-color) !important;
    color: var(--background-dark) !important;
}

.message-wrap .user *:not(code):not(pre) {
    background-color: var(--primary-color) !important;
    color: var(--background-dark) !important;
}

/* Additional overrides for Gradio's nested elements */
.message > div,
.message-wrap > div > div,
.message-wrap .user-message > div > div,
.message-wrap .user > div > div {
    background: transparent !important;
    border: none !important;
}

.message p,
.message span {
    background: inherit !important;
    color: inherit !important;
}

/* Hide Gradio footer */
footer {
    display: none !important;
}

.footer {
    display: none !important;
}

.gradio-footer {
    display: none !important;
}

/* Hide any potential footer variants */
div[class*="footer"],
div[class*="Footer"] {
    display: none !important;
}

"""

def create_interface():
    llm = LLMInterface()
    available_models = [model.name for model in llm.get_available_models()]
    
    with gr.Blocks(css=CUSTOM_CSS, theme=gr.themes.Base(primary_hue="green", neutral_hue="slate", font=["Inter", "ui-sans-serif", "system-ui"])) as interface:
        with gr.Row(equal_height=True):
            # Left sidebar - wrapped in a container for proper width control
            with gr.Column(scale=1, elem_classes="sidebar-container"):
                with gr.Column(elem_classes="sidebar"):
                    gr.Markdown("### MIDAS 2.0")
                    gr.Markdown("#### Model Selection")
                    model_dropdown = gr.Dropdown(
                        choices=available_models,
                        value=available_models[0] if available_models else None,
                        label="",
                        container=True
                    )
                    
                    with gr.Accordion("System Status", open=True):
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
            with gr.Column(scale=4, elem_classes="chat-container"):
                chatbot = gr.Chatbot(
                    height="70vh",
                    show_label=False,
                    container=False,
                    elem_classes=["chat-messages", "dark"]
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
        
        def user(user_message, history):
            return "", history + [[user_message, None]]

        def bot(history, temperature, max_new_tokens, top_p, top_k, rep_pen):
            if not history:
                return history
            
            history[-1][1] = ""
            for response in llm.generate_response(
                history[-1][0], 
                history[:-1],
                temperature=temperature,
                max_new_tokens=max_new_tokens,
                top_p=top_p,
                top_k=top_k,
                repetition_penalty=rep_pen
            ):
                history[-1][1] = response
                yield history

        def change_model(model_name):
            if llm.load_model(model_name.lower()):
                return f"Model: {model_name}\nStatus: Active ●"
            return f"Failed to load {model_name}"

        def refresh_system_information():
            return get_system_info()

        # Event handlers
        msg.submit(user, [msg, chatbot], [msg, chatbot], queue=False).then(
            bot, [chatbot, temperature, max_new_tokens, top_p, top_k, rep_pen], chatbot
        )
        submit.click(user, [msg, chatbot], [msg, chatbot], queue=False).then(
            bot, [chatbot, temperature, max_new_tokens, top_p, top_k, rep_pen], chatbot
        )
        clear.click(lambda: None, None, chatbot, queue=False)
        model_dropdown.change(change_model, model_dropdown, system_info)
        refresh_sys_info.click(refresh_system_information, None, system_info)

    return interface
