import axios from 'axios';
import bodyParser from 'body-parser';
import e from 'express';
import { ChromaClient, OllamaEmbeddingFunction } from "chromadb";
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';
import fileUpload from 'express-fileupload';
import fs from 'node:fs';

const app = e();
const port = 3000;

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
app.use(e.static(`${__dirname}/public`));
app.use(bodyParser.urlencoded({ extended: true }));
app.use(fileUpload({
    createParentPath: true,
}));

const client = new ChromaClient({
    path: "http://iceberg:8000",
});

const embedder = new OllamaEmbeddingFunction({
    url: "http://iceberg:11434/api/embeddings",
    model: "mxbai-embed-large",
});

const collection = await client.getOrCreateCollection({
    name: 'documents10',
    embeddingFunction: embedder,  // Embedding function is passed here
});

const ollamaURL = "http://iceberg:11434/api";
const model = "llama3.2";

app.get("/", async (req, res) => {
    res.render("index.ejs");
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

const messages = [];

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