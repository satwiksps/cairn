import { ImageResponse } from "next/og";

export const dynamic = "force-static";

export function GET() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: 72,
        color: "#f4f7f5",
        background: "#080a0b",
        fontFamily: "sans-serif",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 18, fontSize: 32 }}>
        <div style={{ width: 20, height: 20, borderRadius: 5, background: "#8ce8b3" }} />
        Cairn
        <span style={{ color: "#78817c", fontSize: 22 }}>v0.1 alpha</span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        <div style={{ color: "#8ce8b3", fontSize: 22, letterSpacing: 3 }}>
          CONTENT-DEFINED RAG INDEXING
        </div>
        <div style={{ maxWidth: 1000, fontSize: 70, lineHeight: 1.06, letterSpacing: -3 }}>
          Incremental indexing for RAG corpora that change.
        </div>
      </div>
      <div style={{ display: "flex", gap: 28, color: "#a8b0ac", fontSize: 22 }}>
        <span>Cache-aware planning</span>
        <span>·</span>
        <span>Transactional indexing</span>
        <span>·</span>
        <span>MIT licensed</span>
      </div>
    </div>,
    { width: 1200, height: 630 },
  );
}
