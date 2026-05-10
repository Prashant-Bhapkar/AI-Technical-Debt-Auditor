import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2 } from "lucide-react";
import { api } from "../api/client";

interface Message {
  role: "user" | "assistant";
  text: string;
}

interface Props {
  auditId: string;
}

export default function QAChat({ auditId }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: "Ask me anything about this codebase — its debt, architecture, or how to prioritise fixes.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setLoading(true);
    try {
      const { answer } = await api.askQuestion(auditId, q);
      setMessages((prev) => [...prev, { role: "assistant", text: answer }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: `Error: ${(err as Error).message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="bg-gray-800/60 border border-gray-700 rounded-2xl flex flex-col h-96">
      <div className="px-5 py-3 border-b border-gray-700 flex items-center gap-2">
        <Bot size={16} className="text-sky-400" />
        <span className="text-sm font-semibold text-gray-300">Ask AI about this audit</span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            {msg.role === "assistant" && (
              <div className="shrink-0 w-6 h-6 rounded-full bg-sky-600 flex items-center justify-center mt-0.5">
                <Bot size={12} />
              </div>
            )}
            <div
              className={`max-w-[80%] text-sm px-3 py-2 rounded-xl whitespace-pre-wrap leading-relaxed ${
                msg.role === "user"
                  ? "bg-sky-600 text-white"
                  : "bg-gray-700 text-gray-200"
              }`}
            >
              {msg.text}
            </div>
            {msg.role === "user" && (
              <div className="shrink-0 w-6 h-6 rounded-full bg-gray-600 flex items-center justify-center mt-0.5">
                <User size={12} />
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex gap-2 justify-start">
            <div className="w-6 h-6 rounded-full bg-sky-600 flex items-center justify-center">
              <Bot size={12} />
            </div>
            <div className="bg-gray-700 px-3 py-2 rounded-xl flex items-center gap-1">
              <Loader2 size={14} className="animate-spin text-gray-400" />
              <span className="text-sm text-gray-400">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="px-4 py-3 border-t border-gray-700 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKey}
          placeholder="What are the highest-risk issues?"
          className="flex-1 bg-gray-700 text-sm text-gray-200 placeholder-gray-500
                     rounded-lg px-3 py-2 outline-none focus:ring-1 focus:ring-sky-500"
        />
        <button
          onClick={send}
          disabled={!input.trim() || loading}
          className="px-3 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-40
                     disabled:cursor-not-allowed rounded-lg transition-colors"
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  );
}
