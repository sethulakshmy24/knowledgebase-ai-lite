# KnowledgeBase AI Lite

**Turn long-form content into structured, useful learning notes with AI.**

KnowledgeBase AI Lite is a full-stack AI-powered application that transforms text, web articles, and YouTube transcripts into organized learning notes. It combines a React and TypeScript frontend with a Python FastAPI backend and supports incremental delivery of generated notes through WebSockets.

The project explores practical AI application development, including content extraction, text chunking, LLM integration, asynchronous processing, and real-time streaming.

## ✨ Features

- **Text summarization** — paste technical documentation, articles, or notes.
- **Web article summarization** — extract and summarize content from publicly accessible article URLs.
- **YouTube summarization** — generate notes from videos with accessible transcripts.
- **AI-generated learning notes** — organize content into topics, key concepts, explanations, code examples, practical tips, and takeaways.
- **Real-time streaming** — progressively deliver generated notes through WebSockets.
- **Long-content processing** — split large inputs into manageable chunks before generating consolidated notes.
- **Markdown rendering** — display structured headings, lists, tables, links, and code blocks.
- **Provider-independent architecture** — keep the AI integration isolated so the model provider can be replaced without redesigning the frontend.

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite |
| Styling | CSS |
| Backend | Python, FastAPI |
| API communication | HTTP, WebSockets |
| Content extraction | HTTPX, BeautifulSoup |
| YouTube transcripts | youtube-transcript-api |
| AI inference | Ollama with Qwen 2.5 7B Instruct |
| Markdown rendering | react-markdown, remark-gfm |

## 🏗️ Architecture

```text
┌──────────────────────────────────┐
│         React Frontend           │
│                                  │
│  Text Input / Article URL / Video│
│  Live Progress + Markdown Notes  │
└────────────────┬─────────────────┘
                 │
          WebSocket / HTTP
                 │
┌────────────────▼─────────────────┐
│          FastAPI Backend         │
│                                  │
│  Request Validation              │
│  Content Extraction              │
│  Text Chunking                   │
│  Summary Generation              │
│  Streaming Event Delivery        │
└─────────┬────────────────┬───────┘
          │                │
┌─────────▼────────┐ ┌─────▼────────────┐
│ Content Extractors│ │  AI Provider     │
│                  │ │                  │
│ Article Extractor│ │ Ollama / Qwen    │
│ YouTube Transcript│ │ Replaceable API │
└──────────────────┘ └──────────────────┘
```

### Processing flow

1. The user submits text, an article URL, or a YouTube URL.
2. The backend extracts content when necessary.
3. Large inputs are split into smaller chunks.
4. The AI model processes the content and generates notes.
5. The backend sends progress and streamed text events through a WebSocket.
6. The frontend progressively renders the generated Markdown.
7. The completed notes remain available in the result view.

## 📁 Project Structure

```text
knowledgebase-ai-lite/
├── backend/
│   ├── main.py                 # FastAPI routes and WebSocket
│   ├── summarizer.py           # AI integration and summarization
│   ├── article_extractor.py    # Web article extraction
│   └── youtube_extractor.py    # YouTube transcript extraction
│
├── src/
│   ├── components/
│   │   └── summary/
│   │       └── summary.tsx     # Markdown rendering
│   ├── App.tsx                 # Main application UI
│   ├── App.css                 # Application styling
│   └── main.tsx                # Frontend entry point
│
├── .gitignore
├── package.json
├── README.md
└── requirements.txt
```

*The structure above describes the expected layout; adjust filenames and paths to match the actual repository.*

## 🚀 Getting Started

### Prerequisites

- Node.js and npm
- Python 3.10 or a compatible version supported by your dependencies
- Ollama installed locally
- Git

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd knowledgebase-ai-lite
```

Replace the placeholder with your repository URL.

### 2. Set up the AI model

Install Ollama from [ollama.com](https://ollama.com/), then download the configured model:

```bash
ollama pull qwen2.5:7b-instruct
```

Start the Ollama service if it is not already running:

```bash
ollama serve
```

Ollama's default API endpoint is:

```text
http://localhost:11434
```

If your Ollama installation already runs as a background service, you do not need to start it again.

### 3. Set up the Python backend

From the project root:

```bash
cd backend

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

