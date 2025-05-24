
# Ultrabook

#### A self-hosted alternative to Google's [NotebookLM](https://notebooklm.google/)

### Table of contents
- [Installation](#installation)
- [FAQ](#faq)
- [Roadmap](#roadmap)

#### About
Ultrabook uses [Ollama](https://ollama.com/), [LangChain](https://www.langchain.com/) and [Chroma](https://trychroma.com/) to create a RAG pipeline that lets you chat to your documents! It is a great tool to accelerate research and learning; for example, you might get your chosen model to quiz you on a topic or create the basic structure of essays or other writing, all while keeping your data on device and private.
## Installation

> [!IMPORTANT]
> Requires [Ollama](https://ollama.com/) and [Python](https://www.python.org/downloads/) to be installed

1. Clone the repo:
```bash
  git clone https://github.com/diva-in-STEM/ultrabook.git
```

2. Install required packages:
```bash
  cd ultrabook
  pip install -r requirements.txt
```

3. Make the Django database migrations:
```bash
  py manage.py migrate
```

4. Serve the Django server:
```bash
  py manage.py runserver
```

5. Done! 🎉
## FAQ

#### Question 1

How do I change the default model?
> Support for environment variables is coming soon!

#### Question 2

Where are the tests?
> Software test are on the way! I am new to Django so please be patient


## Roadmap

- Environment variables to control default values

- ~~Tests~~

- ~~Add model pulling to selection dropdown~~

- ~~Website loading & embedding~~

- Podcast feature

- Scripts to automate starting server

- Create services for Windows, Linux and MacOS to run automatically

- Containerize
