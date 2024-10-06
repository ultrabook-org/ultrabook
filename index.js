import axios from 'axios';
import bodyParser from 'body-parser';
import e from 'express';
import multer from 'multer';
import { ChromaClient, OllamaEmbeddingFunction } from "chromadb";

const app = e()
const port = 3000

app.use(bodyParser.urlencoded({extended: true}))

const storage = multer.memoryStorage()
const fileFilter = (req, file, cb) => {
    if (file.mimetype === 'text/plain') { // checking the MIME type of the uploaded file
        cb(null, true);
    } else {
        cb(null, false);
    }
}

const upload = multer({ fileFilter, storage })

const client = new ChromaClient({
    path: "http://iceberg:8000"
});

const embedder = new OllamaEmbeddingFunction({
    url: "http://iceberg:11434/api/embeddings",
    model: "mxbai-embed-large"
})

const collection = await client.getCollection({
    name: 'documents8',
    embeddingFunction: embedder
})

const ollamaURL = "http://iceberg:11434/api"
const model = "llama3.2"

app.get("/", async (req, res) => {
    res.render("index.ejs")
})

app.get("/ingest", async (req, res) => {
    res.render("ingest.ejs")
})

app.post("/gen", async(req, res) => {
    try {
        const result = await axios.post(`${ollamaURL}/generate`, {
            model: model,
            prompt: req.body.prompt,
            stream: false
        }).then((response) => {
            res.render("index.ejs", { result: response.data.response })
        })
    } catch(error) {
        res.render("index.ejs", { result: error.response.data })
    }
})

app.post("/ingest", upload.single('file'), async (req, res) => {
    const documents = req.file.buffer.toString().split('. ')
    for(const i in documents) {
        console.log(documents[i])
        const embed = await collection.add({ids: [i.toString()],documents: documents[i]})
    }
    res.render("ingest.ejs", {hasData: true})
})

app.post("/docChat", async (req, res) => {
    const prompt = req.body.prompt
    try {
        const bestDoc = await collection.query({
            queryTexts: [prompt],
            nResults: 3
        })
        const data = bestDoc.documents[0]
        console.log(data)
        axios.post(`${ollamaURL}/generate`, {
            model: model,
            prompt: `Using this information: ${data}. Respond to this prompt: ${prompt} Do not make up information or use any data from your training. DO NOT HALLUCINATE.`,
            stream: false
        }).then((response) => {
            res.render("ingest.ejs", {hasData: true, result: response.data.response})
        })
    } catch(error) {
        res.render("ingest.ejs", {hasData: true, result: error.response.data})
    }
})

app.listen(port, () => {
    console.log(`Server running at ${port}`)
})