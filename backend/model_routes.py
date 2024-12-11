from flask import Blueprint, request, jsonify
from .model_manager import ModelManager
import logging

logger = logging.getLogger(__name__)
model_routes = Blueprint('model_routes', __name__)
model_manager = ModelManager()

@model_routes.route('/api/models', methods=['GET'])
def list_models():
    """List all available models"""
    try:
        models = model_manager.list_models()
        return jsonify([{
            "id": model.name.lower(),
            "name": model.name,
            "size": model.size,
            "type": model.type,
            "is_downloaded": model.is_downloaded,
            "is_loaded": model.is_loaded
        } for model in models])
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        return jsonify({"error": str(e)}), 500

@model_routes.route('/api/models/downloaded', methods=['GET'])
def list_downloaded_models():
    """List downloaded models"""
    try:
        models = model_manager.get_downloaded_models()
        return jsonify([{
            "id": model.name.lower(),
            "name": model.name,
            "size": model.size,
            "type": model.type,
            "is_loaded": model.is_loaded
        } for model in models])
    except Exception as e:
        logger.error(f"Error listing downloaded models: {str(e)}")
        return jsonify({"error": str(e)}), 500

@model_routes.route('/api/models/<model_id>/download', methods=['POST'])
def download_model(model_id):
    """Download a specific model"""
    try:
        force = request.json.get('force', False) if request.json else False
        success = model_manager.download_model(model_id, force=force)
        if success:
            return jsonify({"message": "Model downloaded successfully"})
        return jsonify({"error": "Failed to download model"}), 400
    except Exception as e:
        logger.error(f"Error downloading model {model_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@model_routes.route('/api/models/<model_id>', methods=['DELETE'])
def remove_model(model_id):
    """Remove a specific model"""
    try:
        success = model_manager.remove_model(model_id)
        if success:
            return jsonify({"message": "Model removed successfully"})
        return jsonify({"error": "Model not found"}), 404
    except Exception as e:
        logger.error(f"Error removing model {model_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@model_routes.route('/api/models', methods=['POST'])
def add_model():
    """Add a new model"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        required_fields = ['name', 'size', 'type', 'url']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        model = model_manager.add_model(
            name=data['name'],
            size=data['size'],
            type=data['type'],
            url=data['url']
        )

        return jsonify({
            "id": model.name.lower(),
            "name": model.name,
            "size": model.size,
            "type": model.type,
            "is_downloaded": model.is_downloaded,
            "is_loaded": model.is_loaded
        })
    except Exception as e:
        logger.error(f"Error adding model: {str(e)}")
        return jsonify({"error": str(e)}), 500
