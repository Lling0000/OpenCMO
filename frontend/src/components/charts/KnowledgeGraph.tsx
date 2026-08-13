import { useRef, useEffect, useCallback, useState, useMemo } from "react";
import ForceGraph3D from "react-force-graph-3d";
import * as THREE from "three";
import { Link } from "react-router";
import type { GraphData, GraphNode } from "../../api/graph";
import { useI18n } from "../../i18n";

/* ─── Light Elegant Color Palette ─── */
const NODE_COLORS: Record<string, number> = {
  brand: 0x6366f1,            // Indigo
  keyword: 0x0ea5e9,          // Sky blue
  discussion: 0xf59e0b,       // Amber
  serp: 0x10b981,             // Emerald
  competitor: 0xf43f5e,       // Rose
  competitor_keyword: 0xf97316, // Orange
};

const NODE_COLORS_CSS: Record<string, string> = {
  brand: "#6366f1",
  keyword: "#0ea5e9",
  discussion: "#f59e0b",
  serp: "#10b981",
  competitor: "#f43f5e",
  competitor_keyword: "#f97316",
};

const LINK_COLORS: Record<string, string> = {
  has_keyword: "rgba(99, 102, 241, 0.25)",
  has_discussion: "rgba(245, 158, 11, 0.25)",
  serp_rank: "rgba(16, 185, 129, 0.25)",
  competitor_of: "rgba(244, 63, 94, 0.35)",
  comp_keyword: "rgba(249, 115, 22, 0.25)",
  keyword_overlap: "rgba(225, 29, 72, 0.6)",
  expanded_from: "rgba(168, 85, 247, 0.35)", // Purple for expansion edges
};

import type { TranslationKey } from "../../i18n";

const TYPE_LABEL_KEYS: Record<string, TranslationKey> = {
  brand: "graph.type.brand",
  keyword: "graph.type.keyword",
  discussion: "graph.type.discussion",
  serp: "graph.type.serp",
  competitor: "graph.type.competitor",
  competitor_keyword: "graph.type.competitorKeyword",
};

/* ─── Sizing ─── */
function getNodeSize(node: GraphNode): number {
  if (node.type === "brand") return 12;
  if (node.type === "competitor") return 9;
  if (node.type === "discussion") return 3 + Math.min((node.engagement ?? 0) / 30, 6);
  if (node.type === "keyword") return 5;
  if (node.type === "serp") return 4;
  return 3;
}

interface NewNodeData extends GraphNode {
  __isNew?: number; // timestamp when added
  x?: number; y?: number; z?: number; // injected by force-graph at runtime
}

