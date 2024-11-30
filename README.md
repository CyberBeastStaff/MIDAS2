# MIDAS 2.0 - Machine Intelligence Deployment and Automation System

MIDAS 2.0 is a powerful, privacy-focused platform for deploying and interacting with state-of-the-art language models locally. It provides a user-friendly interface for advanced AI interactions while maintaining complete data privacy and control.

## Features

### Core Capabilities
- Local Language Model Execution
- Dynamic Model Management
- Advanced Generation Controls
- Real-time System Monitoring
- Privacy-First Design

### Model Management
- Automatic Model Download
- Dynamic Model Loading/Unloading
- Persistent Model Selection
- Multiple Model Support

### Generation Controls
- Temperature Control
- Response Length Management
- Top-P and Top-K Sampling
- Repetition Penalty
- Conversation History Management

### System Features
- GPU Acceleration Support
- Real-time Resource Monitoring
- Efficient Memory Management
- Error Handling and Recovery

## Supported Models

Currently supported models include:
- Llama-2-7B-Chat (Q4 Quantized)
- Llama-2-13B-Chat (Q4 Quantized)

Additional models can be easily integrated through the model management system.

## Technical Requirements

### Core Dependencies
- Python 3.8+
- PyTorch
- llama-cpp-python
- Gradio 4.19.2+
- CUDA (optional, for GPU acceleration)

### System Requirements
- 8GB+ RAM (16GB+ recommended)
- 10GB+ Storage Space
- NVIDIA GPU (optional, for acceleration)

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install torch llama-cpp-python gradio requests tqdm
   ```
3. Run the application:
   ```bash
   python app.py
   ```

## Usage

1. Launch MIDAS 2.0
2. Select a language model from the dropdown
3. Configure generation parameters (optional)
4. Enter your query and click Submit
5. Monitor system resources in the side panel

## Architecture

MIDAS 2.0 follows a modular architecture:

- Frontend (Gradio Interface)
- Backend
  - Model Management
  - LLM Interface
  - System Monitoring

## Privacy & Security

MIDAS 2.0 is designed with privacy in mind:
- All processing happens locally
- No data leaves your system
- No external API calls (except for model downloads)
- Secure model storage and management

## License

MIT License - See LICENSE file for details
