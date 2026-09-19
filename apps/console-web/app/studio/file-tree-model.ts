/** Pure model for the Files/Code trees (R-494): no React, no DOM, so it can be exercised directly
 * (e.g. `node --experimental-strip-types`) against a real build's file list. */

export interface FileTreeNode {
  name: string;
  path: string;
  kind: "dir" | "file";
  children: FileTreeNode[];
}

function sortTree(node: FileTreeNode): void {
  node.children.sort((a, b) => {
    if (a.kind !== b.kind) {
      return a.kind === "dir" ? -1 : 1;
    }
    return a.name.localeCompare(b.name);
  });
  node.children.forEach(sortTree);
}

/** Turns the flat path list the agent-engine reports (`apps/web/app/page.tsx`, …) into nested
 * nodes: directories first, then files, both alphabetical. */
export function buildFileTree(paths: string[]): FileTreeNode[] {
  const root: FileTreeNode = { name: "", path: "", kind: "dir", children: [] };
  for (const raw of paths) {
    const parts = raw.split("/").filter(Boolean);
    let node = root;
    parts.forEach((part, index) => {
      const kind = index === parts.length - 1 ? "file" : "dir";
      const path = parts.slice(0, index + 1).join("/");
      let child = node.children.find((entry) => entry.name === part && entry.kind === kind);
      if (!child) {
        child = { name: part, path, kind, children: [] };
        node.children.push(child);
      }
      node = child;
    });
  }
  sortTree(root);
  return root.children;
}

/** Every directory path above a file path, outermost first. */
export function ancestorsOf(path: string): string[] {
  const parts = path.split("/");
  return parts.slice(0, -1).map((_, index) => parts.slice(0, index + 1).join("/"));
}

/** Total number of file leaves under a set of nodes. */
export function countFiles(nodes: FileTreeNode[]): number {
  return nodes.reduce(
    (total, node) => total + (node.kind === "file" ? 1 : countFiles(node.children)),
    0,
  );
}
