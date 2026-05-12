# Install Ollama
brew install ollama

# Pull all models (this takes a while — do it overnight)
ollama pull sqlcoder:7b
ollama pull codellama:7b
ollama pull deepseek-coder:6.7b
ollama pull mistral:7b
ollama pull phi3:mini

# Start Ollama server
ollama serve


python3 -m venv venv
source venv/bin/activate

pip install ollama pandas sqlglot rouge-score matplotlib seaborn requests tqdm