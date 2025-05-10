import axios from 'axios';
import bodyParser from 'body-parser';
import e from 'express';
import { fileURLToPath } from 'node:url';
import path, { dirname } from 'node:path';
import fs from 'node:fs';
import fileUpload from 'express-fileupload';
import PocketBase from 'pocketbase';
import { ChromaClient, OllamaEmbeddingFunction } from "chromadb";
import mime from 'mime-types';
import { MultiFileLoader } from "langchain/document_loaders/fs/multi_file";
import { PDFLoader } from "@langchain/community/document_loaders/fs/pdf";
import { PPTXLoader } from "@langchain/community/document_loaders/fs/pptx";
import { DocxLoader } from "@langchain/community/document_loaders/fs/docx";
import { RecursiveCharacterTextSplitter } from "@langchain/textsplitters";

const app = e();
const port = 3000;
const pb = new PocketBase('http://127.0.0.1:8090');

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
app.use(e.static(`${__dirname}/public`));
app.use(bodyParser.urlencoded({ extended: true }));
app.use(fileUpload({
    createParentPath: true,
}));

const filesDir = path.join(__dirname, 'files');
if (!fs.existsSync(filesDir)) {
  fs.mkdirSync(filesDir, { recursive: true });
}

const ollamaURL = "http://localhost:11434/api";
const model = "llama3.1:8b";

const client = new ChromaClient({
  path: "http://localhost:8000",
});

const embedder = new OllamaEmbeddingFunction({
  url: "http://localhost:11434/api/embeddings",
  model: "snowflake-arctic-embed2",
});

const textSplitter = new RecursiveCharacterTextSplitter({
  chunkSize: 200,
  chunkOverlap: 0,
});

const projects = [];

app.get("/", async (req, res) => {
    res.render("index.ejs", { register: true });
});

app.get("/ingest", async (req, res) => {
    res.render("ingest.ejs");
});

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

  try {
    // 3) Build record data with File instances
    const recordData = {
      owner: ownerId,
      title,
      desc,
      sources: savedNames.map(name => {
        const fullPath = path.join(filesDir, name);
        const buffer = fs.readFileSync(fullPath);
        const contentType = mime.lookup(fullPath) || 'application/octet-stream';
        return new File([buffer], name, { type: contentType });
      }),
    };

    // 4) Create record (auto multipart)
    const projectRecord = await pb.collection('projects').create(recordData);
    projects.push({
        icon: 'heart',
        title,
        desc,
        files: savedNames,
        id: projectRecord.id
      });

    const collectionName = `${projectRecord.id}`; // Use title and ID for collection name
    const collection = await client.getOrCreateCollection({
      name: collectionName,
      embeddingFunction: embedder,
    });

    // 5) Load, chunk, embed, and add documents to Chroma using MultiFileLoader
    const filePaths = savedNames.map(name => path.join(filesDir, name));

    const loaderConfig = {
      ".docx": (path) => new DocxLoader(path),
      ".doc": (path) => new DocxLoader(path, {type: "doc"}),
      ".pdf": (path) => new PDFLoader(path),
      ".pptx": (path) => new PPTXLoader(path),
    };

    const loader = new MultiFileLoader(filePaths, loaderConfig);
    const documents = await loader.load();

    let docID = 0
    for (const chunk of documents) {
      await collection.add({
        documents: [chunk.pageContent],
        ids: [`chunk_${docID}`],
      });
      docID += 1
    }
    res.redirect("/home");
  } catch (err) {
    console.error('Error creating record:', err);
    return res.status(500).send('Failed to create record.');
  }
});

app.get("/projects", async (req, res) => {
  console.log(req.query.id)
  res.redirect("/home")
})

app.post("/gen", async (req, res) => {
	try {
		const prompt = req.body.prompt;
		messages.push(new Message("user", prompt));
		const result = await axios
			.post(`${ollamaURL}/generate`, {
				model: model,
				prompt: prompt,
				stream: false,
			})
			.then((response) => {
				const reply = response.data.response;
				messages.push(new Message("system", reply));
				res.render("index.ejs", { messages: messages });
			});
	} catch (error) {
		messages.push(new Message("system", error.response.data));
		res.render("index.ejs", { messages: messages });
	}
});

app.post("/ingest", async (req, res) => {
    const file = req.files.myFile;
    const path = `${__dirname}/files/${file.name}`;
    const nameList = file.name.split(".");
    const extension = nameList[nameList.length - 1];
    const allowedExtensions = ['txt', 'pdf'];

    if (!allowedExtensions.includes(extension)) {
        return res.status(422).send("Invalid FileType");
    }

    file.mv(path, async (err) => {
        if (err) {
            return res.status(500).send(err);
        }
        
        fs.readFile(path, 'utf8', async (err, data) => {
            if (err) {
                return res.status(500).send(err);
            }
            
            // Split the document into paragraphs based on line breaks
            const paragraphs = data.split(/\n\s*\n/); // Regex to split by blank lines

            // Embed and store each paragraph in the collection
            for (const [i, paragraph] of paragraphs.entries()) {
                if (paragraph.trim()) {
                    await collection.add({
                        ids: [`para_${i}`],
                        documents: [paragraph],
                    });
                }
            }
             
            res.render("ingest.ejs", { hasData: true });
        });
    });
});

const docMessages = [];

app.post("/docChat", async (req, res) => {
    const prompt = req.body.prompt;
    docMessages.push(new Message('user', prompt));
    
    try {
        // Retrieve top 5 matching documents to provide a broader context
        const bestDocs = await collection.query({
            queryTexts: [prompt],
            nResults: 5,  // Increase nResults to broaden context
        });

        // Check if relevant documents are being retrieved
        console.log("Retrieved Documents:", bestDocs.documents);
        
        // Combine top retrieved documents into a single context
        const combinedDoc = bestDocs.documents.map(doc => doc).join("\n\n");

        // Revised generation prompt to make it clear that the model should use the retrieved context only
        const generationPrompt = `Context: \n\n${combinedDoc}\n\nBased on the above context, respond to this question: "${prompt}". Your answer should use only the information provided in the context above. Do not speculate or add any information beyond what is given in the context.`;

        const response = await axios.post(`${ollamaURL}/generate`, {
            model: model,
            prompt: generationPrompt,
            stream: false,
        });

        // Log response for debugging purposes
        console.log("Generated Response:", response.data.response);

        // Add the model's response to the chat history and render it on the page
        docMessages.push(new Message('system', response.data.response));
        res.render("ingest.ejs", { hasData: true, messages: docMessages });
        
    } catch (error) {
        console.error("Error:", error);
        res.render("ingest.ejs", { hasData: true, result: error.response?.data || "An error occurred." });
    }
});


app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});