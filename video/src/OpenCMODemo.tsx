import {
  AbsoluteFill,
  Img,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

/* ─── Scene config ─── */
const SCENES = [
  { file: "01_dashboard.png", label: "Enter URL, Start Scanning" },
  { file: "02_seo.png",       label: "SEO Audit & Core Web Vitals" },
  { file: "03_serp.png",      label: "SERP Keyword Tracking" },
  { file: "04_community.png", label: "Community Monitoring" },
  { file: "05_graph.png",     label: "3D Knowledge Graph" },
  { file: "06_chat.png",      label: "25+ AI Specialist Agents" },
] as const;

const INTRO_DUR  = 75;   // 2.5s
const SCENE_DUR  = 105;  // 3.5s per scene
const OUTRO_DUR  = 75;   // 2.5s
const FADE       = 15;   // fade frames between scenes

export const TOTAL_FRAMES =
  INTRO_DUR + SCENES.length * SCENE_DUR + OUTRO_DUR; // 780

/* ─── Intro slide ─── */
function Intro() {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({ frame, fps, config: { damping: 80 } });
  const titleOpacity = interpolate(frame, [30, 50], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const subtitleOpacity = interpolate(frame, [45, 65], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(135deg, #f8fafc 0%, #eef2ff 50%, #e0e7ff 100%)",
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: 16,
      }}
    >
      <Img
        src={staticFile("logo.png")}
        style={{
          width: 120,
          height: 120,
          transform: `scale(${logoScale})`,
        }}
      />
      <h1
        style={{
          fontSize: 72,
          fontWeight: 800,
          color: "#0f172a",
          fontFamily: "Inter, system-ui, sans-serif",
          opacity: titleOpacity,
          margin: 0,
          letterSpacing: -2,
        }}
      >
        OpenCMO
      </h1>
      <p
        style={{
          fontSize: 24,
          color: "#6366f1",
          fontFamily: "Inter, system-ui, sans-serif",
          fontWeight: 500,
          opacity: subtitleOpacity,
          margin: 0,
        }}
      >
        Open-Source AI Growth System
      </p>
    </AbsoluteFill>
  );
}

/* ─── Screenshot scene with label overlay ─── */
function ScreenScene({ file, label }: { file: string; label: string }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Fade in
  const fadeIn = interpolate(frame, [0, FADE], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // Subtle zoom
  const scale = interpolate(frame, [0, SCENE_DUR], [1.02, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // Label slide up
  const labelY = spring({
    frame: frame - 10,
    fps,
    config: { damping: 100 },
  });
  const labelTranslate = interpolate(labelY, [0, 1], [40, 0]);

  return (
    <AbsoluteFill style={{ backgroundColor: "#0f172a", opacity: fadeIn }}>
      <Img
        src={staticFile(`screenshots/${file}`)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale})`,
        }}
      />
      {/* Bottom gradient overlay */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: 160,
          background:
            "linear-gradient(to top, rgba(15,23,42,0.92) 0%, rgba(15,23,42,0.6) 50%, transparent 100%)",
        }}
      />
      {/* Label */}
      <div
        style={{
          position: "absolute",
          bottom: 40,
          left: 60,
          display: "flex",
          alignItems: "center",
          gap: 16,
          transform: `translateY(${labelTranslate}px)`,
          opacity: labelY,
        }}
      >
        <div
          style={{
            width: 6,
            height: 40,
            borderRadius: 3,
            backgroundColor: "#6366f1",
          }}
        />
        <span
          style={{
            fontSize: 36,
            fontWeight: 700,
            color: "#ffffff",
            fontFamily: "Inter, system-ui, sans-serif",
            letterSpacing: -0.5,
            textShadow: "0 2px 8px rgba(0,0,0,0.4)",
          }}
        >
          {label}
        </span>
      </div>
    </AbsoluteFill>
  );
}

/* ─── Outro slide ─── */
function Outro() {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const badgeScale = spring({
    frame: frame - 25,
    fps,
    config: { damping: 80 },
  });

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(135deg, #f8fafc 0%, #eef2ff 50%, #e0e7ff 100%)",
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        gap: 20,
        opacity: fadeIn,
      }}
    >
      <Img
        src={staticFile("logo.png")}
        style={{ width: 80, height: 80 }}
      />
      <h1
        style={{
          fontSize: 56,
          fontWeight: 800,
          color: "#0f172a",
          fontFamily: "Inter, system-ui, sans-serif",
          margin: 0,
          letterSpacing: -1.5,
        }}
      >
        OpenCMO
      </h1>
      <div
        style={{
          display: "flex",
          gap: 12,
          alignItems: "center",
          transform: `scale(${badgeScale})`,
        }}
      >
        <span
          style={{
            fontSize: 18,
            fontWeight: 600,
            color: "#fff",
            backgroundColor: "#6366f1",
            padding: "8px 20px",
            borderRadius: 12,
            fontFamily: "Inter, system-ui, sans-serif",
          }}
        >
          Open Source
        </span>
        <span
          style={{
            fontSize: 18,
            fontWeight: 600,
            color: "#fff",
            backgroundColor: "#0f172a",
            padding: "8px 20px",
            borderRadius: 12,
            fontFamily: "Inter, system-ui, sans-serif",
          }}
        >
          github.com/Lling0000/OpenCMO
        </span>
      </div>
    </AbsoluteFill>
  );
}

/* ─── Main composition ─── */
export function OpenCMODemo() {
  return (
    <AbsoluteFill style={{ backgroundColor: "#0f172a" }}>
      {/* Intro */}
      <Sequence durationInFrames={INTRO_DUR}>
        <Intro />
      </Sequence>

      {/* Screenshots */}
      {SCENES.map((scene, i) => (
        <Sequence
          key={scene.file}
          from={INTRO_DUR + i * SCENE_DUR}
          durationInFrames={SCENE_DUR}
        >
          <ScreenScene file={scene.file} label={scene.label} />
        </Sequence>
      ))}

      {/* Outro */}
      <Sequence from={INTRO_DUR + SCENES.length * SCENE_DUR}>
        <Outro />
      </Sequence>
    </AbsoluteFill>
  );
}
