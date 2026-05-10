import { useState } from "react";
import { Key, Check, X } from "lucide-react";
import { getApiKey, setApiKey } from "../api/client";

export default function ApiKeyBar() {
  const [value, setValue] = useState(() => getApiKey());
  const [saved, setSaved] = useState(false);
  const hasKey = !!getApiKey();

  const handleSave = () => {
    const trimmed = value.trim();
    setApiKey(trimmed);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleRemove = () => {
    setApiKey("");
    setValue("");
  };

  return (
    <div className="w-full bg-gray-900/95 border-b border-gray-800 px-4 py-2 flex items-center gap-3">
      <Key size={13} className="text-gray-500 shrink-0" />
      <span className="text-gray-500 text-xs shrink-0 hidden sm:inline">Anthropic API Key:</span>
      <input
        type="password"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="sk-ant-... · stays in your browser only, never sent to our servers"
        className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1 text-gray-200
                   placeholder-gray-600 text-xs focus:outline-none focus:border-sky-500
                   focus:ring-1 focus:ring-sky-500 min-w-0"
        onKeyDown={(e) => e.key === "Enter" && handleSave()}
      />
      <button
        onClick={handleSave}
        disabled={!value.trim()}
        className="shrink-0 text-xs px-3 py-1 rounded-lg bg-sky-700 hover:bg-sky-600
                   disabled:opacity-40 disabled:cursor-not-allowed text-white transition-colors
                   flex items-center gap-1"
      >
        {saved ? <><Check size={11} />Saved</> : "Save"}
      </button>
      {hasKey && (
        <button
          onClick={handleRemove}
          title="Remove API key"
          className="shrink-0 p-1 rounded-lg border border-gray-700 hover:border-red-700
                     text-gray-400 hover:text-red-400 transition-colors"
        >
          <X size={13} />
        </button>
      )}
    </div>
  );
}
