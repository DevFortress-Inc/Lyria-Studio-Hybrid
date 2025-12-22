"use client";

import { useState, useRef, useEffect } from "react";
import {
  Send,
  Music,
  Disc,
  Settings,
  X,
  ExternalLink,
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
  parameters?: {
    bpm?: number;
    guidance?: number;
    density?: number;
  };
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  const [showSettings, setShowSettings] = useState(false);
  const [duration, setDuration] = useState(15);
  const [bpm, setBpm] = useState(90);
  const [guidance, setGuidance] = useState(7.0);
  const [density, setDensity] = useState(0.5);
  const [aiSuggestedParams, setAiSuggestedParams] = useState<{
    bpm?: number;
    guidance?: number;
    density?: number;
  } | null>(null);

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
    setAiSuggestedParams(null); // Clear previous suggestions

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      
      // Get the last assistant message with track info for context
      const lastTrack = messages
        .slice()
        .reverse()
        .find(msg => msg.role === "assistant" && msg.weightedPrompts && msg.weightedPrompts.length > 0);
      
      // Build request body with optional previous context
      // Always pass context if there's a previous track - let the AI decide if it's an edit
      const analyzeRequestBody: any = { prompt: originalPrompt };
      if (lastTrack && lastTrack.weightedPrompts && lastTrack.weightedPrompts.length > 0) {
        // Use stored parameters if available, otherwise try to parse from details
        const lastParams: any = lastTrack.parameters || {};
        if (!lastParams.bpm && lastTrack.details) {
          // Fallback: Try to parse BPM from details string
          const bpmMatch = lastTrack.details.match(/(\d+)\s*BPM/i);
          if (bpmMatch) lastParams.bpm = parseInt(bpmMatch[1]);
        }
        if (!lastParams.guidance && lastTrack.details) {
          const guidanceMatch = lastTrack.details.match(/Guidance\s*(\d+\.?\d*)/i);
          if (guidanceMatch) lastParams.guidance = parseFloat(guidanceMatch[1]);
        }
        if (!lastParams.density && lastTrack.details) {
          const densityMatch = lastTrack.details.match(/Density\s*(\d+\.?\d*)/i);
          if (densityMatch) lastParams.density = parseFloat(densityMatch[1]);
        }
        
        analyzeRequestBody.previous_context = {
          weighted_prompts: lastTrack.weightedPrompts || [],
          parameters: Object.keys(lastParams).length > 0 ? lastParams : undefined
        };
      }
      
      // Analyze the prompt to get weighted components
      const analyzeResponse = await fetch(`${apiUrl}/analyze-prompt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(analyzeRequestBody),
      });

      if (!analyzeResponse.ok) throw new Error("Error analyzing prompt");

      const analyzeData = await analyzeResponse.json();
      const weightedPrompts = analyzeData.weighted_prompts || [{ text: originalPrompt, weight: 1.0 }];
      const suggestedParams = analyzeData.parameters || {};
      
      // Update parameters with AI suggestions if available
      if (suggestedParams.bpm !== undefined) {
        setBpm(suggestedParams.bpm);
      }
      if (suggestedParams.guidance !== undefined) {
        setGuidance(suggestedParams.guidance);
      }
      if (suggestedParams.density !== undefined) {
        setDensity(suggestedParams.density);
      }
      
      setAiSuggestedParams(suggestedParams);
      setAnalyzing(false);

      // Generate music with the analyzed components and AI-suggested parameters
      const response = await fetch(`${apiUrl}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
          weighted_prompts: weightedPrompts.filter((p: WeightedPrompt) => p.text.trim() !== ""),
          duration: duration,
          bpm: bpm,
          guidance: guidance,
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

      const finalBpm = suggestedParams.bpm !== undefined ? suggestedParams.bpm : bpm;
      const finalGuidance = suggestedParams.guidance !== undefined ? suggestedParams.guidance : guidance;
      const finalDensity = suggestedParams.density !== undefined ? suggestedParams.density : density;
      
      const currentSettingsStr = `${duration}s • ${finalBpm} BPM • Guidance ${finalGuidance.toFixed(1)} • Density ${finalDensity.toFixed(1)}`;

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
          parameters: {
            bpm: finalBpm,
            guidance: finalGuidance,
            density: finalDensity,
          },
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

              {msg.weightedPrompts && msg.weightedPrompts.length > 0 && (
                <div className="mb-3 p-3 bg-[#231C2E]/50 rounded-xl border border-[#383340]/50">
                  <div className="text-[10px] text-[#777380] uppercase tracking-wider font-bold mb-2">
                    AI-Detected Components
                  </div>
                  <div className="flex flex-wrap gap-2 mb-2">
                    {msg.weightedPrompts.map((wp, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-2 px-3 py-1.5 bg-[#5B3890]/10 border border-[#5B3890]/20 rounded-lg"
                      >
                        <span className="text-xs text-[#C5C2CC]">{wp.text}</span>
                        <span className="text-[10px] text-[#917AB5] font-mono bg-[#5B3890]/20 px-1.5 py-0.5 rounded">
                          {(wp.weight * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </div>
                  <div className="flex gap-1 h-2 rounded-full overflow-hidden">
                    {msg.weightedPrompts.map((wp, idx) => (
                      <div
                        key={idx}
                        className="bg-[#5B3890]"
                        style={{ width: `${wp.weight * 100}%` }}
                        title={`${wp.text}: ${(wp.weight * 100).toFixed(0)}%`}
                      />
                    ))}
                  </div>
                </div>
              )}

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
                {analyzing ? "Analyzing prompt and identifying components..." : "Composing track..."}
              </span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-[#231C2E] border-t border-[#383340] relative z-20">
        {showSettings && (
          <div className="absolute bottom-full mb-4 left-4 right-4 sm:left-auto sm:right-4 sm:w-80 bg-[#231C2E]/95 backdrop-blur-xl border border-[#383340] p-5 rounded-2xl shadow-2xl z-30 animate-in slide-in-from-bottom-4 fade-in duration-200">
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-2">
                <Settings size={16} className="text-[#5B3890]" />
                <h3 className="text-sm font-bold text-[#E6E4EB]">
                  Generation Settings
                </h3>
              </div>
              <button
                onClick={() => setShowSettings(false)}
                className="text-[#777380] hover:text-white bg-[#231C2E]/50 hover:bg-[#231C2E] p-1 rounded-full transition-colors"
              >
                <X size={14} />
              </button>
            </div>

            <div className="space-y-6">
              <div className="space-y-2">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-[#C5C2CC]">Duration</span>
                  <span className="text-[#917AB5] bg-[#5B3890]/10 px-2 py-0.5 rounded text-[10px]">
                    {duration}s
                  </span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="60"
                  value={duration}
                  onChange={(e) => setDuration(parseInt(e.target.value))}
                  className="w-full h-1.5 bg-[#231C2E] rounded-lg appearance-none cursor-pointer accent-[#5B3890] hover:accent-[#6D4D9C]"
                />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-[#C5C2CC]">Target BPM</span>
                  <div className="flex items-center gap-2">
                    {aiSuggestedParams?.bpm !== undefined && (
                      <span className="text-[8px] text-[#00C0B1] bg-[#00C0B1]/10 px-1.5 py-0.5 rounded uppercase">
                        AI
                      </span>
                    )}
                    <span className="text-[#917AB5] bg-[#5B3890]/10 px-2 py-0.5 rounded text-[10px]">
                      {bpm}
                    </span>
                  </div>
                </div>
                <input
                  type="range"
                  min="60"
                  max="180"
                  value={bpm}
                  onChange={(e) => {
                    setBpm(parseInt(e.target.value));
                    // Clear AI suggestion if user manually adjusts
                    if (aiSuggestedParams?.bpm !== undefined) {
                      setAiSuggestedParams(prev => prev ? { ...prev, bpm: undefined } : null);
                    }
                  }}
                  className="w-full h-1.5 bg-[#231C2E] rounded-lg appearance-none cursor-pointer accent-[#5B3890] hover:accent-[#6D4D9C]"
                />
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-[#C5C2CC]">Prompt Adherence</span>
                  <div className="flex items-center gap-2">
                    {aiSuggestedParams?.guidance !== undefined && (
                      <span className="text-[8px] text-[#00C0B1] bg-[#00C0B1]/10 px-1.5 py-0.5 rounded uppercase">
                        AI
                      </span>
                    )}
                    <span className="text-[#917AB5] bg-[#5B3890]/10 px-2 py-0.5 rounded text-[10px]">
                      {guidance.toFixed(1)}
                    </span>
                  </div>
                </div>
                <input
                  type="range"
                  min="1"
                  max="10"
                  step="0.5"
                  value={guidance}
                  onChange={(e) => {
                    setGuidance(parseFloat(e.target.value));
                    // Clear AI suggestion if user manually adjusts
                    if (aiSuggestedParams?.guidance !== undefined) {
                      setAiSuggestedParams(prev => prev ? { ...prev, guidance: undefined } : null);
                    }
                  }}
                  className="w-full h-1.5 bg-[#231C2E] rounded-lg appearance-none cursor-pointer accent-[#5B3890] hover:accent-[#6D4D9C]"
                />
                <div className="flex justify-between text-[10px] text-[#777380] px-1">
                  <span>Creative</span>
                  <span>Strict</span>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-[#C5C2CC]">Instrument Density</span>
                  <div className="flex items-center gap-2">
                    {aiSuggestedParams?.density !== undefined && (
                      <span className="text-[8px] text-[#00C0B1] bg-[#00C0B1]/10 px-1.5 py-0.5 rounded uppercase">
                        AI
                      </span>
                    )}
                    <span className="text-[#917AB5] bg-[#5B3890]/10 px-2 py-0.5 rounded text-[10px]">
                      {density.toFixed(1)}
                    </span>
                  </div>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={density}
                  onChange={(e) => {
                    setDensity(parseFloat(e.target.value));
                    // Clear AI suggestion if user manually adjusts
                    if (aiSuggestedParams?.density !== undefined) {
                      setAiSuggestedParams(prev => prev ? { ...prev, density: undefined } : null);
                    }
                  }}
                  className="w-full h-1.5 bg-[#231C2E] rounded-lg appearance-none cursor-pointer accent-[#5B3890] hover:accent-[#6D4D9C]"
                />
                <div className="flex justify-between text-[10px] text-[#777380] px-1">
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
                ? "bg-[#5B3890]/10 border-[#5B3890]/50 text-[#917AB5]"
                : "bg-[#1D122E] border-[#383340] text-[#C5C2CC] hover:text-[#E6E4EB] hover:bg-[#231C2E] hover:border-[#5B3890]"
            }`}
          >
            <Settings size={20} />
          </button>

          <div className="flex-1 relative group">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a prompt for the AI..."
              className="w-full bg-[#1D122E] border border-[#383340] group-hover:border-[#5B3890] rounded-2xl px-5 py-3.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#5B3890]/20 focus:border-[#5B3890] transition-all placeholder:text-[#777380] text-[#E6E4EB]"
              disabled={loading}
            />
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
