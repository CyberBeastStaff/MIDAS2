from flask import Blueprint, jsonify, request
from .chat_manager import ChatManager

chat_bp = Blueprint('chat', __name__)
chat_manager = ChatManager()

@chat_bp.route('/chats', methods=['GET'])
def list_chats():
    chats = chat_manager.list_chats()
    return jsonify(chats)

@chat_bp.route('/chats', methods=['POST'])
def create_chat():
    data = request.get_json()
    title = data.get('title', 'New Chat')
    chat_id = chat_manager.create_chat(title)
    return jsonify({"id": chat_id})

@chat_bp.route('/chats/<chat_id>', methods=['GET'])
def get_chat(chat_id):
    chat = chat_manager.get_chat(chat_id)
    if chat:
        return jsonify(chat)
    return jsonify({"error": "Chat not found"}), 404

@chat_bp.route('/chats/<chat_id>/messages', methods=['POST'])
def add_message(chat_id):
    data = request.get_json()
    role = data.get('role')
    content = data.get('content')
    
    if not role or not content:
        return jsonify({"error": "Missing role or content"}), 400
    
    success = chat_manager.add_message(chat_id, role, content)
    if success:
        return jsonify({"status": "success"})
    return jsonify({"error": "Failed to add message"}), 400

@chat_bp.route('/chats/<chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    success = chat_manager.delete_chat(chat_id)
    if success:
        return jsonify({"status": "success"})
    return jsonify({"error": "Failed to delete chat"}), 400

@chat_bp.route('/chats/<chat_id>/title', methods=['PUT'])
def update_chat_title(chat_id):
    data = request.get_json()
    new_title = data.get('title')
    
    if not new_title:
        return jsonify({"error": "Missing title"}), 400
    
    success = chat_manager.update_chat_title(chat_id, new_title)
    if success:
        return jsonify({"status": "success"})
    return jsonify({"error": "Failed to update chat title"}), 400
