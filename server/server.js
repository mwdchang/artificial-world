import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const WORLDS_DIR = path.resolve(__dirname, '../worlds');
const PORT = process.env.PORT || 3001;

async function ensureWorldsDir() {
  try {
    await fs.mkdir(WORLDS_DIR, { recursive: true });
  } catch (err) {
    console.error('Failed to create worlds directory:', err);
  }
}

function setCorsHeaders(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

function sendJson(res, statusCode, data) {
  setCorsHeaders(res);
  res.writeHead(statusCode, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(data));
}

function sanitizeWorldName(name) {
  // Allow alphanumeric, dashes, underscores, spaces
  return name.replace(/[^\w\s-]/gi, '').trim();
}

const server = http.createServer(async (req, res) => {
  setCorsHeaders(res);

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const pathname = url.pathname;

  // GET /api/worlds
  if (req.method === 'GET' && pathname === '/api/worlds') {
    try {
      await ensureWorldsDir();
      const files = await fs.readdir(WORLDS_DIR);
      const worldNames = files
        .filter((file) => file.endsWith('.json'))
        .map((file) => file.replace(/\.json$/, ''));
      sendJson(res, 200, worldNames);
    } catch (err) {
      sendJson(res, 500, { error: 'Failed to read worlds', details: err.message });
    }
    return;
  }

  // Matches /api/worlds/:world
  const worldMatch = pathname.match(/^\/api\/worlds\/([^/]+)$/);
  if (worldMatch) {
    const rawWorldName = decodeURIComponent(worldMatch[1]);
    const worldName = sanitizeWorldName(rawWorldName);

    if (!worldName) {
      sendJson(res, 400, { error: 'Invalid world name' });
      return;
    }

    const filePath = path.join(WORLDS_DIR, `${worldName}.json`);

    // GET /api/worlds/:world
    if (req.method === 'GET') {
      try {
        const fileContent = await fs.readFile(filePath, 'utf-8');
        const data = JSON.parse(fileContent);
        sendJson(res, 200, data);
      } catch (err) {
        if (err.code === 'ENOENT') {
          sendJson(res, 404, { error: `World "${worldName}" not found` });
        } else {
          sendJson(res, 500, { error: 'Failed to read world file', details: err.message });
        }
      }
      return;
    }

    // POST /api/worlds/:world
    if (req.method === 'POST') {
      let body = '';
      req.on('data', (chunk) => {
        body += chunk;
      });

      req.on('end', async () => {
        try {
          const parsed = JSON.parse(body);
          await ensureWorldsDir();
          await fs.writeFile(filePath, JSON.stringify(parsed, null, 2), 'utf-8');
          sendJson(res, 200, { success: true, message: `World "${worldName}" saved successfully`, name: worldName });
        } catch (err) {
          sendJson(res, 400, { error: 'Failed to save world. Invalid JSON or filesystem error.', details: err.message });
        }
      });
      return;
    }
  }

  sendJson(res, 404, { error: 'Endpoint not found' });
});

await ensureWorldsDir();

server.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
