/** A hand-rolled, dependency-free syntax tokenizer for the Code tab (R-481).
 *
 * Ports the *approach* (not the exact generated code) of `codegen/nextjs.py`'s own
 * `tokenizeCodeLine`/`normalizeLang` - the tokenizer already shipped, tested, and generated into
 * every app this platform produces, as part of that app's own `CodeBlock` component. Reusing the
 * same regex-driven, single-pass-per-line approach here (rather than adding a syntax-highlighting
 * dependency) matches the icon-decision precedent set in R-475: the console has zero UI
 * dependencies today, and a small, fixed highlighting surface doesn't clear the bar for one.
 *
 * Scoped to what a generated app actually contains: TypeScript/TSX/JavaScript (the bulk of it),
 * JSON, CSS, Markdown, and a plain-text fallback for everything else.
 */

export type CodeTokenType =
  | "plain"
  | "keyword"
  | "string"
  | "comment"
  | "number"
  | "type"
  | "boolean"
  | "function"
  | "variable"
  | "operator"
  | "punctuation";

export interface CodeToken {
  type: CodeTokenType;
  text: string;
}

const TS_KEYWORDS = new Set([
  "const", "let", "var", "function", "return", "if", "else", "for", "while", "do", "switch",
  "case", "default", "break", "continue", "class", "extends", "implements", "interface", "type",
  "enum", "import", "export", "from", "as", "async", "await", "try", "catch", "finally", "throw",
  "new", "delete", "typeof", "instanceof", "in", "of", "yield", "static", "public", "private",
  "protected", "readonly", "abstract", "namespace", "declare", "module", "extends", "super",
  "this", "null", "undefined",
]);

const COMMON_TYPES = new Set([
  "string", "number", "boolean", "any", "void", "unknown", "never", "Promise", "Array", "Record",
  "Object", "Partial", "Pick", "Omit",
]);

/** Maps a file path's extension to a tokenizer language key. Unrecognized extensions fall back to
 * plain text - an honest degradation, not a guess. */
export function languageForPath(path: string): string {
  const ext = path.slice(path.lastIndexOf(".") + 1).toLowerCase();
  switch (ext) {
    case "ts":
    case "tsx":
    case "js":
    case "jsx":
    case "mjs":
    case "cjs":
      return "typescript";
    case "json":
      return "json";
    case "css":
      return "css";
    case "md":
    case "mdx":
      return "markdown";
    default:
      return "plain";
  }
}

/** Tokenizes one line of source into typed spans - pure, single-pass, no lookahead beyond what
 * each token needs. Every generated app already ships the same algorithm's TypeScript twin. */
export function tokenizeCodeLine(line: string, language: string): CodeToken[] {
  if (!line) return [{ type: "plain", text: "" }];
  if (language === "plain" || language === "markdown") {
    return [{ type: "plain", text: line }];
  }

  const tokens: CodeToken[] = [];
  let remaining = line;

  while (remaining.length > 0) {
    // 1. Comments (line comments end the line; CSS has no line-comment form, JSON has none at all)
    if (language !== "css" && language !== "json" && remaining.startsWith("//")) {
      tokens.push({ type: "comment", text: remaining });
      break;
    }
    if ((language === "typescript" || language === "css") && remaining.startsWith("/*")) {
      const closeIdx = remaining.indexOf("*/");
      if (closeIdx !== -1) {
        tokens.push({ type: "comment", text: remaining.slice(0, closeIdx + 2) });
        remaining = remaining.slice(closeIdx + 2);
        continue;
      }
      tokens.push({ type: "comment", text: remaining });
      break;
    }

    // 2. Strings
    const quoteChar = remaining[0];
    if (quoteChar === '"' || quoteChar === "'" || quoteChar === "`") {
      let endIdx = -1;
      let escaped = false;
      for (let i = 1; i < remaining.length; i++) {
        if (remaining[i] === "\\" && !escaped) {
          escaped = true;
          continue;
        }
        if (remaining[i] === quoteChar && !escaped) {
          endIdx = i;
          break;
        }
        escaped = false;
      }
      if (endIdx !== -1) {
        tokens.push({ type: "string", text: remaining.slice(0, endIdx + 1) });
        remaining = remaining.slice(endIdx + 1);
        continue;
      }
      tokens.push({ type: "string", text: remaining });
      break;
    }

    // 3. Numbers
    const numMatch = remaining.match(/^(0x[0-9a-fA-F]+|\d+(\.\d+)?([eE][+-]?\d+)?)\b/);
    if (numMatch) {
      tokens.push({ type: "number", text: numMatch[0] });
      remaining = remaining.slice(numMatch[0].length);
      continue;
    }

    // 4. Identifiers & words
    const wordMatch = remaining.match(/^[a-zA-Z_$][a-zA-Z0-9_$-]*/);
    if (wordMatch) {
      const word = wordMatch[0];
      remaining = remaining.slice(word.length);
      const isFunctionCall = remaining.trimStart().startsWith("(");

      if (language === "typescript" && TS_KEYWORDS.has(word)) {
        tokens.push({ type: "keyword", text: word });
      } else if (language === "typescript" && COMMON_TYPES.has(word)) {
        tokens.push({ type: "type", text: word });
      } else if (word === "true" || word === "false" || word === "null" || word === "undefined") {
        tokens.push({ type: "boolean", text: word });
      } else if (language === "typescript" && isFunctionCall) {
        tokens.push({ type: "function", text: word });
      } else {
        tokens.push({ type: "variable", text: word });
      }
      continue;
    }

    // 5. Whitespace
    const wsMatch = remaining.match(/^\s+/);
    if (wsMatch) {
      tokens.push({ type: "plain", text: wsMatch[0] });
      remaining = remaining.slice(wsMatch[0].length);
      continue;
    }

    // 6. Operators & punctuation
    const opMatch = remaining.match(/^([=!<>+\-*/%&|^~?:]+|[{}[\],;().])/);
    if (opMatch) {
      const op = opMatch[0];
      const isPunctuation = /^[{}[\],;().]/.test(op);
      tokens.push({ type: isPunctuation ? "punctuation" : "operator", text: op });
      remaining = remaining.slice(op.length);
      continue;
    }

    // 7. Fallback: one character, never stall
    tokens.push({ type: "plain", text: remaining[0] });
    remaining = remaining.slice(1);
  }

  return tokens;
}
