import { Settings, Key, Zap } from "lucide-react";
import { getApiKey, getRedisUrl } from "../api/client";

interface Props {
  onOpenSettings: () => void;
}

function StatusDot({ active, label }: { active: boolean; label: string }) {
  return (
    <span className={`flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full border ${
      active
        ? "border-green-800 bg-green-900/30 text-green-400"
        : "border-gray-700 bg-gray-800/30 text-gray-500"
    }`}>
      <span className={`w-1.5 h-1.5 rounded-full ${active ? "bg-green-400" : "bg-gray-600"}`} />
      {label}
    </span>
  );
}

export default function ApiKeyBar({ onOpenSettings }: Props) {
  const hasApiKey = !!getApiKey();
  const hasRedis = !!getRedisUrl();

  return (
    <div className="w-full bg-gray-900/95 border-b border-gray-800 px-4 py-2 flex items-center justify-between gap-3">
      {/* Status indicators */}
      <div className="flex items-center gap-2">
        <Key size={12} className="text-gray-600" />
        <StatusDot active={hasApiKey} label="AI key" />
        <Zap size={12} className="text-gray-600" />
        <StatusDot active={hasRedis} label="Redis" />
      </div>

      {/* Settings button */}
      <button
        onClick={onOpenSettings}
        className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200
                   border border-gray-700 hover:border-gray-500 px-3 py-1 rounded-lg transition-colors"
      >
        <Settings size={13} />
        Settings
      </button>
    </div>
  );
}
