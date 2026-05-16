import { useState, useEffect, useRef } from "react";
import { X, Key, Zap, Check, Eye, EyeOff } from "lucide-react";
import { getApiKey, setApiKey, getRedisUrl, setRedisUrl } from "../api/client";

interface Props {
  open: boolean;
  onClose: () => void;
}

function Field({
  label, icon, value, onChange, onSave, onClear,
  placeholder, hint, type = "password", saved,
}: {
  label: string;
  icon: React.ReactNode;
  value: string;
  onChange: (v: string) => void;
  onSave: () => void;
  onClear: () => void;
  placeholder: string;
  hint: string;
  type?: string;
  saved: boolean;
}) {
  const [show, setShow] = useState(false);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-sm font-medium text-gray-300">
        {icon}
        {label}
      </div>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <input
            type={type === "password" && !show ? "password" : "text"}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            onKeyDown={(e) => e.key === "Enter" && onSave()}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm
                       text-gray-200 placeholder-gray-600 focus:outline-none focus:border-sky-500
                       focus:ring-1 focus:ring-sky-500 pr-9"
          />
          {type === "password" && (
            <button
              type="button"
              onClick={() => setShow((v) => !v)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
            >
              {show ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          )}
        </div>
        <button
          onClick={onSave}
          disabled={!value.trim()}
          className="px-3 py-2 rounded-lg bg-sky-700 hover:bg-sky-600 disabled:opacity-40
                     disabled:cursor-not-allowed text-white text-sm transition-colors flex items-center gap-1.5"
        >
          {saved ? <><Check size={13} /> Saved</> : "Save"}
        </button>
        {value && (
          <button
            onClick={onClear}
            title="Remove"
            className="px-2 py-2 rounded-lg border border-gray-700 hover:border-red-700
                       text-gray-400 hover:text-red-400 transition-colors"
          >
            <X size={14} />
          </button>
        )}
      </div>
      <p className="text-xs text-gray-500">{hint}</p>
    </div>
  );
}

export default function SettingsModal({ open, onClose }: Props) {
  const [apiKey, setApiKeyVal] = useState(() => getApiKey());
  const [redisUrl, setRedisUrlVal] = useState(() => getRedisUrl());
  const [apiKeySaved, setApiKeySaved] = useState(false);
  const [redisSaved, setRedisSaved] = useState(false);
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const saveApiKey = () => {
    setApiKey(apiKey.trim());
    setApiKeySaved(true);
    setTimeout(() => setApiKeySaved(false), 2000);
  };

  const clearApiKey = () => { setApiKey(""); setApiKeyVal(""); };

  const saveRedis = () => {
    setRedisUrl(redisUrl.trim());
    setRedisSaved(true);
    setTimeout(() => setRedisSaved(false), 2000);
  };

  const clearRedis = () => { setRedisUrl(""); setRedisUrlVal(""); };

  return (
    <div
      ref={overlayRef}
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4"
    >
      <div className="w-full max-w-lg bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <h2 className="text-base font-semibold text-white">Settings</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="px-6 py-5 space-y-6">
          {/* AI Features */}
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-4">AI Features</p>
            <Field
              label="Anthropic API Key"
              icon={<Key size={14} className="text-sky-400" />}
              value={apiKey}
              onChange={setApiKeyVal}
              onSave={saveApiKey}
              onClear={clearApiKey}
              placeholder="sk-ant-..."
              hint="Enables AI Insights, Q&A chat, and code fixes. Stored in your browser only — never sent to our server."
              saved={apiKeySaved}
            />
          </div>

          <div className="border-t border-gray-800" />

          {/* Async Processing */}
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-4">Async Processing (optional)</p>
            <Field
              label="Redis URL"
              icon={<Zap size={14} className="text-purple-400" />}
              value={redisUrl}
              onChange={setRedisUrlVal}
              onSave={saveRedis}
              onClear={clearRedis}
              placeholder="rediss://default:password@host:6379"
              hint="Bring your own Redis (e.g. Upstash free tier) to enable async audit processing. Without this, audits run in standard mode. Stored in your browser only."
              saved={redisSaved}
            />
            <a
              href="https://upstash.com"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block mt-2 text-xs text-purple-400 hover:text-purple-300 underline"
            >
              Get a free Redis URL from Upstash →
            </a>
          </div>
        </div>

        <div className="px-6 py-4 border-t border-gray-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200 border border-gray-700
                       hover:border-gray-500 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
