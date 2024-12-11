from flask import Blueprint, request, jsonify, Response
from .bot_manager import Bot, BotManager
import logging
import re
import json

logger = logging.getLogger(__name__)
bot_routes = Blueprint('bot_routes', __name__)
bot_manager = BotManager()

def sanitize_bot_id(name: str) -> str:
    """Convert a bot name to a valid bot ID"""
    # Remove special characters and convert spaces to underscores
    bot_id = re.sub(r'[^a-zA-Z0-9\s]', '', name)
    bot_id = bot_id.strip().replace(' ', '_').lower()
    return bot_id

@bot_routes.route('/api/bots', methods=['GET'])
def list_bots():
    """List all available bots"""
    try:
        bots = bot_manager.list_bots()
        return jsonify(bots)
    except Exception as e:
        logger.error(f"Error listing bots: {str(e)}")
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
        logger.error(f"Error getting bot {bot_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bot_routes.route('/api/bots', methods=['POST'])
def create_bot():
    """Create a new bot"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        required_fields = ['name', 'system_prompt', 'base_model', 'parameters']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        required_params = ['temperature', 'max_new_tokens', 'top_p', 'top_k', 'repetition_penalty']
        missing_params = [param for param in required_params if param not in data['parameters']]
        if missing_params:
            return jsonify({"error": f"Missing required parameters: {', '.join(missing_params)}"}), 400

        # Generate bot ID from name
        bot_id = sanitize_bot_id(data['name'])
        if not bot_id:
            return jsonify({"error": "Invalid bot name"}), 400

        # Create the bot
        bot = Bot(
            id=bot_id,
            name=data['name'],
            system_prompt=data['system_prompt'],
            base_model=data['base_model'],
            parameters=data['parameters']
        )
        
        bot = bot_manager.create_bot(bot)
        logger.info(f"Created new bot: {bot_id}")
        return jsonify(bot.to_dict())
    except ValueError as e:
        logger.warning(f"Invalid bot creation request: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating bot: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bot_routes.route('/api/bots/<bot_id>', methods=['PUT'])
def update_bot(bot_id):
    """Update an existing bot"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate required fields
        required_fields = ['name', 'description', 'greeting_message', 'base_model', 'system_prompt', 'parameters']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
        
        # Validate parameters
        required_params = ['temperature', 'max_new_tokens', 'top_p', 'top_k', 'repetition_penalty']
        if not all(param in data['parameters'] for param in required_params):
            return jsonify({"error": "Missing required parameters"}), 400
        
        # Update the bot
        bot_manager.update_bot(
            bot_id=bot_id,
            name=data['name'],
            description=data['description'],
            greeting_message=data['greeting_message'],
            base_model=data['base_model'],
            system_prompt=data['system_prompt'],
            parameters=data['parameters']
        )
        
        return jsonify({"message": "Bot updated successfully"})
    except Exception as e:
        logger.error(f"Error updating bot {bot_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bot_routes.route('/api/bots/<bot_id>', methods=['DELETE'])
def delete_bot(bot_id):
    """Delete a bot"""
    try:
        bot_manager.delete_bot(bot_id)
        logger.info(f"Deleted bot: {bot_id}")
        return jsonify({"message": "Bot deleted successfully"})
    except ValueError as e:
        logger.warning(f"Invalid bot deletion request: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error deleting bot: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bot_routes.route('/api/bots/<bot_id>/chat', methods=['POST'])
def chat_with_bot(bot_id):
    """Chat with a specific bot"""
    try:
        data = request.get_json()
        message = data.get('message')
        parameters = data.get('parameters', {})
        
        if not message:
            return jsonify({"error": "No message provided"}), 400
            
        # Get the bot
        bot = bot_manager.get_bot(bot_id)
        if bot is None:
            return jsonify({"error": "Bot not found"}), 404
            
        # Generate response
        try:
            def generate():
                for token in bot.generate_response(
                    messages=[{"role": "user", "content": message}],
                    parameters=parameters
                ):
                    if isinstance(token, dict):
                        yield f"data: {json.dumps(token)}\n\n"
                    else:
                        yield f"data: {json.dumps({'token': token})}\n\n"
                        
            return Response(generate(), mimetype='text/event-stream')
            
        except Exception as e:
            logger.error(f"Error generating response from bot {bot_id}: {e}")
            return jsonify({"error": f"Failed to generate response: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"Error in chat endpoint for bot {bot_id}: {e}")
        return jsonify({"error": str(e)}), 500
