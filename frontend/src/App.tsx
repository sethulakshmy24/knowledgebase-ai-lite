
import { useState } from "react";
import "./App.css";
import Summary from "./components/summary/summary";
import { WS_URL } from "./config";


type Mode = "text" | "url" | "youtube";

function App() {
  const [mode, setMode] = useState<Mode>("text");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");


const [progress, setProgress] = useState("");
const [partialNotes, setPartialNotes] = useState<string[]>([]);
const [streamingSummary, setStreamingSummary] = useState("");

function handleSummarize() {
  setSummary("");
  setStreamingSummary("");
  setError("");
  setProgress("");
  setPartialNotes([]);

  const content = mode === "text" ? text.trim() : url.trim();

  if (!content) {
    setError("Please enter some text or a URL.");
    return;
  }

  setLoading(true);

  const ws = new WebSocket(`${WS_URL}/ws/summarize`);

  ws.onopen = () => {
    ws.send(
      JSON.stringify({
        mode,
        content,
      })
    );
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch (data.event) {
      case "progress":
        setProgress(data.message);
        break;

      case "chunk_completed":
        setProgress(
          `Processed chunk ${data.index} of ${data.total}`
        );
        break;

      case "text_delta":
        setStreamingSummary((previous) => previous + data.text);
        break;

      case "completed":
        setSummary(data.summary);
        setProgress(data.message || "Completed");
        break;

      case "error":
        setError(data.message || "Summarization failed.");
        ws.close();
        break;
    }

    ws.onerror = () => {
      setError("Unable to connect to the summarization service.");
      setLoading(false);
    };

    ws.onclose = () => {
      setLoading(false);
    };
  }
}


  return (
    <main className="app">
      <header className="app-header">
        <h1>KnowledgeBase AI Lite</h1>
        <p>Turn long content into concise, useful summaries.</p>
      </header>

      <section className="summarizer">
        <div className="mode-switch">
          <button
            className={mode === "text" ? "active" : ""}
            onClick={() => {
              setMode("text");
              setSummary("");
              setError("");
            }}
          >
            Paste text
          </button>

          <button
            className={mode === "url" ? "active" : ""}
            onClick={() => {
              setMode("url");
              setSummary("");
              setError("");
            }}
          >
            Web article
          </button>

          <button
            className={mode === "youtube" ? "active" : ""}
            onClick={() => {
              setMode("youtube");
              setSummary("");
              setError("");
            }}
          >
            YouTube
          </button>
        </div>

        {mode === "text" ? (
          <div className="input-section">
            <label htmlFor="source-text">Content to summarize</label>
            <textarea
              id="source-text"
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="Paste an article, technical document, or notes here..."
              rows={10}
            />
            <p className="helper-text">
              Minimum 20 characters, maximum 50,000.
            </p>
          </div>
        ) : (
          <div className="input-section">
            <label htmlFor="source-url">
              {mode === "youtube" ? "YouTube video URL" : "Web article URL"}
            </label>
            <input
              id="source-url"
              type="url"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder={
                mode === "youtube"
                  ? "https://www.youtube.com/watch?v=..."
                  : "https://example.com/article"
              }
            />
            <p className="helper-text">
              {mode === "youtube"
                ? "The video must have an accessible transcript."
                : "Enter a publicly accessible article URL."}
            </p>
          </div>
        )}

        <button
          className="summarize-button"
          onClick={handleSummarize}
          disabled={loading}
        >
          {loading ? "Summarizing..." : "Summarize"}
        </button>


        {progress && (
          <p className="helper-text" role="status">
            {progress}
          </p>
        )}

        {partialNotes.length > 0 && (
          <section className="result-section">
            <h2>Notes generated so far</h2>

            {partialNotes.map((note, index) => (
              <article key={index} className="summary-chunk">
                <Summary summary={note} />
              </article>
            ))}
          </section>
        )}

        {summary && (
          <section className="result-section">
            <h2>Final learning notes</h2>
            <Summary summary={summary} />
          </section>
        )}


        {error && (
          <div className="error-message" role="alert">
            {error}
          </div>
        )}

        {(streamingSummary || summary) && (
          <section className="result-section">
            <h2>
              {loading ? "Generating learning notes..." : "Final learning notes"}
            </h2>

            <Summary summary={streamingSummary || summary} />
          </section>
        )}
      </section>
    </main>
  );
}

export default App;
