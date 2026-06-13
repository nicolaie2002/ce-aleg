import { AlertCircle, AlertTriangle, CheckCircle2, Info } from "lucide-react";

const TONES = {
  success: {
    classes: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
    icon: CheckCircle2,
  },
  error: {
    classes: "border-red-400/30 bg-red-400/10 text-red-200",
    icon: AlertCircle,
  },
  warning: {
    classes: "border-yellow-300/30 bg-yellow-300/10 text-yellow-100",
    icon: AlertTriangle,
  },
  info: {
    classes: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
    icon: Info,
  },
};

export function InlineNotice({ message, tone = "success", className = "" }) {
  if (!message) return null;

  const selectedTone = TONES[tone] || TONES.info;
  const Icon = selectedTone.icon;

  return (
    <div
      className={`flex items-start gap-3 rounded-lg border p-4 text-sm leading-6 ${selectedTone.classes} ${className}`}
      role={tone === "error" ? "alert" : "status"}
    >
      <Icon className="mt-0.5 shrink-0" size={18} />
      <span>{message}</span>
    </div>
  );
}
