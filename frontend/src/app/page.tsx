"use client";

import { useState, useRef, useEffect } from "react";
import {
  Send,
  Music,
  Disc,
  Settings,
  X,
  ExternalLink,
  Play,
  Sparkles,
} from "lucide-react";

interface WeightedPrompt {
  text: string;
  weight: number;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  audioUrl?: string;
  details?: string;
  filename?: string;
  promptRef?: string;
  weightedPrompts?: WeightedPrompt[];
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  const [showSettings, setShowSettings] = useState(false);
  const [duration, setDuration] = useState(15);
  const [bpm, setBpm] = useState(90);
  const [density, setDensity] = useState(0.5);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);


  const handleSend = async () => {
    if (!input.trim()) return;

    const originalPrompt = input;
    const userMsg: Message = { 
      role: "user", 
      content: originalPrompt
    };
    
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setShowSettings(false);
    setLoading(true);
    setAnalyzing(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      
      // First, analyze the prompt to get weighted components
      const analyzeResponse = await fetch(`${apiUrl}/analyze-prompt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: originalPrompt }),
      });

      if (!analyzeResponse.ok) throw new Error("Error analyzing prompt");

      const analyzeData = await analyzeResponse.json();
      const weightedPrompts = analyzeData.weighted_prompts || [{ text: originalPrompt, weight: 1.0 }];
      
      setAnalyzing(false);

      // Now generate music with the analyzed components
      const response = await fetch(`${apiUrl}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          weighted_prompts: weightedPrompts.filter(p => p.text.trim() !== ""),
          duration: duration,
          bpm: bpm,
          density: density,
        }),
      });

      if (!response.ok) throw new Error("Error generating audio");

      const contentDisposition = response.headers.get("content-disposition");
      let filename = "";
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^"]+)"?/);
        if (match && match[1]) {
          filename = match[1];
        }
      }

      const breakdownHeader = response.headers.get("X-Prompt-Breakdown");
      const weightedPromptsUsed = breakdownHeader 
        ? JSON.parse(breakdownHeader) 
        : weightedPrompts;

      const blob = await response.blob();
      const audioUrl = URL.createObjectURL(blob);

      const currentSettingsStr = `${duration}s • ${bpm} BPM • Density ${density}`;

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Here is your generated track:",
          audioUrl: audioUrl,
          details: currentSettingsStr,
          filename: filename,
          promptRef: originalPrompt,
          weightedPrompts: weightedPromptsUsed,
        },
      ]);
    } catch (error) {
      console.error(error);
      setAnalyzing(false);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error connecting to Lyria Backend." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-zinc-950 text-zinc-100 font-sans overflow-hidden">
      <header className="p-4 border-b border-zinc-800 flex items-center gap-2 bg-zinc-900/50 backdrop-blur z-10 sticky top-0">
        <Disc className="text-blue-500 animate-spin-slow" />
        <h1 className="font-bold text-lg tracking-tight bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent">
          Lyria Studio V2
        </h1>
        <span className="text-[10px] font-medium bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded-full border border-blue-500/20 uppercase tracking-wide">
          Beta
        </span>
      </header>

      <div className="flex-1 overflow-y-auto p-4 space-y-6 relative scroll-smooth">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-zinc-500 space-y-6 animate-in fade-in zoom-in duration-500">
            <div className="relative">
              <div className="absolute inset-0 bg-blue-500/20 blur-3xl rounded-full"></div>
              <Music size={64} className="relative opacity-20 text-zinc-100" />
            </div>
            <div className="text-center space-y-2">
              <p className="text-lg font-medium text-zinc-400">
                Describe the music you want to create
              </p>
              <p className="text-sm text-zinc-600">
                Our AI engine will compose it in seconds.
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setInput("A synthwave track with heavy bass")}
                className="text-xs text-zinc-400 hover:text-white bg-zinc-900 hover:bg-zinc-800 px-4 py-2 rounded-full border border-zinc-800 transition-colors"
              >
                "Synthwave track"
              </button>
              <button
                onClick={() => setInput("Lo-fi hip hop beat for studying")}
                className="text-xs text-zinc-400 hover:text-white bg-zinc-900 hover:bg-zinc-800 px-4 py-2 rounded-full border border-zinc-800 transition-colors"
              >
                "Lo-fi beat"
              </button>
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${
              msg.role === "user" ? "justify-end" : "justify-start"
            } animate-in slide-in-from-bottom-2 duration-300`}
          >
            <div
              className={`
                p-5 rounded-3xl shadow-lg
                ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white rounded-tr-sm max-w-[85%]"
                    : "bg-zinc-900 border border-zinc-800 rounded-tl-sm w-full max-w-[95%] sm:max-w-[600px]"
                }
              `}
            >
              <p className="text-sm mb-3 font-medium leading-relaxed opacity-90">
                {msg.content}
              </p>

              {msg.weightedPrompts && msg.weightedPrompts.length > 0 && (
                <div className="mb-3 p-3 bg-zinc-800/50 rounded-xl border border-zinc-700/50">
                  <div className="text-[10px] text-zinc-500 uppercase tracking-wider font-bold mb-2">
                    AI-Detected Components
                  </div>
                  <div className="flex flex-wrap gap-2 mb-2">
                    {msg.weightedPrompts.map((wp, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-2 px-3 py-1.5 bg-blue-500/10 border border-blue-500/20 rounded-lg"
                      >
                        <span className="text-xs text-zinc-300">{wp.text}</span>
                        <span className="text-[10px] text-blue-400 font-mono bg-blue-500/20 px-1.5 py-0.5 rounded">
                          {(wp.weight * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </div>
                  <div className="flex gap-1 h-2 rounded-full overflow-hidden">
                    {msg.weightedPrompts.map((wp, idx) => (
                      <div
                        key={idx}
                        className="bg-blue-500"
                        style={{ width: `${wp.weight * 100}%` }}
                        title={`${wp.text}: ${(wp.weight * 100).toFixed(0)}%`}
                      />
                    ))}
                  </div>
                </div>
              )}

              {msg.audioUrl && (
                <div className="mt-4 bg-zinc-950/40 p-4 rounded-2xl border border-zinc-800/50 backdrop-blur-sm">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center">
                      <Play
                        size={14}
                        className="text-blue-400 ml-0.5"
                        fill="currentColor"
                      />
                    </div>
                    <div className="flex-1 h-8 bg-zinc-800/50 rounded-lg overflow-hidden flex items-center px-2">
                      <audio
                        controls
                        src={msg.audioUrl}
                        className="w-full h-8 block opacity-80 hover:opacity-100 transition-opacity"
                      />
                    </div>
                  </div>

                  <div className="flex justify-between items-center pt-3 border-t border-zinc-800/50">
                    {msg.details && (
                      <div className="flex flex-col">
                        <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-bold">
                          Parameters
                        </span>
                        <span className="text-xs text-zinc-400 font-mono">
                          {msg.details}
                        </span>
                      </div>
                    )}

                    <a
                      href={`http://localhost:8501?file=${
                        msg.filename || ""
                      }&prompt=${encodeURIComponent(
                        msg.promptRef || "Imported Audio"
                      )}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group flex items-center gap-2 text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 pl-4 pr-3 py-2 rounded-xl transition-all border border-zinc-700 hover:border-zinc-600 hover:text-white hover:shadow-lg hover:shadow-blue-900/10"
                    >
                      <span className="font-semibold">Open in Studio</span>
                      <ExternalLink
                        size={14}
                        className="text-zinc-500 group-hover:text-blue-400 transition-colors"
                      />
                    </a>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start animate-pulse">
            <div className="bg-zinc-900 border border-zinc-800 p-4 rounded-2xl rounded-tl-sm flex items-center gap-3 text-zinc-400 text-sm shadow-sm">
              <div className="flex gap-1">
                <div
                  className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"
                  style={{ animationDelay: "0ms" }}
                />
                <div
                  className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"
                  style={{ animationDelay: "150ms" }}
                />
                <div
                  className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"
                  style={{ animationDelay: "300ms" }}
                />
              </div>
              <span className="font-medium">
                {analyzing ? "Analyzing prompt and identifying components..." : "Composing track..."}
              </span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-zinc-900 border-t border-zinc-800 relative z-20">
        {showSettings && (
          <div className="absolute bottom-full mb-4 left-4 right-4 sm:left-auto sm:right-4 sm:w-80 bg-zinc-900/95 backdrop-blur-xl border border-zinc-700 p-5 rounded-2xl shadow-2xl z-30 animate-in slide-in-from-bottom-4 fade-in duration-200">
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-2">
                <Settings size={16} className="text-blue-500" />
                <h3 className="text-sm font-bold text-zinc-100">
                  Generation Settings
                </h3>
              </div>
              <button
                onClick={() => setShowSettings(false)}
                className="text-zinc-500 hover:text-white bg-zinc-800/50 hover:bg-zinc-800 p-1 rounded-full transition-colors"
              >
                <X size={14} />
              </button>
            </div>

            <div className="space-y-6">
              <div className="space-y-2">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-zinc-400">Duration</span>
                  <span className="text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded text-[10px]">
                    {duration}s
                  </span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="60"
                  value={duration}
                  onChange={(e) => setDuration(parseInt(e.target.value))}
                  className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-blue-500 hover:accent-blue-400"
                />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-zinc-400">Target BPM</span>
                  <span className="text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded text-[10px]">
                    {bpm}
                  </span>
                </div>
                <input
                  type="range"
                  min="60"
                  max="180"
                  value={bpm}
                  onChange={(e) => setBpm(parseInt(e.target.value))}
                  className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-blue-500 hover:accent-blue-400"
                />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-zinc-400">Instrument Density</span>
                  <span className="text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded text-[10px]">
                    {density}
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={density}
                  onChange={(e) => setDensity(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-blue-500 hover:accent-blue-400"
                />
                <div className="flex justify-between text-[10px] text-zinc-600 px-1">
                  <span>Sparse</span>
                  <span>Dense</span>
                </div>
              </div>
            </div>
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="relative max-w-4xl mx-auto flex gap-3 items-end"
        >
          <button
            type="button"
            onClick={() => setShowSettings(!showSettings)}
            className={`p-3.5 rounded-2xl transition-all border shadow-sm ${
              showSettings
                ? "bg-blue-500/10 border-blue-500/50 text-blue-400"
                : "bg-zinc-950 border-zinc-800 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900 hover:border-zinc-700"
            }`}
          >
            <Settings size={20} />
          </button>

          <div className="flex-1 relative group">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a prompt for the AI..."
              className="w-full bg-zinc-950 border border-zinc-800 group-hover:border-zinc-700 rounded-2xl px-5 py-3.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all placeholder:text-zinc-600 text-zinc-100"
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            disabled={loading || !input}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white p-3.5 rounded-2xl transition-all shadow-lg shadow-blue-900/20 hover:shadow-blue-600/20 active:scale-95"
          >
            <Send size={20} fill="currentColor" className="ml-0.5" />
          </button>
        </form>
      </div>
    </div>
  );
}
