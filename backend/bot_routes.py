from flask import Blueprint, request, jsonify
from .bot_manager import Bot, BotManager

bot_routes = Blueprint('bot_routes', __name__)
bot_manager = BotManager()

@bot_routes.route('/api/bots', methods=['GET'])
def list_bots():
    """List all available bots"""
    try:
        bots = bot_manager.list_bots()
        return jsonify(bots)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bot_routes.route('/api/bots/<bot_id>', methods=['GET'])
def get_bot(bot_id):
    """Get a specific bot's details"""
    try:
        bot = bot_manager.get_bot(bot_id)
        if bot is None:
            return jsonify({"error": "Bot not found"}), 404
        return jsonify(bot.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bot_routes.route('/api/bots', methods=['POST'])
def create_bot():
    """Create a new bot"""
    try:
        data = request.get_json()
        
        # Generate a simple ID from the name
        bot_id = data['name'].lower().replace(' ', '_')
        
        bot = Bot(
            id=bot_id,
            name=data['name'],
            system_prompt=data['system_prompt'],
            base_model=data['base_model'],
            parameters=data['parameters']
        )
        
        bot = bot_manager.create_bot(bot)
        return jsonify(bot.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bot_routes.route('/api/bots/<bot_id>', methods=['PUT'])
def update_bot(bot_id):
    """Update a bot's properties"""
    try:
        data = request.get_json()
        bot = bot_manager.update_bot(
            bot_id,
            name=data.get('name'),
            system_prompt=data.get('system_prompt'),
            base_model=data.get('base_model'),
            parameters=data.get('parameters')
        )
        return jsonify(bot.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bot_routes.route('/api/bots/<bot_id>', methods=['DELETE'])
def delete_bot(bot_id):
    """Delete a bot"""
    try:
        bot_manager.delete_bot(bot_id)
        return jsonify({"message": "Bot deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
