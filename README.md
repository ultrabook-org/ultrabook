
# Ultrabook

#### A self-hosted alternative to Google's [NotebookLM](https://notebooklm.google/)

### Table of contents
- [Installation](#installation)
- [Roadmap](#roadmap)

#### About
Ultrabook uses [Ollama](https://ollama.com/), [LangChain](https://www.langchain.com/) and [Chroma](https://trychroma.com/) to create a RAG pipeline that lets you chat to your documents! It is a great tool to accelerate research and learning; for example, you might get your chosen model to quiz you on a topic or create the basic structure of essays or other writing, all while keeping your data on device and private.
## Installation

> [!IMPORTANT]
> Requires [Ollama](https://ollama.com/) and [Python](https://www.python.org/downloads/) to be installed. Do not use a reasoning model when setting the `PODCAST_MODEL` environment  variable.

1. Clone the repo:
```bash
  git clone https://github.com/diva-in-STEM/ultrabook.git
```

2. Install required packages:
```bash
  cd ultrabook
  pip install -r requirements.txt
```

3. Set environment variables (see .env.example for the necessary values.) Get a secret key using the commands below:
```bash
  python3 manage.py shell

  from django.core.management.utils import get_random_secret_key
  print(get_random_secret_key())
```

4. Make the Django database migrations:
```bash
  py manage.py migrate
```

5. Serve the Django server:
```bash
  py manage.py runserver
```

6. Done! 🎉

## Roadmap

- ~~Environment variables to control default values~~

- ~~Tests~~

- ~~Add model pulling to selection dropdown~~

- ~~Website loading & embedding~~

- ~~Podcast feature~~ ⚠️ Needs work. DO NOT USE A REASONING MODEL
    - Improve podcast UI (waveform/blob to indicate speaking, controls)
    - Loading spinner when podcast is being generated
    - 'Jump-in' feature (see (RealtimeSTT)[https://github.com/KoljaB/RealtimeSTT])

- Scripts to automate starting server

- Create services for Windows, Linux and MacOS to run automatically

- Containerize
