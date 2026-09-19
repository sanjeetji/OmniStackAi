"use client";

import { useMemo, useState } from "react";
import { ChevronRight, FileText, Folder, FolderOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { ancestorsOf, buildFileTree, type FileTreeNode } from "./file-tree-model";

export { buildFileTree, ancestorsOf, type FileTreeNode } from "./file-tree-model";

interface LevelProps {
  nodes: FileTreeNode[];
  depth: number;
  selectedFile: string | null;
  isExpanded: (node: FileTreeNode, depth: number) => boolean;
  onToggle: (node: FileTreeNode, depth: number) => void;
  onOpen: (path: string) => void;
}

const ROW =
  "flex w-full min-w-0 items-center gap-1.5 rounded-md py-1 pr-2 text-left text-[13px] leading-5 outline-none transition-colors hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 active:translate-y-px";

function TreeLevel({ nodes, depth, selectedFile, isExpanded, onToggle, onOpen }: LevelProps) {
  return (
    <ul className="grid gap-px">
      {nodes.map((node) => {
        const indent = { paddingLeft: `${6 + depth * 14}px` };
        if (node.kind === "dir") {
          const open = isExpanded(node, depth);
          return (
            <li key={node.path}>
              <button
                type="button"
                aria-expanded={open}
                onClick={() => onToggle(node, depth)}
                className={cn(ROW, "text-foreground")}
                style={indent}
              >
                <ChevronRight
                  className={cn(
                    "size-3.5 shrink-0 text-muted-foreground transition-transform",
                    open && "rotate-90",
                  )}
                  aria-hidden="true"
                />
                {open ? (
                  <FolderOpen className="size-4 shrink-0 text-brand" aria-hidden="true" />
                ) : (
                  <Folder className="size-4 shrink-0 text-brand" aria-hidden="true" />
                )}
                <span className="truncate">{node.name}</span>
              </button>
              {open ? (
                <TreeLevel
                  nodes={node.children}
                  depth={depth + 1}
                  selectedFile={selectedFile}
                  isExpanded={isExpanded}
                  onToggle={onToggle}
                  onOpen={onOpen}
                />
              ) : null}
            </li>
          );
        }
        const selected = node.path === selectedFile;
        return (
          <li key={node.path}>
            <button
              type="button"
              aria-current={selected ? "true" : undefined}
              onClick={() => onOpen(node.path)}
              className={cn(
                ROW,
                selected ? "bg-brand/10 text-foreground" : "text-muted-foreground hover:text-foreground",
              )}
              style={indent}
            >
              <span className="size-3.5 shrink-0" aria-hidden="true" />
              <FileText className="size-4 shrink-0" aria-hidden="true" />
              <span className="truncate font-mono text-xs">{node.name}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

/** A collapsible file tree. Expansion is derived, not synced: top-level directories and every
 * ancestor of the selected file are open by default, and the user's own toggles are kept as
 * overrides - so no effect is needed when `files` or `selectedFile` change. */
export function FileTree({
  files,
  selectedFile,
  onOpen,
  className,
}: {
  files: string[];
  selectedFile: string | null;
  onOpen: (path: string) => void;
  className?: string;
}) {
  const tree = useMemo(() => buildFileTree(files), [files]);
  const selectedAncestors = useMemo(
    () => new Set(selectedFile ? ancestorsOf(selectedFile) : []),
    [selectedFile],
  );
  const [overrides, setOverrides] = useState<Record<string, boolean>>({});

  function isExpanded(node: FileTreeNode, depth: number): boolean {
    return overrides[node.path] ?? (depth === 0 || selectedAncestors.has(node.path));
  }

  function onToggle(node: FileTreeNode, depth: number) {
    const next = !isExpanded(node, depth);
    setOverrides((current) => ({ ...current, [node.path]: next }));
  }

  return (
    <nav aria-label="Files" className={cn("min-w-0", className)}>
      <TreeLevel
        nodes={tree}
        depth={0}
        selectedFile={selectedFile}
        isExpanded={isExpanded}
        onToggle={onToggle}
        onOpen={onOpen}
      />
    </nav>
  );
}
