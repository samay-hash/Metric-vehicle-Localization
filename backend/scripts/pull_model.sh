#!/bin/bash
# Run this on the AWS EC2 terminal to pull the LLaVA model for the local VLM
echo "Pulling LLaVA Vision model into the local Ollama container..."
sudo docker compose exec ollama ollama run llava "Hello, is the model loaded?"
echo "Model loaded successfully!"
