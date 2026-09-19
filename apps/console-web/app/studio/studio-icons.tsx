import {
  ArrowLeft,
  ChevronDown,
  Code,
  Coins,
  FileText,
  Play,
  RefreshCw,
  SendHorizontal,
  Settings2,
  Square,
  TriangleAlert,
  type LucideProps,
} from "lucide-react";

/* R-493: the hand-drawn icon set from R-475 is retired in favor of Lucide (one stroke family
 * across the whole console). This module stays as a thin shim with the same export names and
 * the same 18px / aria-hidden defaults because the R-475 contract pins the file and the tabs and
 * preview components (R-494's job) still import from it. R-494 replaces those imports and can
 * then retire this file together with that assertion. */

type IconProps = LucideProps;

const base = { size: 18, "aria-hidden": true } as const;

export function BackArrowIcon(props: IconProps) {
  return <ArrowLeft {...base} {...props} />;
}

export function SendIcon(props: IconProps) {
  return <SendHorizontal {...base} {...props} />;
}

export function FileIcon(props: IconProps) {
  return <FileText {...base} {...props} />;
}

export function CodeIcon(props: IconProps) {
  return <Code {...base} {...props} />;
}

export function PlayIcon(props: IconProps) {
  return <Play {...base} {...props} />;
}

export function WarningIcon(props: IconProps) {
  return <TriangleAlert {...base} {...props} />;
}

export function ChevronDownIcon(props: IconProps) {
  return <ChevronDown {...base} {...props} />;
}

export function CreditIcon(props: IconProps) {
  return <Coins {...base} {...props} />;
}

export function StopIcon(props: IconProps) {
  return <Square {...base} {...props} />;
}

export function RefreshIcon(props: IconProps) {
  return <RefreshCw {...base} {...props} />;
}

export function SettingsIcon(props: IconProps) {
  return <Settings2 {...base} {...props} />;
}
