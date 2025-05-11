import bodyParser from 'body-parser';
import express from 'express';
import { fileURLToPath } from 'node:url';
import path, { dirname } from 'node:path';
import fs from 'node:fs';
import fileUpload from 'express-fileupload';
import PocketBase from 'pocketbase';
import { Chroma } from "@langchain/community/vectorstores/chroma";
import mime from 'mime-types';
import { MultiFileLoader } from "langchain/document_loaders/fs/multi_file";
import { PDFLoader } from "@langchain/community/document_loaders/fs/pdf";
import { PPTXLoader } from "@langchain/community/document_loaders/fs/pptx";
import { DocxLoader } from "@langchain/community/document_loaders/fs/docx";
import { RecursiveCharacterTextSplitter } from "@langchain/textsplitters";
import { ChatPromptTemplate } from "@langchain/core/prompts";
import { createRetrievalChain } from "langchain/chains/retrieval";
import { createStuffDocumentsChain } from "langchain/chains/combine_documents";
import { OllamaEmbeddings, ChatOllama, Ollama } from "@langchain/ollama";

const app = express();
const port = 3000;
const pb = new PocketBase('http://127.0.0.1:8090');

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
app.use(express.static(`${__dirname}/public`));
app.use(bodyParser.urlencoded({ extended: true }));
app.use(fileUpload({ createParentPath: true }));

// Ensure files directory
const filesDir = path.join(__dirname, 'files');
if (!fs.existsSync(filesDir)) fs.mkdirSync(filesDir, { recursive: true });

// Ollama settings
const embedder = new OllamaEmbeddings({ model: "snowflake-arctic-embed2" });
let modelList = new Ollama()
modelList = await modelList.client.list()
const textSplitter = new RecursiveCharacterTextSplitter({ chunkSize: 200, chunkOverlap: 0 });

const projects = [];

app.get("/", async (req, res) => {
    res.render("index.ejs", { register: true });
});

app.get("/home", async (req, res) => {
    try {
        // 1. Ensure user is authenticated
        const ownerId = pb.authStore.record?.id;
        if (!ownerId) {
          return res.redirect('/');
        }
    
        // 2. Fetch all projects for this user
        const records = await pb
          .collection('projects')
          .getFullList({
            filter: `owner = "${ownerId}"`,
            sort: '-created',
          });
    
        // 3. Build local projects array
        const projects = records.map(rec => ({
          icon: rec.icon,
          title: rec.title,
          desc: rec.desc,
          id: rec.id,
          model: rec.model,
        }));
    
        // 4. Render view with fetched projects
        res.render('home.ejs', { projects: projects });
      } catch (err) {
        console.error('Error fetching projects:', err);
        res.status(500).send('Could not load projects.');
      }
})

let register = true

app.get("/swap", async (req, res) => {
  if (register) {
    register = false
    res.render("index.ejs", { register })
  } else {
    register = true
    res.render("index.ejs", { register })
  }
})

app.get("/projects", async (req, res) => {
  const project = await pb.collection('projects').getOne(req.query.id)
  let chat = []
  if (project.conversation) {
    chat = JSON.parse(project.conversation)
  }
  res.render("chat.ejs", { project: project, chat: chat, models: modelList });
})

app.get("/switch-model", async (req, res) => {
  const newModel = {
    model: req.query.selected
  }
  const project = await pb.collection('projects').update(req.query.id, newModel)
  res.redirect(`/projects?id=${req.query.id}`)
})

app.post("/auth-user", async (req, res) => {
    const { email, password, confirmPassword, action } = req.body
    if (action === "register") {
        try {
            await pb.collection("users").create({
                email,
                password,
                passwordConfirm: confirmPassword
            })
            register = false
            res.render("index.ejs", { register })
        } catch (err) {
            console.log(err)
            res.render("index.ejs", { message: err.response.message })
        }
    } else {
        try {
            await pb.collection("users").authWithPassword(email, password)
            res.redirect("/home")
        } catch (err) {
            console.log(err)
            res.render("index.ejs", { message: err.response.message })
        }
    }
})

const loaderConfig = {
      ".docx": (path) => new DocxLoader(path),
      ".doc": (path) => new DocxLoader(path, {type: "doc"}),
      ".pdf": (path) => new PDFLoader(path),
      ".pptx": (path) => new PPTXLoader(path),
    };


