"use client";

import { useState, useRef, useEffect } from "react";
import {
  Send,
  Music,
  Disc,
  ExternalLink,
} from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
  audioUrl?: string;
  details?: string;
  filename?: string;
  promptRef?: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [negativePrompt, setNegativePrompt] = useState("");
  const [seed, setSeed] = useState<number | null>(null);

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
    setLoading(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

      // Generate music with single prompt
      const response = await fetch(`${apiUrl}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: originalPrompt,
          negative_prompt: negativePrompt || undefined,
          seed: seed || undefined,
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

      const blob = await response.blob();
      const audioUrl = URL.createObjectURL(blob);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Here is your generated track:",
          audioUrl: audioUrl,
          details: "30s • 48kHz stereo",
          filename: filename,
          promptRef: originalPrompt,
        },
      ]);
    } catch (error) {
      console.error(error);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error connecting to Lyria Backend." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-[#1D122E] text-[#E6E4EB] font-sans overflow-hidden">
      <header className="p-4 border-b border-[#383340] flex items-center gap-2 bg-[#231C2E]/50 backdrop-blur z-10 sticky top-0">
        <Disc className="text-[#5B3890] animate-spin-slow" />
        <h1 className="font-bold text-lg tracking-tight bg-gradient-to-r from-white to-[#C5C2CC] bg-clip-text text-transparent">
          Lyria Studio V2
        </h1>
        <span className="text-[10px] font-medium bg-[#5B3890]/10 text-[#917AB5] px-2 py-0.5 rounded-full border border-[#5B3890]/20 uppercase tracking-wide">
          Beta
        </span>
      </header>

      <div className="flex-1 overflow-y-auto p-4 space-y-6 relative scroll-smooth">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-[#777380] space-y-6 animate-in fade-in zoom-in duration-500">
            <div className="relative">
              <div className="absolute inset-0 bg-[#5B3890]/20 blur-3xl rounded-full"></div>
              <Music size={64} className="relative opacity-20 text-[#E6E4EB]" />
            </div>
            <div className="text-center space-y-2">
              <p className="text-lg font-medium text-[#C5C2CC]">
                Describe the music you want to create
              </p>
              <p className="text-sm text-[#777380]">
                Our AI engine will compose it in seconds.
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setInput("A synthwave track with heavy bass")}
                className="text-xs text-[#C5C2CC] hover:text-white bg-[#231C2E] hover:bg-[#383340] px-4 py-2 rounded-full border border-[#383340] transition-colors"
              >
                "Synthwave track"
              </button>
              <button
                onClick={() => setInput("Lo-fi hip hop beat for studying")}
                className="text-xs text-[#C5C2CC] hover:text-white bg-[#231C2E] hover:bg-[#383340] px-4 py-2 rounded-full border border-[#383340] transition-colors"
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
                    ? "bg-[#5B3890] text-white rounded-tr-sm max-w-[85%]"
                    : "bg-[#231C2E] border border-[#383340] rounded-tl-sm w-full max-w-[95%] sm:max-w-[600px]"
                }
              `}
            >
              <p className="text-sm mb-3 font-medium leading-relaxed opacity-90">
                {msg.content}
              </p>

              {msg.audioUrl && (
                <div className="mt-4 bg-[#1D122E]/40 p-4 rounded-2xl border border-[#383340]/50 backdrop-blur-sm">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="flex-1 h-10 bg-[#231C2E]/50 rounded-lg overflow-hidden flex items-center px-2">
                      <audio
                        controls
                        src={msg.audioUrl}
                        className="w-full h-full block"
                        preload="metadata"
                      />
                    </div>
                  </div>

                  <div className="flex justify-between items-center pt-3 border-t border-[#383340]/50">
                    {msg.details && (
                      <div className="flex flex-col">
                        <span className="text-[10px] text-[#777380] uppercase tracking-wider font-bold">
                          Parameters
                        </span>
                        <span className="text-xs text-[#C5C2CC] font-mono">
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
                      className="group flex items-center gap-2 text-xs bg-[#231C2E] hover:bg-[#383340] text-[#C5C2CC] pl-4 pr-3 py-2 rounded-xl transition-all border border-[#383340] hover:border-[#5B3890] hover:text-white hover:shadow-lg hover:shadow-[#5B3890]/10"
                    >
                      <span className="font-semibold">Open in Studio</span>
                      <ExternalLink
                        size={14}
                        className="text-[#777380] group-hover:text-[#917AB5] transition-colors"
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
            <div className="bg-[#231C2E] border border-[#383340] p-4 rounded-2xl rounded-tl-sm flex items-center gap-3 text-[#C5C2CC] text-sm shadow-sm">
              <div className="flex gap-1">
                <div
                  className="w-2 h-2 bg-[#5B3890] rounded-full animate-bounce"
                  style={{ animationDelay: "0ms" }}
                />
                <div
                  className="w-2 h-2 bg-[#5B3890] rounded-full animate-bounce"
                  style={{ animationDelay: "150ms" }}
                />
                <div
                  className="w-2 h-2 bg-[#5B3890] rounded-full animate-bounce"
                  style={{ animationDelay: "300ms" }}
                />
              </div>
              <span className="font-medium">
                Composing track...
              </span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-[#231C2E] border-t border-[#383340] relative z-20">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="relative max-w-4xl mx-auto flex gap-3 items-end"
        >

          <div className="flex-1 relative group flex flex-col gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a prompt for the AI..."
              className="w-full bg-[#1D122E] border border-[#383340] group-hover:border-[#5B3890] rounded-2xl px-5 py-3.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#5B3890]/20 focus:border-[#5B3890] transition-all placeholder:text-[#777380] text-[#E6E4EB]"
              disabled={loading}
            />
            <div className="flex gap-2">
              <input
                type="text"
                value={negativePrompt}
                onChange={(e) => setNegativePrompt(e.target.value)}
                placeholder="Negative prompt (optional)..."
                className="flex-1 bg-[#1D122E] border border-[#383340] hover:border-[#5B3890] rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-[#5B3890]/20 focus:border-[#5B3890] transition-all placeholder:text-[#777380] text-[#E6E4EB]"
                disabled={loading}
              />
              <input
                type="number"
                value={seed || ""}
                onChange={(e) => setSeed(e.target.value ? parseInt(e.target.value) : null)}
                placeholder="Seed (optional)"
                className="w-24 bg-[#1D122E] border border-[#383340] hover:border-[#5B3890] rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-[#5B3890]/20 focus:border-[#5B3890] transition-all placeholder:text-[#777380] text-[#E6E4EB]"
                disabled={loading}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || !input}
            className="bg-[#5B3890] hover:bg-[#6D4D9C] disabled:opacity-50 disabled:cursor-not-allowed text-white p-3.5 rounded-2xl transition-all shadow-lg shadow-[#5B3890]/20 hover:shadow-[#6D4D9C]/20 active:scale-95"
          >
            <Send size={20} fill="currentColor" className="ml-0.5" />
          </button>
        </form>
      </div>
    </div>
  );
}