export function KnowledgeGraph({ data }: { data: GraphData }) {
  const fgRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 520 });
  const [selectedNode, setSelectedNode] = useState<NewNodeData | null>(null);
  const [legendOpen, setLegendOpen] = useState(false);
  const { t } = useI18n();
  const typeLabels = Object.fromEntries(
    Object.entries(TYPE_LABEL_KEYS).map(([k, v]) => [k, t(v)])
  );

  // Track previous nodes to detect new ones and animate them
  const prevNodesRef = useRef<Set<string>>(new Set());
  const animatedMeshesRef = useRef<any[]>([]);
  const animationFrameRef = useRef<number | undefined>(undefined);

  // Measure container — listens to actual rendered size so the graph
  // never overflows on mobile and resizes cleanly when the sidebar toggles.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const { width, height } = entries[0]!.contentRect;
      if (width > 0 && height > 0) {
        const w = Math.round(width);
        const h = Math.round(height);
        // Only update when values actually changed — avoids gratuitous re-renders
        // of the heavy ForceGraph3D on unrelated layout shifts.
        setDimensions((prev) => (prev.width === w && prev.height === h ? prev : { width: w, height: h }));
      }
    });
    ro.observe(el);
    // Seed initial dimensions immediately to avoid a one-frame flash at 800×520.
    const rect = el.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      setDimensions({ width: Math.round(rect.width), height: Math.round(rect.height) });
    }
    return () => ro.disconnect();
  }, []);

  // Refit the camera when dimensions change so the graph stays centered on resize.
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    const id = window.setTimeout(() => {
      try {
        fg.zoomToFit(500, 60);
      } catch {
        /* graph not ready */
      }
    }, 200);
    return () => window.clearTimeout(id);
  }, [dimensions.width, dimensions.height]);

  // Update Data & detect newly added nodes
  const graphData = useMemo(() => {
    const currentNodes = new Set(data.nodes.map(n => String(n.id)));
    const hasHistory = prevNodesRef.current.size > 0;
    
    const nodes = data.nodes.map((n) => {
      const isNew = hasHistory && !prevNodesRef.current.has(String(n.id));
      return { 
        ...n, 
        __isNew: isNew ? Date.now() : undefined 
      } as NewNodeData;
    });

    prevNodesRef.current = currentNodes;
    
    return {
      nodes,
      links: data.links.map((l) => ({ ...l })),
    };
  }, [data]);

  // Handle graph auto-rotation & lighting customization
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg || graphData.nodes.length === 0) return;

    // Zoom to fit on initial load. Capture the id so polling-driven graphData
    // updates can't pile up uncancelled timeouts that snap the camera back
    // after a user has manually positioned the view.
    const fitId = window.setTimeout(() => fg.zoomToFit(800, 80), 500);

    // Auto rotate
    const controls = fg.controls();
    if (controls) {
      controls.autoRotate = true;
      controls.autoRotateSpeed = 0.5;
    }

    // Adjust lighting for white background
    const scene = fg.scene();
    if (scene) {
      // Clean up previous custom lights if any
      scene.children = scene.children.filter((c: any) => !c.__customLight);

      // Add a bright, soft ambient light
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
      (ambientLight as any).__customLight = true;
      scene.add(ambientLight);

      // Add a directional light with soft shadows capability (for physical materials)
      const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
      dirLight.position.set(1, 2, 3);
      (dirLight as any).__customLight = true;
      scene.add(dirLight);
    }
    return () => window.clearTimeout(fitId);
  }, [graphData]);

  // Handle animation loop for new node pulses
  useEffect(() => {
    const renderLoop = () => {
      const now = Date.now();
      // Animate all pulse rings
      animatedMeshesRef.current.forEach(mesh => {
        // mesh.userData.startTime is stored when creating the mesh
        const elapsed = now - (mesh.userData.startTime || now);
        const cycle = (elapsed % 2000) / 2000; // 0 to 1 over 2 seconds
        
        // Scale from 1 to 2
        const scale = 1 + cycle;
        mesh.scale.set(scale, scale, scale);
        
        // Fade out as it expands
        if (mesh.material?.transparent) {
          mesh.material.opacity = 0.8 * (1 - cycle);
        }
      });
      animationFrameRef.current = requestAnimationFrame(renderLoop);
    };
    
    animationFrameRef.current = requestAnimationFrame(renderLoop);
    return () => {
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, []);

  const handleNodeClick = useCallback((node: any) => {
    const n = node as NewNodeData;
    setSelectedNode((prev) => (prev?.id === n.id ? null : n));

    const fg = fgRef.current;
    if (!fg) return;
    const controls = fg.controls();
    if (controls) controls.autoRotate = false;

    // Smooth camera focus on the clicked node
    const distance = 100;
    const distRatio = 1 + distance / Math.hypot(n.x || 1, n.y || 1, n.z || 1);
    fg.cameraPosition(
      { x: (n.x || 0) * distRatio, y: (n.y || 0) * distRatio + 20, z: (n.z || 0) * distRatio },
      n,
      800,
    );
  }, []);

  const handleBackgroundClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  /* ─── 3D Object Creation for Light elegant theme ─── */
  const createNodeObject = useCallback((node: any) => {
    const group = new THREE.Group();
    const color = NODE_COLORS[node.type] ?? 0x94a3b8;
    const size = getNodeSize(node as GraphNode);
    const n = node as NewNodeData;

    // Use MeshPhysicalMaterial for a polished, glassy "app-like" look
    const geo = new THREE.SphereGeometry(size, 32, 32);
    const mat = new THREE.MeshPhysicalMaterial({
      color,
      roughness: 0.15,
      transmission: 0.1,  // slight glass effect
      thickness: 1,
      clearcoat: 1.0,     // highly polished
      clearcoatRoughness: 0.1,
    });
    const sphere = new THREE.Mesh(geo, mat);

    // Depth-based styling for expansion-discovered nodes
    const depth = (node as any).depth ?? 0;
    if (depth > 0) {
      const depthScale = Math.max(0.6, 1.0 - depth * 0.1);
      sphere.scale.setScalar(depthScale);
      mat.opacity = Math.max(0.4, 1.0 - depth * 0.12);
      mat.transparent = true;
    }

    group.add(sphere);

    // Frontier indicator: wireframe ring for unexplored expansion nodes
    if (!(node as any).explored && depth > 0) {
      const ringGeo = new THREE.TorusGeometry(size * 0.8 + 2, 0.3, 8, 32);
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0xa855f7,
        transparent: true,
        opacity: 0.5,
        wireframe: true,
      });
      const frontierRing = new THREE.Mesh(ringGeo, ringMat);
      frontierRing.rotation.x = Math.PI / 2;
      group.add(frontierRing);
    }

    // If Brand node, add an elegant double ring
    if (n.type === "brand") {
      const ringGeo = new THREE.TorusGeometry(size + 3, 0.4, 16, 64);
      const ringMat = new THREE.MeshStandardMaterial({ 
        color: 0x6366f1, 
        roughness: 0.2, 
        metalness: 0.8 
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      
      const ringGeo2 = new THREE.TorusGeometry(size + 5, 0.2, 16, 64);
      const ringMat2 = new THREE.MeshStandardMaterial({ 
        color: 0x818cf8, 
        transparent: true,
        opacity: 0.6
      });
      const ring2 = new THREE.Mesh(ringGeo2, ringMat2);
      
      // Rotate them slightly so they aren't completely flat
      ring.rotation.x = Math.PI / 3;
      ring2.rotation.y = Math.PI / 3;
      
      group.add(ring);
      group.add(ring2);
    }

    // If it's a NEW node, add an animated pulse effect
    if (n.__isNew) {
      // Only keep bubbling for a minute or so to not degrade performance long term
      const age = Date.now() - n.__isNew;
      if (age < 60000) {
        const pulseGeo = new THREE.SphereGeometry(size + 0.5, 32, 32);
        const pulseMat = new THREE.MeshBasicMaterial({
          color,
          transparent: true,
          opacity: 0.8,
          side: THREE.BackSide,
        });
        const pulseMesh = new THREE.Mesh(pulseGeo, pulseMat);
        pulseMesh.userData = { startTime: n.__isNew };
        group.add(pulseMesh);
        
        // Save to animated meshes array
        animatedMeshesRef.current.push(pulseMesh);
        
        // Clean up when the object is removed
        group.addEventListener('removed', () => {
          animatedMeshesRef.current = animatedMeshesRef.current.filter(m => m !== pulseMesh);
        });
      }
    }

    return group;
  }, []);

  const getNodeThreeLabel = useCallback((node: any) => {
    const n = node as GraphNode;
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d")!;
    const text = n.label;
    const fontSize = n.type === "brand" ? 36 : 24;
    
    // Measure text to size canvas accurately
    ctx.font = `${n.type === "brand" ? "bold " : ""}${fontSize}px Inter, system-ui, sans-serif`;
    const textWidth = ctx.measureText(text).width;
    canvas.width = textWidth + 32;
    canvas.height = fontSize + 24;
    
    // Draw text with shadow (looks better on light bg)
    ctx.font = `${n.type === "brand" ? "bold " : ""}${fontSize}px Inter, system-ui, sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    
    // Text shadow for legibility over links
    ctx.shadowColor = "rgba(255, 255, 255, 0.8)";
    ctx.shadowBlur = 6;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 0;
    
    // Fill text (dark slate color instead of white)
    ctx.fillStyle = n.type === "brand" ? "#312e81" : "#1e293b";
    
    if (n.type === "brand") {
      ctx.fillStyle = "#4f46e5"; // Indigo for brand text
    } else if ((node as NewNodeData).__isNew) {
      ctx.fillStyle = NODE_COLORS_CSS[n.type] ?? "#1e293b"; // Colored text for new nodes to grab attention
    }
    
    ctx.fillText(text, canvas.width / 2, canvas.height / 2);

    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.minFilter = THREE.LinearFilter; // for crispness
    
    const spriteMat = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthWrite: false, // Prevents z-fighting
    });
    
    const sprite = new THREE.Sprite(spriteMat);
    const scaleFactor = n.type === "brand" ? 1.0 : 0.6;
    sprite.scale.set(canvas.width * 0.08 * scaleFactor, canvas.height * 0.08 * scaleFactor, 1);
    sprite.position.set(0, getNodeSize(n) + 5, 0); // Position slightly above the node
    return sprite;
  }, []);

  const nodeThreeObject = useCallback((node: any) => {
    const group = createNodeObject(node);
    const label = getNodeThreeLabel(node);
    group.add(label);
    return group;
  }, [createNodeObject, getNodeThreeLabel]);

  // Link colors & properties
  const getLinkColor = useCallback((link: any) => {
    return LINK_COLORS[link.type] ?? "rgba(203, 213, 225, 0.4)"; // Slate 300
  }, []);

  const getLinkWidth = useCallback((link: any) => {
    return link.type === "keyword_overlap" ? 2.5 : 0.8;
  }, []);

  const getLinkParticles = useCallback((link: any) => {
    if (link.type === "keyword_overlap") return 4;
    if (link.type === "competitor_of") return 3;
    if (link.type === "expanded_from") return 2;
    if (link.type === "has_keyword") return 1;
    if (link.type === "serp_rank") return 1;
    return 0;
  }, []);

  const getLinkParticleSpeed = useCallback((link: any) => {
    if (link.type === "keyword_overlap") return 0.006;
    if (link.type === "competitor_of") return 0.004;
    if (link.type === "expanded_from") return 0.008; // Faster for discovery
    return 0.003;
  }, []);

  const getLinkParticleColor = useCallback((link: any) => {
    if (link.type === "keyword_overlap") return "#e11d48"; // Rose 600
    if (link.type === "competitor_of") return "#f43f5e"; // Rose 500
    if (link.type === "expanded_from") return "#a855f7"; // Purple 500
    if (link.type === "has_keyword") return "#0ea5e9"; // Sky 500
    if (link.type === "serp_rank") return "#10b981"; // Emerald 500
    return "#94a3b8";
  }, []);

  // HTML Node Label Tooltip (Light Theme Card)
  const getNodeLabelHtml = useCallback((node: any) => {
    const n = node as NewNodeData;
    const typeName = typeLabels[n.type] ?? n.type;
    const isNew = !!n.__isNew;
    
    let html = `<div style="
      background: rgba(255,255,255,0.9);
      backdrop-filter: blur(12px);
      color: #1e293b;
      padding: 12px 16px;
      border-radius: 12px;
      font-size: 13px;
      max-width: 280px;
      line-height: 1.5;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
      border: 1px solid rgba(226, 232, 240, 0.8);
      font-family: Inter, system-ui, sans-serif;
    ">`;
    
    html += `<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">`;
    html += `<div style="font-size:15px; font-weight:700; color: #0f172a;">${n.label}</div>`;
    if (isNew) {
      html += `<span style="background: linear-gradient(135deg, #a855f7, #ef4444); -webkit-background-clip: text; color: transparent; font-size:11px; font-weight:700; letter-spacing:0.5px; animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;">NEW!</span>`;
    }
    html += `</div>`;
    
    // Badge for type
    const badgeColor = NODE_COLORS_CSS[n.type] || "#94a3b8";
    html += `<div style="display:inline-block; padding: 2px 8px; border-radius: 999px; background: ${badgeColor}15; color: ${badgeColor}; font-size: 11px; font-weight: 600; margin-bottom: 8px; border: 1px solid ${badgeColor}30;">${typeName}</div>`;
    
    if (n.platform) html += `<div style="color: #64748b; margin-top: 4px; display:flex; justify-content:space-between;"><span>${t("graph.platform")}</span> <span style="font-weight:500; color:#334155;">${n.platform}</span></div>`;
    if (n.engagement != null) html += `<div style="color: #64748b; margin-top: 4px; display:flex; justify-content:space-between;"><span>${t("graph.engagement")}</span> <span style="font-weight:600; color:#334155;">${n.engagement}</span></div>`;
    if (n.comments != null) html += `<div style="color: #64748b; margin-top: 4px; display:flex; justify-content:space-between;"><span>${t("graph.nodeComments")}</span> <span style="font-weight:500; color:#334155;">${n.comments}</span></div>`;
    if (n.position != null) html += `<div style="color: #64748b; margin-top: 4px; display:flex; justify-content:space-between;"><span>${t("graph.rank")}</span> <span style="font-weight:600; color:#10b981;">#${n.position}</span></div>`;
    if (n.url) html += `<div style="color: #6366f1; margin-top: 8px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:12px;">${n.url}</div>`;
    html += `</div>`;
    return html;
  }, [typeLabels, t]);

  return (
    <div className="relative rounded-2xl border border-zinc-200/50 bg-white shadow-xl overflow-hidden ring-1 ring-zinc-900/5">
      {/* Background Gradient to make it look premium but light */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-indigo-50/30 opacity-80 pointer-events-none" />

      {/* Legend — collapsed on mobile to dots-only; tap to expand. */}
      <div className="absolute top-3 left-3 z-10 max-w-[calc(100%-1.5rem)] rounded-xl bg-white/80 backdrop-blur-xl shadow-lg ring-1 ring-zinc-200/60">
        <button
          type="button"
          onClick={() => setLegendOpen((v) => !v)}
          aria-label={t("graph.controlsHint")}
          aria-expanded={legendOpen}
          className="flex items-center gap-2 px-3 py-2 sm:hidden"
        >
          <span className="flex items-center gap-1">
            {Object.values(NODE_COLORS_CSS).slice(0, 4).map((color) => (
              <span
                key={color}
                className="inline-block h-2.5 w-2.5 rounded-full shadow-sm"
                style={{ backgroundColor: color }}
              />
            ))}
          </span>
          <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-700">
            {legendOpen ? "−" : "+"}
          </span>
        </button>
        <div
          className={`${legendOpen ? "flex" : "hidden"} sm:flex flex-wrap gap-2 sm:gap-2.5 px-3 sm:px-4 py-2.5 sm:py-3`}
        >
          {Object.entries(NODE_COLORS_CSS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-1.5 sm:gap-2">
              <span
                className="inline-block h-2.5 w-2.5 sm:h-3 sm:w-3 rounded-full shadow-sm"
                style={{ backgroundColor: color }}
              />
              <span className="text-[10px] sm:text-[11px] font-semibold text-slate-700 tracking-wide uppercase">
                {typeLabels[type] ?? type}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* "Fit view" button — drag tends to lose users on mobile; one tap recenters. */}
      <button
        type="button"
        onClick={() => {
          const fg = fgRef.current;
          try {
            fg?.zoomToFit(600, 80);
          } catch {
            /* graph not ready */
          }
        }}
        className="absolute top-3 right-3 z-10 inline-flex h-9 items-center gap-1.5 rounded-xl bg-white/80 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-700 shadow-md ring-1 ring-zinc-200/60 backdrop-blur-xl transition hover:bg-white hover:text-slate-900 active:scale-95"
        aria-label={t("graph.controlsHint")}
      >
        ⤢
      </button>

      {/* Controls hint — hidden on mobile (touch users don't have a mouse) */}
      <div className="absolute bottom-3 left-3 z-10 hidden sm:block rounded-xl bg-white/70 px-3 py-2 text-[11px] font-medium text-slate-500 backdrop-blur-xl shadow-sm ring-1 ring-zinc-200/50">
        🖱 {t("graph.controlsHint")}
      </div>

      {/* 3D Graph container — fluid height so it fits any viewport, including phones. */}
      <div
        ref={containerRef}
        className="w-full"
        style={{
          height: "min(720px, calc(100vh - 14rem))",
          minHeight: 360,
          zIndex: 1,
        }}
      >
        <ForceGraph3D
          ref={fgRef}
          graphData={graphData}
          width={dimensions.width}
          height={dimensions.height}
          backgroundColor="rgba(0,0,0,0)" // Transparent to show the CSS gradient behind
          nodeThreeObject={nodeThreeObject}
          nodeLabel={getNodeLabelHtml}
          onNodeClick={handleNodeClick}
          onNodeRightClick={(node: any) => node.url && window.open(node.url, "_blank")}
          onBackgroundClick={handleBackgroundClick}
          linkColor={getLinkColor}
          linkWidth={getLinkWidth}
          linkOpacity={0.8}
          linkDirectionalParticles={getLinkParticles}
          linkDirectionalParticleColor={getLinkParticleColor}
          linkDirectionalParticleWidth={2}
          linkDirectionalParticleSpeed={getLinkParticleSpeed}
          linkCurvature={0.15}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.4}
          cooldownTicks={100}
          enableNodeDrag={true}
          enableNavigationControls={true}
          showNavInfo={false}
        />
      </div>

      {/* Selected Node Info Panel */}
      {selectedNode && (
        <div className="absolute bottom-4 left-4 z-20 w-80 animate-in slide-in-from-bottom-2 duration-300">
          <div className="rounded-2xl border border-white/20 bg-white/90 p-5 shadow-xl backdrop-blur-xl">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div
                  className="h-3 w-3 rounded-full"
                  style={{ backgroundColor: NODE_COLORS_CSS[selectedNode.type] ?? "#94a3b8" }}
                />
                <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  {typeLabels[selectedNode.type] ?? selectedNode.type}
                </span>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="rounded-lg p-1 text-zinc-300 transition hover:bg-zinc-100 hover:text-zinc-600"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <h3 className="text-lg font-bold text-zinc-800 leading-tight">{selectedNode.label}</h3>
            <div className="mt-3 space-y-1.5 text-sm">
              {selectedNode.platform && (
                <div className="flex justify-between"><span className="text-zinc-400">{t("graph.platform")}</span><span className="font-medium text-zinc-700">{selectedNode.platform}</span></div>
              )}
              {selectedNode.engagement != null && (
                <div className="flex justify-between"><span className="text-zinc-400">{t("graph.engagement")}</span><span className="font-medium text-zinc-700">{selectedNode.engagement}</span></div>
              )}
              {selectedNode.comments != null && (
                <div className="flex justify-between"><span className="text-zinc-400">{t("graph.nodeComments")}</span><span className="font-medium text-zinc-700">{selectedNode.comments}</span></div>
              )}
              {selectedNode.position != null && (
                <div className="flex justify-between"><span className="text-zinc-400">{t("graph.rank")}</span><span className="font-medium text-emerald-600 font-bold">#{selectedNode.position}</span></div>
              )}
              {selectedNode.depth != null && selectedNode.depth > 0 && (
                <div className="flex justify-between"><span className="text-zinc-400">{t("graph.discoveryDepth")}</span><span className="font-medium text-zinc-700">{selectedNode.depth}</span></div>
              )}
            </div>
            {selectedNode.type === "competitor" && (
              <Link
                to="../serp"
                relative="path"
                className="mt-4 flex items-center justify-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-indigo-700"
                onClick={(e) => e.stopPropagation()}
              >
                {t("graph.actionViewKeywords")} →
              </Link>
            )}
            {(selectedNode.type === "keyword" || selectedNode.type === "competitor_keyword") && (
              <Link
                to="../serp"
                relative="path"
                className="mt-4 flex items-center justify-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-indigo-700"
                onClick={(e) => e.stopPropagation()}
              >
                {t("graph.actionTrackKeyword")} →
              </Link>
            )}
            {selectedNode.depth != null && selectedNode.depth > 0 && !selectedNode.explored && (
              <div className="mt-4 rounded-xl bg-purple-50 px-3 py-2 text-xs leading-5 text-purple-700">
                {t("graph.actionFrontierReason")}
              </div>
            )}
            {selectedNode.url && (
              <a
                href={selectedNode.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-4 flex items-center justify-center gap-1.5 rounded-xl bg-zinc-900 px-4 py-2 text-xs font-semibold text-white transition hover:bg-zinc-800"
                onClick={(e) => e.stopPropagation()}
              >
                {t("graph.openLink")} →
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
