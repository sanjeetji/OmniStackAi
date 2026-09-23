"use client";

import React, { useMemo } from "react";
import { cn } from "@/lib/utils";

export type QrCodeErrorCorrection = "L" | "M" | "Q" | "H";

// GF(256) Math for Reed-Solomon polynomial error correction
const EXP_TABLE = new Uint8Array(512);
const LOG_TABLE = new Uint8Array(256);

(function initGF256() {
  let x = 1;
  for (let i = 0; i < 255; i++) {
    EXP_TABLE[i] = x;
    EXP_TABLE[i + 255] = x;
    LOG_TABLE[x] = i;
    x <<= 1;
    if (x & 256) x ^= 0x11d;
  }
})();

function gfMultiply(a: number, b: number): number {
  if (a === 0 || b === 0) return 0;
  return EXP_TABLE[LOG_TABLE[a] + LOG_TABLE[b]];
}

function getGeneratorPoly(numEcBytes: number): number[] {
  let poly = [1];
  for (let i = 0; i < numEcBytes; i++) {
    const factor = [1, EXP_TABLE[i]];
    const newPoly = new Array(poly.length + 1).fill(0);
    for (let j = 0; j < poly.length; j++) {
      for (let k = 0; k < 2; k++) {
        newPoly[j + k] ^= gfMultiply(poly[j], factor[k]);
      }
    }
    poly = newPoly;
  }
  return poly;
}

function calculateReedSolomon(dataBytes: number[], numEcBytes: number): number[] {
  const g = getGeneratorPoly(numEcBytes);
  const msg = [...dataBytes, ...new Array(numEcBytes).fill(0)];
  for (let i = 0; i < dataBytes.length; i++) {
    const lead = msg[i];
    if (lead !== 0) {
      for (let j = 0; j < g.length; j++) {
        msg[i + j] ^= gfMultiply(g[j], lead);
      }
    }
  }
  return msg.slice(dataBytes.length);
}

// QR Version table: [version, ecl, size, totalCw, dataCw, ecPerBlock, numBlocks, alignPos]
const QR_TABLE: Record<string, [number, number, number, number, number, number, number]> = {
  "1-L": [1, 21, 26, 19, 7, 1, 0],
  "1-M": [1, 21, 26, 16, 10, 1, 0],
  "1-Q": [1, 21, 26, 13, 13, 1, 0],
  "1-H": [1, 21, 26, 9, 17, 1, 0],
  "2-L": [2, 25, 44, 34, 10, 1, 18],
  "2-M": [2, 25, 44, 28, 16, 1, 18],
  "2-Q": [2, 25, 44, 22, 22, 1, 18],
  "2-H": [2, 25, 44, 16, 28, 1, 18],
  "3-L": [3, 29, 70, 55, 15, 1, 22],
  "3-M": [3, 29, 70, 44, 26, 1, 22],
  "3-Q": [3, 29, 70, 34, 18, 2, 22],
  "3-H": [3, 29, 70, 26, 22, 2, 22],
  "4-L": [4, 33, 100, 80, 20, 1, 26],
  "4-M": [4, 33, 100, 64, 18, 2, 26],
  "4-Q": [4, 33, 100, 48, 26, 2, 26],
  "4-H": [4, 33, 100, 36, 16, 4, 26],
};

function selectVersion(text: string, ecl: QrCodeErrorCorrection): [number, number, number, number, number, number, number] {
  const byteLen = new TextEncoder().encode(text).length;
  for (const v of [1, 2, 3, 4]) {
    const key = `${v}-${ecl}`;
    const entry = QR_TABLE[key];
    if (entry && byteLen <= entry[3] - 3) {
      return entry;
    }
  }
  return QR_TABLE[`4-${ecl}`] || QR_TABLE["4-M"];
}

