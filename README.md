# keep.ai
A FOSS, self-hosted replacement for [Google's NotebookLM](https://notebooklm.google/) for those who want more control

### Table of contents
 - [How it works](#how-it-works)
 - [Installation](#installation-guide)
 - [Roadmap](#todo)

### How it works:
Keep uses [Ollama](https://ollama.com/) to interact with large language models, [Chroma](https://trychroma.com/) as the vector database (used for storing uploaded documents in a way LLMs can understand,) [PocketBase](https://pocketbase.io/) as the backend for user authentication and project management and [LangChain](https://www.langchain.com/) libraries to connect it all together!

Start by creating your account then make your first project. Either upload files at creation or do it while chatting (or both.) Then, chat away with the model of your choosing!
> [!Important]
> keep is barebones (very batteries not included) for now (11/05/2025) so there is no way to pull models from the web interface. However, you just need to run the `ollama pull {model name}` command from a terminal to add new ones

### Installation Guide:
1. Clone the repository:
```bash
git clone https://github.com/diva-in-STEM/keep.ai.git
```

2. Create a directory for Chroma
```bash
cd local-llm
mkdir chroma_data
```

3. Run Chroma with specified directory
> [!Important]
> You will need to provide your own Chroma, Ollama and PocketBase installations. Please refer to their documentation for more!
```bash
chroma run --path ./chroma_data
```

4. Pull the default model (I will add an option to change this)
```bash
ollama pull llama3.1:8b
```

5. Install (see PB docs) and start PocketBase (Windows - for other operating systems, follow PB documentation)
```bash
cd 'your-pocketbase-directory'
./pocketbase.exe serve
```

6. Create new 'projects' collection - only needed once
From the PocketBase admin dashboard:
 - Click 'New Collection'
 - Call it 'projects'
 - Add a relation field called owner from the users collection
 - Add a text field called icon
 - Add a text field called title
 - Add a text field called desc
 - Add a text field called conversation
 - Add a text field called model
 - Add a file field called sources
 - Click the 'Single' dropdown and set it to 'Multiple'

7. Install project dependencies
```bash
# Inside local-llm directory
npm install
```

8. Start the server!
```bash
node index.js
```

### TODO:
In no particular order:
 - Change default model
 - Add model pulling to web interface
 - Add a way to sign out/change users from home screen
 - Improve site navigation with back button
 - Use environment variable for URLs
 - Add website embedding
 - Add podcast feature
 - Add script to start all services automatically
 - Add install script
 - Docker container!
