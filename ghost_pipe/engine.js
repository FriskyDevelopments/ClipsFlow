require('dotenv').config();
const fs = require('fs');
const express = require('express');
const axios = require('axios');
const { spawn } = require('child_process');
const { GoogleGenerativeAI } = require('@google/generative-ai');
const { File } = require('megajs');

const GDRIVE_MASTER = "gdrive:CΛTΛLOG_MΛSTER";
const QUEUE_FILE = require('os').homedir() + "/ghost_queue.txt";

function getModel() {
    const genai = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
    return genai.getGenerativeModel({ 
        model: 'gemini-3.1-pro',
        generationConfig: { responseMimeType: "application/json" }
    });
}

async function streamToFile(url, target) {
    return new Promise((resolve) => {
        axios({ method: 'get', url, responseType: 'stream' }).then(res => {
            const rclone = spawn('rclone', ['rcat', '-v', target]);
            res.data.pipe(rclone.stdin);
            rclone.on('close', (code) => {
                if (code === 0) console.log(`[ ⧨ ] SECURED: ${target.split('/').pop()}`);
                resolve();
            });
        }).catch(e => { console.log(`[!] Stream Err: ${e.message}`); resolve(); });
    });
}

async function processFile(link) {
    try {
        const rd = await axios.post('https://api.real-debrid.com/rest/1.0/unrestrict/link', 
            `link=${link}`, { headers: { 'Authorization': `Bearer ${process.env.RD_API_TOKEN}` } });
        const prompt = "Librarian mode. Return JSON: {\"name\": \"[TAG] CleanName.ext\", \"path\": \"Folder/Sub\"}";
        const ai = await getModel().generateContent(prompt + " File: " + rd.data.filename);
        const meta = JSON.parse(ai.response.text());
        await streamToFile(rd.data.download, `${GDRIVE_MASTER}/${meta.path}/${meta.name}`);
    } catch (e) { console.log(`[!] Failed: ${e.message}`); }
}

async function handleDrop(link) {
    if (!link.trim()) return;
    try {
        if (link.includes('/folder/')) {
            console.log("[+] MEGA Folder Detected. Ripping...");
            const folder = File.fromURL(link);
            await folder.loadAttributes();
            for (const child of folder.children) {
                if (!child.directory) await processFile(await child.link());
            }
        } else {
            await processFile(link);
        }
    } catch (e) {
        console.log(`[!] Error Crítico: La llave de MEGA es inválida o el link está mocho.`);
        throw e;
    }
}

const app = express();
app.use(express.json());

let busy = false;

app.post('/drop', async (req, res) => {
    const { link } = req.body;
    if (!link) return res.status(400).json({ error: 'Missing link' });
    if (busy) return res.status(429).json({ error: 'Engine is busy processing another drop' });
    
    busy = true;
    try {
        await handleDrop(link);
        res.json({ status: 'success', message: 'Drop processed completely.' });
    } catch (e) {
        res.status(500).json({ error: e.message });
    } finally {
        busy = false;
    }
});

app.get('/', (req, res) => {
    res.send("GHOST PIPE V3.1 is ONLINE");
});

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => {
    console.log("╒═════════════════════════════════════════════════╕");
    console.log("│ ⧨  G H O S T   P I P E   V 3 . 1   O N L I N E   │");
    console.log(`│   HTTP Server listening on port ${PORT}          │`);
    console.log("╘═════════════════════════════════════════════════╛");
});