If `requirements.txt` is located in the project root rather than inside `backend/`, run the installation command from the root directory instead.

Start the backend:

```bash
uvicorn main:app --reload --port 8000
```

The API should be available at:

- API base URL: `http://localhost:8000`
- Interactive API documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`
- WebSocket endpoint: `ws://localhost:8000/ws/summarize`

### 4. Set up the React frontend

Open another terminal and navigate to the project root:

```bash
npm install
npm run dev
```

Open the local URL printed by Vite, usually:

```text
http://localhost:5173
```

Make sure the backend and Ollama are running before submitting content.

## 🔌 API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/health` | GET | Check backend health |
| `/api/summarize` | POST | Summarize provided text |
| `/api/summarize-url` | POST | Extract and summarize an article |
| `/api/summarize-youtube` | POST | Extract and summarize a YouTube transcript |
| `/ws/summarize` | WebSocket | Process content and stream progress and generated notes |

For exact request bodies and response formats, refer to the API documentation available at `/docs`.

### WebSocket events

The WebSocket endpoint communicates using JSON events.

| Event | Purpose |
|---|---|
| `progress` | Reports the current processing stage |
| `chunk_completed` | Indicates that a content chunk has been processed |
| `text_delta` | Delivers an incremental piece of generated text |
| `completed` | Returns the final generated notes |
| `error` | Reports a processing error |

Example streamed event:

```json
{
  "event": "text_delta",
  "text": "The main concepts covered in this section are..."
}
```

## ⚙️ Configuration

The current local setup uses Ollama and the `qwen2.5:7b-instruct` model.

If you change the model or provider, update the backend AI integration accordingly. For a hosted provider, keep API keys in environment variables and never expose secrets in frontend code or commit them to Git.

A future configuration could look like:

```env
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct
```

These variables are illustrative; the application must explicitly read them from its environment before they take effect.

## 🧪 Troubleshooting

**The frontend cannot connect to the backend**

- Confirm that FastAPI is running on port `8000`.
- Verify that the WebSocket URL matches the backend host and port.
- Check the browser console for connection errors.

**The AI model is unavailable**

- Run `ollama list` to check installed models.
- Verify that the configured model name matches the installed model.
- Confirm that Ollama is accessible at `http://localhost:11434`.

**Article extraction fails**

- Confirm that the article URL is publicly accessible.
- Some websites block automated requests or render their content using JavaScript.

**YouTube transcript extraction fails**

- The video must have an accessible transcript.
- Transcript availability can depend on the video, language, and YouTube restrictions.

**Generated notes appear incomplete while streaming**

- Check the backend logs for AI provider errors.
- Verify that `text_delta` events are received by the frontend.
- Ensure the final `completed` event is handled correctly.

## 🔒 Security and Limitations

- Only process URLs from trusted sources. Production deployments should validate URLs and block private or internal network destinations to mitigate SSRF risks.
- Do not submit confidential source code or internal documentation to hosted AI providers without reviewing their data policies.
- Public article extraction and YouTube transcript availability are not guaranteed.
- Model output may contain inaccuracies and should be reviewed before relying on it.
- The current project is intended for local development and learning, not as a production-hardened service.

## 🗺️ Roadmap

- [ ] Improve streaming so generated notes appear smoothly in real time.
- [ ] Add syntax highlighting and code-copy controls.
- [ ] Support replaceable hosted AI providers.
- [ ] Add configurable note formats and summary detail levels.
- [ ] Introduce automated backend and frontend tests.
- [ ] Add source references and links to extracted material.
- [ ] Add document upload support for PDF and Markdown files.
- [ ] Add saved notes and searchable knowledge collections.
- [ ] Explore retrieval-augmented generation (RAG) for larger documentation collections.
- [ ] Add configurable chunking, retry handling, and request cancellation.

## 🎯 Project Goals

KnowledgeBase AI Lite is a portfolio project focused on building practical full-stack AI engineering skills, including:

- React and TypeScript application design
- Python backend development with FastAPI
- Asynchronous request processing
- WebSocket-based streaming
- LLM integration and prompt design
- Long-document processing
- Extensible AI provider architecture

## 📄 License

Choose a license before publishing this repository. If you intend to make the project open source, consider the [MIT License](https://opensource.org/license/mit/).

---

**Built as a learning project exploring full-stack development and practical AI integration.**