function encodeData(text: string, dataCw: number): number[] {
  const bytes = Array.from(new TextEncoder().encode(text));
  const bitString: number[] = [];

  // Mode: 0100 (Byte mode)
  bitString.push(0, 1, 0, 0);

  // Character count (8 bits)
  const len = bytes.length;
  for (let i = 7; i >= 0; i--) {
    bitString.push((len >> i) & 1);
  }

  // Data bytes
  for (const b of bytes) {
    for (let i = 7; i >= 0; i--) {
      bitString.push((b >> i) & 1);
    }
  }

  // Terminator
  const remaining = dataCw * 8 - bitString.length;
  const termLen = Math.min(4, Math.max(0, remaining));
  for (let i = 0; i < termLen; i++) bitString.push(0);

  // Pad to byte boundary
  while (bitString.length % 8 !== 0) bitString.push(0);

  // Convert to bytes
  const cws: number[] = [];
  for (let i = 0; i < bitString.length; i += 8) {
    let byte = 0;
    for (let j = 0; j < 8; j++) {
      byte = (byte << 1) | (bitString[i + j] || 0);
    }
    cws.push(byte);
  }

  // Pad bytes 0xEC, 0x11
  const padPatterns = [0xec, 0x11];
  let padIdx = 0;
  while (cws.length < dataCw) {
    cws.push(padPatterns[padIdx % 2]);
    padIdx++;
  }

  return cws;
}

export function generateQrMatrix(text: string, ecl: QrCodeErrorCorrection = "M"): boolean[][] {
  const [, size, , dataCw, ecPerBlock, numBlocks, alignPos] = selectVersion(text, ecl);
  const matrix: (boolean | null)[][] = Array.from({ length: size }, () => new Array(size).fill(null));
  const isFunction: boolean[][] = Array.from({ length: size }, () => new Array(size).fill(false));

  function setModule(r: number, c: number, val: boolean, isFunc = true) {
    if (r >= 0 && r < size && c >= 0 && c < size) {
      matrix[r][c] = val;
      if (isFunc) isFunction[r][c] = true;
    }
  }

  // 1. Finder patterns
  function drawFinderPattern(row: number, col: number) {
    for (let r = -1; r <= 7; r++) {
      for (let c = -1; c <= 7; c++) {
        const nr = row + r;
        const nc = col + c;
        if (nr >= 0 && nr < size && nc >= 0 && nc < size) {
          if (r >= 0 && r <= 6 && c >= 0 && c <= 6) {
            const isBorder = r === 0 || r === 6 || c === 0 || c === 6;
            const isCenter = r >= 2 && r <= 4 && c >= 2 && c <= 4;
            setModule(nr, nc, isBorder || isCenter);
          } else {
            setModule(nr, nc, false);
          }
        }
      }
    }
  }

  drawFinderPattern(0, 0);
  drawFinderPattern(0, size - 7);
  drawFinderPattern(size - 7, 0);

  // 2. Alignment pattern
  if (alignPos > 0) {
    for (let r = -2; r <= 2; r++) {
      for (let c = -2; c <= 2; c++) {
        const nr = alignPos + r;
        const nc = alignPos + c;
        if (matrix[nr][nc] === null) {
          const isBlack = Math.max(Math.abs(r), Math.abs(c)) !== 1;
          setModule(nr, nc, isBlack);
        }
      }
    }
  }

  // 3. Timing patterns
  for (let i = 8; i < size - 8; i++) {
    if (matrix[6][i] === null) setModule(6, i, i % 2 === 0);
    if (matrix[i][6] === null) setModule(i, 6, i % 2 === 0);
  }

  // 4. Dark module
  setModule(size - 8, 8, true);

  // 5. Reserve format info
  for (let i = 0; i < 9; i++) {
    if (matrix[8][i] === null) setModule(8, i, false);
    if (matrix[i][8] === null) setModule(i, 8, false);
  }
  for (let i = size - 8; i < size; i++) {
    if (matrix[8][i] === null) setModule(8, i, false);
    if (matrix[i][8] === null) setModule(i, 8, false);
  }

  // 6. Encode Data & RS EC
  const rawData = encodeData(text, dataCw);
  const dataBlocks: number[][] = [];
  const ecBlocks: number[][] = [];
  const blockSize = Math.floor(dataCw / numBlocks);

  for (let b = 0; b < numBlocks; b++) {
    const start = b * blockSize;
    const end = b === numBlocks - 1 ? dataCw : (b + 1) * blockSize;
    const blockData = rawData.slice(start, end);
    dataBlocks.push(blockData);
    ecBlocks.push(calculateReedSolomon(blockData, ecPerBlock));
  }

  const finalStream: number[] = [];
  for (let i = 0; i < blockSize; i++) {
    for (let b = 0; b < numBlocks; b++) {
      if (i < dataBlocks[b].length) finalStream.push(dataBlocks[b][i]);
    }
  }
  for (let i = 0; i < ecPerBlock; i++) {
    for (let b = 0; b < numBlocks; b++) {
      if (i < ecBlocks[b].length) finalStream.push(ecBlocks[b][i]);
    }
  }

  const finalBits: boolean[] = [];
  for (const byte of finalStream) {
    for (let i = 7; i >= 0; i--) {
      finalBits.push(((byte >> i) & 1) === 1);
    }
  }

  // 7. Place data bits (right to left, zigzag)
  let bitIdx = 0;
  let col = size - 1;
  let goingUp = true;

  while (col > 0) {
    if (col === 6) col--;
    const rows = goingUp
      ? Array.from({ length: size }, (_, i) => size - 1 - i)
      : Array.from({ length: size }, (_, i) => i);

    for (const r of rows) {
      for (const c of [col, col - 1]) {
        if (!isFunction[r][c]) {
          const bit = bitIdx < finalBits.length ? finalBits[bitIdx++] : false;
          const mask = (r + c) % 2 === 0;
          matrix[r][c] = bit !== mask;
        }
      }
    }
    col -= 2;
    goingUp = !goingUp;
  }

  // 8. Write format bits
  const formatBitsMap: Record<QrCodeErrorCorrection, number> = {
    M: 0b101010000010010,
    L: 0b111011111000100,
    H: 0b001011010001001,
    Q: 0b011010101011111,
  };
  const formatInt = formatBitsMap[ecl] || formatBitsMap.M;
  for (let i = 0; i < 15; i++) {
    const bit = ((formatInt >> i) & 1) === 1;
    if (i < 6) setModule(i, 8, bit);
    else if (i === 6) setModule(7, 8, bit);
    else if (i === 7) setModule(8, 8, bit);
    else if (i === 8) setModule(8, 7, bit);
    else setModule(8, 14 - i, bit);

    if (i < 8) setModule(8, size - 1 - i, bit);
    else setModule(size - 15 + i, 8, bit);
  }

  return matrix.map((row) => row.map((cell) => cell ?? false));
}

