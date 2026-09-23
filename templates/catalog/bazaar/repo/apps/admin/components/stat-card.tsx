import { ReactNode } from "react";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: string;
  trendPositive?: boolean;
  icon?: any;
  tone?: "default" | "amber" | "emerald" | "sky" | "rose";
}

export function StatCard({
  title,
  value,
  subtitle,
  trend,
  trendPositive = true,
  icon: Icon,
  tone = "default",
}: StatCardProps) {
  const toneMap = {
    default: "border-slate-800 bg-slate-900/60 text-slate-400",
    amber: "border-amber-500/20 bg-amber-500/5 text-amber-400",
    emerald: "border-emerald-500/20 bg-emerald-500/5 text-emerald-400",
    sky: "border-sky-500/20 bg-sky-500/5 text-sky-400",
    rose: "border-rose-500/20 bg-rose-500/5 text-rose-400",
  };

  return (
    <div className={`p-4 rounded-xl border ${toneMap[tone]} flex flex-col justify-between`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-400">{title}</span>
        {Icon && <Icon className="w-4 h-4 opacity-75" />}
      </div>

      <div className="my-2">
        <div className="text-2xl font-bold font-mono text-white tracking-tight">{value}</div>
      </div>

      {(subtitle || trend) && (
        <div className="flex items-center justify-between text-[11px]">
          {subtitle && <span className="text-slate-400">{subtitle}</span>}
          {trend && (
            <span
              className={`font-semibold font-mono ${
                trendPositive ? "text-emerald-400" : "text-rose-400"
              }`}
            >
              {trend}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
