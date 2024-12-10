from flask import Blueprint, jsonify, request
from .chat_manager import ChatManager
import logging

chat_routes = Blueprint('chat_routes', __name__)
chat_manager = ChatManager()

# Configure logging
logger = logging.getLogger(__name__)

@chat_routes.route('/api/chats', methods=['GET'])
def list_chats():
    try:
        chats = chat_manager.list_chats()
        return jsonify(chats)
    except Exception as e:
        logger.error(f"Error listing chats: {e}")
        return jsonify({"error": str(e)}), 500

@chat_routes.route('/api/chats', methods=['POST'])
def create_chat():
    try:
        data = request.get_json()
        title = data.get('title', 'New Chat')
        chat_id = chat_manager.create_chat(title)
        return jsonify({"id": chat_id, "title": title})
    except Exception as e:
        logger.error(f"Error creating chat: {e}")
        return jsonify({"error": str(e)}), 500

@chat_routes.route('/api/chats/<chat_id>', methods=['GET'])
def get_chat(chat_id):
    try:
        chat = chat_manager.get_chat(chat_id)
        if chat is None:
            return jsonify({"error": "Chat not found"}), 404
        return jsonify(chat)
    except Exception as e:
        logger.error(f"Error getting chat {chat_id}: {e}")
        return jsonify({"error": str(e)}), 500

@chat_routes.route('/api/chats/<chat_id>/messages', methods=['POST'])
def add_message(chat_id):
    try:
        data = request.get_json()
        role = data.get('role')
        content = data.get('content')
        
        if not role or not content:
            return jsonify({"error": "Missing role or content"}), 400
        
        success = chat_manager.add_message(chat_id, role, content)
        if not success:
            return jsonify({"error": "Failed to add message"}), 500
        
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error adding message to chat {chat_id}: {e}")
        return jsonify({"error": str(e)}), 500

@chat_routes.route('/api/chats/<chat_id>/messages', methods=['GET'])
def get_messages(chat_id):
    try:
        chat = chat_manager.get_chat(chat_id)
        if chat is None:
            return jsonify({"error": "Chat not found"}), 404
        return jsonify(chat.get("messages", []))
    except Exception as e:
        logger.error(f"Error getting messages for chat {chat_id}: {e}")
        return jsonify({"error": str(e)}), 500

@chat_routes.route('/api/chats/<chat_id>', methods=['PUT'])
def update_chat(chat_id):
    try:
        data = request.get_json()
        title = data.get('title')
        if not title:
            return jsonify({"error": "Missing title"}), 400
        
        success = chat_manager.update_chat_title(chat_id, title)
        if not success:
            return jsonify({"error": "Chat not found"}), 404
            
        return jsonify({"status": "success", "id": chat_id, "title": title})
    except Exception as e:
        logger.error(f"Error updating chat {chat_id}: {e}")
        return jsonify({"error": str(e)}), 500

@chat_routes.route('/api/chats/<chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    try:
        success = chat_manager.delete_chat(chat_id)
        if not success:
            return jsonify({"error": "Chat not found"}), 404
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error deleting chat {chat_id}: {e}")
        return jsonify({"error": str(e)}), 500