app.post("/new-project", async (req, res) => {
  const { title, desc } = req.body;
  const ownerId = pb.authStore.record.id;
  const filesDir = path.join(__dirname, `files/${ownerId}/${title}`);

  // 1) Ensure directory exists
  if (!fs.existsSync(filesDir)) {
    fs.mkdirSync(filesDir, { recursive: true });
  }

  // 2) Save incoming uploads to disk
  const uploaded = req.files?.files;
  const filesArray = uploaded
    ? (Array.isArray(uploaded) ? uploaded : [uploaded])
    : [];
  const savedNames = [];
  for (const file of filesArray) {
    const savePath = path.join(filesDir, file.name);
    await file.mv(savePath);
    savedNames.push(file.name);
  }

  const icon = "bi-stars"

  try {
    // 3) Build record data with File instances
    const recordData = {
      owner: ownerId,
      icon,
      title,
      desc,
      sources: savedNames.map(name => {
        const fullPath = path.join(filesDir, name);
        const buffer = fs.readFileSync(fullPath);
        const contentType = mime.lookup(fullPath) || 'application/octet-stream';
        return new File([buffer], name, { type: contentType });
      }),
      model: "llama3.1:8b",
    };

    // 4) Create record (auto multipart)
    const projectRecord = await pb.collection('projects').create(recordData);
    projects.push({
        icon,
        title,
        desc,
        id: projectRecord.id
      });

    const collectionName = `${projectRecord.id}`;
    const collection = new Chroma(embedder, {
      collectionName: collectionName
    })

    // 5) Load, chunk, embed, and add documents to Chroma using MultiFileLoader
    const filePaths = savedNames.map(name => path.join(filesDir, name));

    const loader = new MultiFileLoader(filePaths, loaderConfig);
    const documents = await loader.load();
    const splits = await textSplitter.splitDocuments(documents)
    
    await collection.addDocuments(splits);

    res.redirect("/home");
  } catch (err) {
    console.error('Error creating record:', err);
    return res.status(500).send('Failed to create record.');
  }
});

app.post("/upload-file", async (req, res) => {
  const ownerId = pb.authStore.record.id;
  const projectId = req.body.projectID;
  const project = await pb.collection("projects").getOne(projectId);
  const filesDir = path.join(__dirname, `files/${ownerId}/${project.title}`);

  // 1) Ensure directory exists
  if (!fs.existsSync(filesDir)) {
    fs.mkdirSync(filesDir, { recursive: true });
  }

  // 2) Save incoming uploads to disk
  const uploaded = req.files?.files;
  const filesArray = uploaded
    ? (Array.isArray(uploaded) ? uploaded : [uploaded])
    : [];
  const savedNames = [];
  for (const file of filesArray) {
    const savePath = path.join(filesDir, file.name);
    await file.mv(savePath);
    savedNames.push(file.name);
  }

  try {
    const recordSources = {
      "sources+": savedNames.map(name => {
        const fullPath = path.join(filesDir, name);
        const buffer = fs.readFileSync(fullPath);
        const contentType = mime.lookup(fullPath) || 'application/octet-stream';
        return new File([buffer], name, { type: contentType });
      }),
    };

    // 4) Update record (auto multipart)
    const projectRecord = await pb.collection('projects').update(projectId, recordSources)

    const collectionName = `${projectRecord.id}`;
    const collection = new Chroma(embedder, {
      collectionName: collectionName
    })

    // 5) Load, chunk, embed, and add documents to Chroma using MultiFileLoader
    const filePaths = savedNames.map(name => path.join(filesDir, name));

    const loader = new MultiFileLoader(filePaths, loaderConfig);
    const documents = await loader.load();
    const splits = await textSplitter.splitDocuments(documents)
    
    await collection.addDocuments(splits);

    res.redirect(`/projects?id=${projectId}`);
  } catch (err) {
    console.error('Error creating record:', err);
    return res.status(500).send('Failed to create record.');
  }
})

class Message {
    constructor(sender, message) {
        this.sender = sender;
        this.message = message;
    }

    getSender() {
        return this.sender;
    }

    getMessage() {
        return this.message;
    }
}

app.post("/gen", async (req, res) => {
  const promptText = req.body.prompt;
  const projectID = req.body.projectID;
  
  try {
    const project = await pb.collection("projects").getOne(projectID)
    let chat = []
    if (project.conversation) {
      chat = JSON.parse(project.conversation)
    }

    chat.push(new Message("user", promptText))

    // 1) Initialize vector store for this project
    const vectorStore = new Chroma(embedder, { collectionName: projectID });

    // 1) Prepare a prompt template with a `{context}` slot
    const questionAnsweringPrompt = ChatPromptTemplate.fromMessages([
      [
        "system",
        "You are provided multiple context items that are related to the prompt you have to answer. Use the following pieces of context to respond to the prompt at the end.\n\n{context}\n",
      ],
      ["human", "{input}"],
    ]);

    // 2) Create the combine-documents chain (it’s a Runnable)
    const LLM = new ChatOllama({ model: project.model });
    const combineDocsChain = await createStuffDocumentsChain({
      llm: LLM,          // your ChatOllama instance
      prompt: questionAnsweringPrompt,  // the template above
    });

    // 3) Get your retriever
    const retriever = vectorStore.asRetriever();

    // 4) Finally, build the RetrievalChain correctly
    const chain = await createRetrievalChain({
      combineDocsChain,
      retriever,
    });

    // 5) Run it
    const response = await chain.invoke({ input: promptText });
    const answer   = response.answer;

    // 4) Record chat and render
    // (Assumes you pass `chat` into your template for rendering)
    chat.push({ sender: project.model.split(":")[0], message: answer });

    // 5) Store chat in PocketBase
    const chatData = {
      "conversation": JSON.stringify(chat)
    }
    await pb.collection("projects").update(projectID, chatData)
    
    res.render('chat.ejs', { project: project, chat: chat, models: modelList });
  } catch (err) {
    console.error('Error in /gen:', err);
    res.status(500).send('Chat generation failed.');
  }
});

app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});