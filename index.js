import axios from 'axios';
import bodyParser from 'body-parser';
import e from 'express';

const app = e()
const port = 3000

app.use(bodyParser.urlencoded({extended: true}))

const ollamaURL = "http://iceberg:11434/api"
const model = "llama3.2"

app.get("/", async (req, res) => {
    res.render("index.ejs")
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

app.listen(port, () => {
    console.log(`Server running at ${port}`)
})