export interface QrCodeProps extends React.SVGAttributes<SVGSVGElement> {
  value: string;
  size?: number;
  level?: QrCodeErrorCorrection;
  fgColor?: string;
  bgColor?: string;
}

export function QrCode({
  value,
  size = 200,
  level = "M",
  fgColor = "currentColor",
  bgColor = "transparent",
  className,
  ...props
}: QrCodeProps) {
  const matrix = useMemo(() => {
    try {
      return generateQrMatrix(value, level);
    } catch {
      return [];
    }
  }, [value, level]);

  if (!matrix.length) return null;

  const count = matrix.length;
  // 2-module quiet border
  const quietZone = 2;
  const viewBoxSize = count + quietZone * 2;

  // Build SVG path
  let path = "";
  for (let r = 0; r < count; r++) {
    for (let c = 0; c < count; c++) {
      if (matrix[r][c]) {
        path += `M${c + quietZone},${r + quietZone}h1v1h-1z `;
      }
    }
  }

  return (
    <svg
      role="img"
      aria-label={`QR Code for ${value}`}
      viewBox={`0 0 ${viewBoxSize} ${viewBoxSize}`}
      width={size}
      height={size}
      className={cn("shape-rendering-crispEdges block", className)}
      {...props}
    >
      {bgColor !== "transparent" ? (
        <rect width={viewBoxSize} height={viewBoxSize} fill={bgColor} />
      ) : null}
      <path d={path} fill={fgColor} fillRule="evenodd" />
    </svg>
  );
}

export default QrCode;
