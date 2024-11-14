## Local LLM 🤖
A self hosted way of interacting with AI models with a built in RAG pipeline.

### How it works:
This app utilises an instance of [ChromaDB](https://docs.trychroma.com/) and [Ollama](https://ollama.com/) as a backend. The app is currently hardcoded to use llama3.2 and mxbai-embed-large models (to chat and embed docunents respectively) and all vectors are stored in the ChromaDB.

### TODO:
 - Allow users to change address of Ollama/ChromaDB
 - Allow users to change models used
 - Chat context (LangChain??)
