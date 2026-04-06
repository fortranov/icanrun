"use client";

import React, {
  useState,
  useRef,
  useCallback,
  useMemo,
} from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ControlPoint {
  id: string;
  x: number; // 0..1 normalized
  y: number; // 0..1 normalized (1 = top = max)
}

interface PlanSettings {
  months: number; // 2..9
  maxVolume: number; // 4..30 h/week
  maxIntensity: number; // 50..100 %
  loadWeeks: number; // 1..4
  recoveryDepth: number; // 0.20..0.60 (fraction)
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const VOLUME_COLOR = "#00d4ff";
const INTENSITY_COLOR = "#b44dff";
const CYCLE_COLOR = "#f59e0b";
const RECOVERY_COLOR = "rgba(255,80,80,0.10)";

const VIEWBOX_W = 800;
const VIEWBOX_H = 220;
const PAD = { top: 20, right: 20, bottom: 35, left: 50 };
const CW = VIEWBOX_W - PAD.left - PAD.right; // 730
const CH = VIEWBOX_H - PAD.top - PAD.bottom; // 165

// ---------------------------------------------------------------------------
// Spline math — Catmull-Rom
// ---------------------------------------------------------------------------

/** Evaluate a single Catmull-Rom spline at parameter t in [0,1] between P1 and P2.
 *  P0 and P3 are the surrounding "phantom" points.  */
function catmullRomPoint(
  P0: [number, number],
  P1: [number, number],
  P2: [number, number],
  P3: [number, number],
  t: number
): [number, number] {
  const t2 = t * t;
  const t3 = t2 * t;
  const x =
    0.5 *
    (2 * P1[0] +
      (-P0[0] + P2[0]) * t +
      (2 * P0[0] - 5 * P1[0] + 4 * P2[0] - P3[0]) * t2 +
      (-P0[0] + 3 * P1[0] - 3 * P2[0] + P3[0]) * t3);
  const y =
    0.5 *
    (2 * P1[1] +
      (-P0[1] + P2[1]) * t +
      (2 * P0[1] - 5 * P1[1] + 4 * P2[1] - P3[1]) * t2 +
      (-P0[1] + 3 * P1[1] - 3 * P2[1] + P3[1]) * t3);
  return [x, y];
}

/** Convert normalized [0..1] control points to an SVG path string using Catmull-Rom spline.
 *  Also converts to Bezier cubic segments for SVG rendering. */
function buildSplinePath(pts: ControlPoint[]): string {
  if (pts.length === 0) return "";
  const sorted = [...pts].sort((a, b) => a.x - b.x);

  const toSVG = (nx: number, ny: number): [number, number] => [
    PAD.left + nx * CW,
    PAD.top + (1 - ny) * CH,
  ];

  if (sorted.length === 1) {
    const [sx, sy] = toSVG(sorted[0].x, sorted[0].y);
    return `M ${PAD.left} ${sy} L ${sx} ${sy} L ${PAD.left + CW} ${sy}`;
  }

  // Build ghost points for Catmull-Rom at the extremes
  const pts2D: [number, number][] = sorted.map((p) => toSVG(p.x, p.y));
  const ghost0: [number, number] = [
    pts2D[0][0] - (pts2D[1][0] - pts2D[0][0]),
    pts2D[0][1] - (pts2D[1][1] - pts2D[0][1]),
  ];
  const last = pts2D.length - 1;
  const ghostN: [number, number] = [
    pts2D[last][0] + (pts2D[last][0] - pts2D[last - 1][0]),
    pts2D[last][1] + (pts2D[last][1] - pts2D[last - 1][1]),
  ];

  const allPts = [ghost0, ...pts2D, ghostN];

  const SEGMENTS = 20;
  const pathParts: string[] = [];

  // Starting edge: straight line from chart left edge to first point
  const [startX, startY] = [PAD.left, pts2D[0][1]];
  pathParts.push(`M ${startX} ${startY} L ${pts2D[0][0]} ${pts2D[0][1]}`);

  for (let i = 1; i < pts2D.length; i++) {
    const P0 = allPts[i - 1];
    const P1 = allPts[i];
    const P2 = allPts[i + 1];
    const P3 = allPts[i + 2];

    // Convert Catmull-Rom to Bezier cubic
    const cp1x = P1[0] + (P2[0] - P0[0]) / 6;
    const cp1y = P1[1] + (P2[1] - P0[1]) / 6;
    const cp2x = P2[0] - (P3[0] - P1[0]) / 6;
    const cp2y = P2[1] - (P3[1] - P1[1]) / 6;

    pathParts.push(`C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${P2[0]} ${P2[1]}`);
  }

  // Ending edge: straight line to chart right edge
  pathParts.push(`L ${PAD.left + CW} ${pts2D[last][1]}`);

  return pathParts.join(" ");
}

/** Evaluate the spline Y value at a given normalized X position (0..1). */
function evaluateSplineAtX(pts: ControlPoint[], nx: number): number {
  if (pts.length === 0) return 0;
  const sorted = [...pts].sort((a, b) => a.x - b.x);
  if (sorted.length === 1) return sorted[0].y;
  if (nx <= sorted[0].x) return sorted[0].y;
  if (nx >= sorted[sorted.length - 1].x) return sorted[sorted.length - 1].y;

  // Find segment
  let segIdx = 0;
  for (let i = 0; i < sorted.length - 1; i++) {
    if (nx >= sorted[i].x && nx <= sorted[i + 1].x) {
      segIdx = i;
      break;
    }
  }

  const P1 = sorted[segIdx];
  const P2 = sorted[segIdx + 1];
  const P0 = segIdx > 0 ? sorted[segIdx - 1] : { x: P1.x * 2 - P2.x, y: P1.y };
  const P3 =
    segIdx + 2 < sorted.length
      ? sorted[segIdx + 2]
      : { x: P2.x * 2 - P1.x, y: P2.y };

  const t = (nx - P1.x) / (P2.x - P1.x);
  const [, ry] = catmullRomPoint(
    [P0.x, P0.y],
    [P1.x, P1.y],
    [P2.x, P2.y],
    [P3.x, P3.y],
    t
  );
  return Math.max(0, Math.min(1, ry));
}

// ---------------------------------------------------------------------------
// Cycle modification
// ---------------------------------------------------------------------------

function getCycleMultiplier(
  weekIndex: number,
  loadWeeks: number,
  recoveryDepth: number
): number {
  const cycleLength = loadWeeks + 1;
  const posInCycle = weekIndex % cycleLength;
  if (posInCycle === loadWeeks) {
    return 1 - recoveryDepth;
  }
  return 0.7 + 0.3 * ((posInCycle + 1) / loadWeeks);
}

function isRecoveryWeek(weekIndex: number, loadWeeks: number): boolean {
  return weekIndex % (loadWeeks + 1) === loadWeeks;
}

// ---------------------------------------------------------------------------
// Weekly data computation
// ---------------------------------------------------------------------------

interface WeekData {
  weekIndex: number;
  volumeRaw: number; // 0..1 from spline
  intensityRaw: number; // 0..1 from spline
  volumeMod: number; // after cycle modification
  intensityMod: number; // after cycle modification
  isRecovery: boolean;
}

function computeWeeklyData(
  totalWeeks: number,
  volumePts: ControlPoint[],
  intensityPts: ControlPoint[],
  settings: PlanSettings
): WeekData[] {
  const data: WeekData[] = [];
  for (let i = 0; i < totalWeeks; i++) {
    const nx = totalWeeks <= 1 ? 0 : i / (totalWeeks - 1);
    const vRaw = evaluateSplineAtX(volumePts, nx);
    const iRaw = evaluateSplineAtX(intensityPts, nx);
    const mult = getCycleMultiplier(i, settings.loadWeeks, settings.recoveryDepth);
    data.push({
      weekIndex: i,
      volumeRaw: vRaw,
      intensityRaw: iRaw,
      volumeMod: Math.min(1, vRaw * mult),
      intensityMod: Math.min(1, iRaw * mult),
      isRecovery: isRecoveryWeek(i, settings.loadWeeks),
    });
  }
  return data;
}

// ---------------------------------------------------------------------------
// FuturisticSlider component
// ---------------------------------------------------------------------------

interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  color?: string;
  unit?: string;
  onChange: (v: number) => void;
  format?: (v: number) => string;
}

function FuturisticSlider({
  label,
  value,
  min,
  max,
  step = 1,
  color = VOLUME_COLOR,
  unit = "",
  onChange,
  format,
}: SliderProps) {
  const pct = ((value - min) / (max - min)) * 100;
  const displayVal = format ? format(value) : `${value}${unit}`;

  return (
    <div className="mb-4">
      <div className="flex justify-between items-center mb-1">
        <span
          style={{
            color: "rgba(226,232,240,0.7)",
            fontSize: "11px",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            fontFamily: "monospace",
          }}
        >
          {label}
        </span>
        <span
          style={{
            color,
            fontSize: "13px",
            fontFamily: "monospace",
            fontWeight: 700,
            textShadow: `0 0 8px ${color}`,
          }}
        >
          {displayVal}
        </span>
      </div>
      <div className="relative" style={{ height: "20px" }}>
        {/* Track background */}
        <div
          className="absolute inset-y-0 my-auto rounded-full"
          style={{
            height: "4px",
            left: 0,
            right: 0,
            background: "rgba(255,255,255,0.08)",
          }}
        />
        {/* Filled portion */}
        <div
          className="absolute inset-y-0 my-auto rounded-full"
          style={{
            height: "4px",
            left: 0,
            width: `${pct}%`,
            background: `linear-gradient(90deg, ${color}88, ${color})`,
            boxShadow: `0 0 6px ${color}80`,
            transition: "width 0.05s",
          }}
        />
        {/* Thumb visual */}
        <div
          className="absolute inset-y-0 my-auto rounded-full pointer-events-none"
          style={{
            width: "14px",
            height: "14px",
            left: `calc(${pct}% - 7px)`,
            background: color,
            boxShadow: `0 0 10px ${color}, 0 0 20px ${color}60`,
            border: "2px solid rgba(255,255,255,0.5)",
            transition: "left 0.05s",
          }}
        />
        {/* Actual range input (transparent, on top) */}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="absolute inset-0 w-full opacity-0 cursor-pointer"
          style={{ height: "100%" }}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CurveChart component
// ---------------------------------------------------------------------------

interface CurveChartProps {
  label: string;
  color: string;
  gradientId: string;
  glowId: string;
  controlPoints: ControlPoint[];
  weekData: WeekData[];
  totalWeeks: number;
  valueKey: "volumeMod" | "intensityMod";
  onAddPoint: (x: number, y: number) => void;
  onRemovePoint: (id: string) => void;
  onDragPoint: (id: string, x: number, y: number) => void;
  unitLabel?: string;
  maxValue?: number;
}

function CurveChart({
  label,
  color,
  gradientId,
  glowId,
  controlPoints,
  weekData,
  totalWeeks,
  valueKey,
  onAddPoint,
  onRemovePoint,
  onDragPoint,
  unitLabel = "%",
  maxValue = 100,
}: CurveChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const draggingRef = useRef<string | null>(null);

  const getSVGCoords = useCallback(
    (e: React.MouseEvent | MouseEvent): { nx: number; ny: number } => {
      if (!svgRef.current) return { nx: 0, ny: 0 };
      const pt = svgRef.current.createSVGPoint();
      pt.x = e.clientX;
      pt.y = e.clientY;
      const ctm = svgRef.current.getScreenCTM();
      if (!ctm) return { nx: 0, ny: 0 };
      const svgPt = pt.matrixTransform(ctm.inverse());
      const nx = Math.max(0, Math.min(1, (svgPt.x - PAD.left) / CW));
      const ny = Math.max(0, Math.min(1, 1 - (svgPt.y - PAD.top) / CH));
      return { nx, ny };
    },
    []
  );

  const handleSVGClick = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      // Don't add point if clicking on a control point circle
      if ((e.target as SVGElement).tagName === "circle") return;
      const { nx, ny } = getSVGCoords(e);
      onAddPoint(nx, ny);
    },
    [getSVGCoords, onAddPoint]
  );

  const handlePointMouseDown = useCallback(
    (e: React.MouseEvent, id: string) => {
      e.stopPropagation();
      draggingRef.current = id;

      const onMove = (me: MouseEvent) => {
        if (!draggingRef.current) return;
        const { nx, ny } = getSVGCoords(me);
        onDragPoint(draggingRef.current, nx, ny);
      };

      const onUp = () => {
        draggingRef.current = null;
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
      };

      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
    },
    [getSVGCoords, onDragPoint]
  );

  const handlePointDblClick = useCallback(
    (e: React.MouseEvent, id: string) => {
      e.stopPropagation();
      onRemovePoint(id);
    },
    [onRemovePoint]
  );

  const pathStr = useMemo(
    () => buildSplinePath(controlPoints),
    [controlPoints]
  );

  // Build fill path (close below the curve)
  const fillPath = useMemo(() => {
    if (!pathStr) return "";
    const bottomY = PAD.top + CH;
    return (
      pathStr +
      ` L ${PAD.left + CW} ${bottomY} L ${PAD.left} ${bottomY} Z`
    );
  }, [pathStr]);

  // X-axis grid lines (months)
  const totalMonths = Math.round(totalWeeks / 4.33);
  const gridLines: number[] = [];
  for (let m = 0; m <= totalMonths; m++) {
    gridLines.push(m / totalMonths);
  }

  // Y-axis labels
  const yLabels = [0, 25, 50, 75, 100];

  // Bar width
  const barW = totalWeeks > 0 ? (CW / totalWeeks) * 0.7 : 0;

  return (
    <div
      style={{
        background: "rgba(255,255,255,0.02)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: "12px",
        padding: "12px",
        marginBottom: "16px",
        backdropFilter: "blur(10px)",
      }}
    >
      {/* Label */}
      <div
        style={{
          fontSize: "11px",
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          fontFamily: "monospace",
          color,
          textShadow: `0 0 8px ${color}`,
          marginBottom: "6px",
          paddingLeft: `${PAD.left}px`,
        }}
      >
        {label}
      </div>

      <svg
        ref={svgRef}
        viewBox={`0 0 ${VIEWBOX_W} ${VIEWBOX_H}`}
        preserveAspectRatio="none"
        style={{ width: "100%", display: "block", cursor: "crosshair" }}
        onClick={handleSVGClick}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.25" />
            <stop offset="100%" stopColor={color} stopOpacity="0.02" />
          </linearGradient>
          <filter id={glowId} x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Chart background */}
        <rect
          x={PAD.left}
          y={PAD.top}
          width={CW}
          height={CH}
          fill="rgba(0,0,0,0.15)"
          rx="2"
        />

        {/* Vertical grid lines (months) */}
        {gridLines.map((nx, i) => (
          <line
            key={`vgrid-${i}`}
            x1={PAD.left + nx * CW}
            y1={PAD.top}
            x2={PAD.left + nx * CW}
            y2={PAD.top + CH}
            stroke="rgba(255,255,255,0.04)"
            strokeWidth="1"
          />
        ))}

        {/* Horizontal grid lines (25% intervals) */}
        {yLabels.map((pct) => {
          const sy = PAD.top + (1 - pct / 100) * CH;
          return (
            <line
              key={`hgrid-${pct}`}
              x1={PAD.left}
              y1={sy}
              x2={PAD.left + CW}
              y2={sy}
              stroke="rgba(255,255,255,0.04)"
              strokeWidth="1"
            />
          );
        })}

        {/* Recovery week backgrounds */}
        {weekData.map((w) => {
          if (!w.isRecovery) return null;
          const bx =
            totalWeeks > 1
              ? PAD.left + (w.weekIndex / (totalWeeks - 1)) * CW - CW / totalWeeks / 2
              : PAD.left;
          const bw = totalWeeks > 0 ? CW / totalWeeks : 0;
          return (
            <rect
              key={`rec-${w.weekIndex}`}
              x={bx}
              y={PAD.top}
              width={bw}
              height={CH}
              fill={RECOVERY_COLOR}
            />
          );
        })}

        {/* Weekly bars */}
        {weekData.map((w) => {
          const val = w[valueKey];
          const bx =
            totalWeeks > 1
              ? PAD.left + (w.weekIndex / (totalWeeks - 1)) * CW - barW / 2
              : PAD.left;
          const bh = val * CH;
          const by = PAD.top + CH - bh;
          return (
            <rect
              key={`bar-${w.weekIndex}`}
              x={bx}
              y={by}
              width={barW}
              height={bh}
              fill={w.isRecovery ? "rgba(255,80,80,0.25)" : `${color}22`}
              rx="1"
            />
          );
        })}

        {/* Gradient fill under curve */}
        {fillPath && (
          <path d={fillPath} fill={`url(#${gradientId})`} strokeWidth="0" />
        )}

        {/* Spline curve */}
        {pathStr && (
          <path
            d={pathStr}
            fill="none"
            stroke={color}
            strokeWidth="2.5"
            filter={`url(#${glowId})`}
          />
        )}

        {/* Control points */}
        {[...controlPoints]
          .sort((a, b) => a.x - b.x)
          .map((cp) => {
            const cx = PAD.left + cp.x * CW;
            const cy = PAD.top + (1 - cp.y) * CH;
            return (
              <g key={cp.id}>
                {/* Outer glow ring */}
                <circle
                  cx={cx}
                  cy={cy}
                  r={10}
                  fill="transparent"
                  stroke={color}
                  strokeWidth="1"
                  strokeOpacity="0.3"
                />
                {/* Main dot */}
                <circle
                  cx={cx}
                  cy={cy}
                  r={6}
                  fill={color}
                  stroke="rgba(255,255,255,0.6)"
                  strokeWidth="1.5"
                  style={{
                    cursor: "grab",
                    filter: `drop-shadow(0 0 6px ${color})`,
                  }}
                  onMouseDown={(e) => handlePointMouseDown(e, cp.id)}
                  onDoubleClick={(e) => handlePointDblClick(e, cp.id)}
                />
              </g>
            );
          })}

        {/* X-axis month labels */}
        {gridLines.map((nx, i) => (
          <text
            key={`xlabel-${i}`}
            x={PAD.left + nx * CW}
            y={VIEWBOX_H - 8}
            textAnchor="middle"
            fontSize="9"
            fill="rgba(255,255,255,0.3)"
            fontFamily="monospace"
          >
            {i === 0 ? "0" : `M${i}`}
          </text>
        ))}

        {/* Y-axis labels */}
        {yLabels.map((pct) => {
          const sy = PAD.top + (1 - pct / 100) * CH;
          const val =
            unitLabel === "h"
              ? `${((pct / 100) * maxValue).toFixed(0)}h`
              : `${pct}%`;
          return (
            <text
              key={`ylabel-${pct}`}
              x={PAD.left - 6}
              y={sy + 3}
              textAnchor="end"
              fontSize="9"
              fill="rgba(255,255,255,0.3)"
              fontFamily="monospace"
            >
              {val}
            </text>
          );
        })}
      </svg>

      {/* Hint */}
      <div
        style={{
          fontSize: "9px",
          color: "rgba(255,255,255,0.2)",
          fontFamily: "monospace",
          textAlign: "right",
          paddingRight: `${PAD.right}px`,
          marginTop: "2px",
        }}
      >
        click=add point &nbsp;·&nbsp; double-click=remove &nbsp;·&nbsp; drag=reshape
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// WeeklySummaryChart component
// ---------------------------------------------------------------------------

interface WeeklySummaryChartProps {
  weekData: WeekData[];
  totalWeeks: number;
  maxVolume: number;
  maxIntensity: number;
}

function WeeklySummaryChart({
  weekData,
  totalWeeks,
  maxVolume,
  maxIntensity,
}: WeeklySummaryChartProps) {
  const W = 800;
  const H = 80;
  const PL = 50;
  const PR = 20;
  const PT = 10;
  const PB = 20;
  const IW = W - PL - PR;
  const IH = H - PT - PB;

  const barW = totalWeeks > 0 ? (IW / totalWeeks) * 0.7 : 0;

  return (
    <div
      style={{
        background: "rgba(255,255,255,0.02)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: "12px",
        padding: "12px",
        backdropFilter: "blur(10px)",
      }}
    >
      <div
        style={{
          fontSize: "11px",
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          fontFamily: "monospace",
          color: "rgba(226,232,240,0.5)",
          marginBottom: "6px",
          paddingLeft: `${PL}px`,
        }}
      >
        Weekly Summary
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        style={{ width: "100%", display: "block" }}
      >
        {weekData.map((w) => {
          const bx =
            totalWeeks > 1
              ? PL + (w.weekIndex / (totalWeeks - 1)) * IW - barW / 2
              : PL;
          const vh = w.volumeMod * IH;
          const by = PT + IH - vh;
          const dotY = PT + (1 - w.intensityMod) * IH;
          const dotX =
            totalWeeks > 1
              ? PL + (w.weekIndex / (totalWeeks - 1)) * IW
              : PL;

          return (
            <g key={`sum-${w.weekIndex}`}>
              {/* Recovery bg */}
              {w.isRecovery && (
                <rect
                  x={bx - barW * 0.15}
                  y={PT}
                  width={barW * 1.3}
                  height={IH}
                  fill={RECOVERY_COLOR}
                />
              )}
              {/* Volume bar */}
              <rect
                x={bx}
                y={by}
                width={barW}
                height={vh}
                fill={w.isRecovery ? "rgba(255,80,80,0.4)" : VOLUME_COLOR}
                fillOpacity="0.6"
                rx="1"
              />
              {/* Intensity dot */}
              <circle
                cx={dotX}
                cy={dotY}
                r={2.5}
                fill={INTENSITY_COLOR}
                style={{ filter: `drop-shadow(0 0 3px ${INTENSITY_COLOR})` }}
              />
            </g>
          );
        })}

        {/* Intensity line */}
        {weekData.length > 1 && (
          <polyline
            points={weekData
              .map((w) => {
                const x =
                  totalWeeks > 1
                    ? PL + (w.weekIndex / (totalWeeks - 1)) * IW
                    : PL;
                const y = PT + (1 - w.intensityMod) * IH;
                return `${x},${y}`;
              })
              .join(" ")}
            fill="none"
            stroke={INTENSITY_COLOR}
            strokeWidth="1.5"
            strokeOpacity="0.6"
          />
        )}

        {/* Y axis labels */}
        <text
          x={PL - 4}
          y={PT + 4}
          textAnchor="end"
          fontSize="8"
          fill="rgba(255,255,255,0.3)"
          fontFamily="monospace"
        >
          {maxVolume}h
        </text>
        <text
          x={PL - 4}
          y={PT + IH}
          textAnchor="end"
          fontSize="8"
          fill="rgba(255,255,255,0.3)"
          fontFamily="monospace"
        >
          0h
        </text>

        {/* Legend */}
        <rect x={W - PR - 80} y={PT} width={8} height={8} fill={VOLUME_COLOR} fillOpacity="0.6" rx="1" />
        <text x={W - PR - 68} y={PT + 8} fontSize="8" fill="rgba(255,255,255,0.4)" fontFamily="monospace">VOLUME</text>
        <circle cx={W - PR - 76} cy={PT + 20} r={3} fill={INTENSITY_COLOR} />
        <text x={W - PR - 68} y={PT + 24} fontSize="8" fill="rgba(255,255,255,0.4)" fontFamily="monospace">INTENSITY</text>
      </svg>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Cycle pattern preview
// ---------------------------------------------------------------------------

function CyclePatternPreview({ loadWeeks }: { loadWeeks: number }) {
  const cycleLen = loadWeeks + 1;
  const blocks = Array.from({ length: cycleLen }, (_, i) => ({
    isRecovery: i === loadWeeks,
    label: i === loadWeeks ? "R" : `L${i + 1}`,
  }));

  return (
    <div style={{ display: "flex", gap: "3px", marginTop: "6px" }}>
      {blocks.map((b, i) => (
        <div
          key={i}
          style={{
            flex: 1,
            height: "24px",
            borderRadius: "4px",
            background: b.isRecovery
              ? "rgba(255,80,80,0.3)"
              : `${CYCLE_COLOR}33`,
            border: `1px solid ${b.isRecovery ? "rgba(255,80,80,0.5)" : CYCLE_COLOR + "55"}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "9px",
            fontFamily: "monospace",
            color: b.isRecovery ? "rgba(255,120,120,0.9)" : CYCLE_COLOR,
            letterSpacing: "0.05em",
          }}
        >
          {b.label}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Stat card
// ---------------------------------------------------------------------------

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  const c = color || VOLUME_COLOR;
  return (
    <div
      style={{
        background: "rgba(255,255,255,0.03)",
        border: `1px solid ${c}30`,
        borderRadius: "8px",
        padding: "10px 14px",
        minWidth: "80px",
      }}
    >
      <div
        style={{
          fontSize: "9px",
          fontFamily: "monospace",
          color: "rgba(255,255,255,0.4)",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          marginBottom: "4px",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: "20px",
          fontFamily: "monospace",
          fontWeight: 700,
          color: c,
          textShadow: `0 0 12px ${c}80`,
          lineHeight: 1,
        }}
      >
        {value}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ID generator helper
// ---------------------------------------------------------------------------

function makeId(): string {
  return Math.random().toString(36).slice(2, 9);
}

// ---------------------------------------------------------------------------
// Default control points
// ---------------------------------------------------------------------------

const DEFAULT_VOLUME_PTS: ControlPoint[] = [
  { id: makeId(), x: 0.0, y: 0.3 },
  { id: makeId(), x: 0.2, y: 0.6 },
  { id: makeId(), x: 0.55, y: 1.0 },
  { id: makeId(), x: 0.8, y: 0.75 },
  { id: makeId(), x: 1.0, y: 0.5 },
];

const DEFAULT_INTENSITY_PTS: ControlPoint[] = [
  { id: makeId(), x: 0.0, y: 0.4 },
  { id: makeId(), x: 0.35, y: 0.55 },
  { id: makeId(), x: 0.65, y: 0.9 },
  { id: makeId(), x: 0.85, y: 0.95 },
  { id: makeId(), x: 1.0, y: 0.7 },
];

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function PlanDesignerPage() {
  const [settings, setSettings] = useState<PlanSettings>({
    months: 6,
    maxVolume: 14,
    maxIntensity: 100,
    loadWeeks: 3,
    recoveryDepth: 0.35,
  });

  const [volumePts, setVolumePts] = useState<ControlPoint[]>(DEFAULT_VOLUME_PTS);
  const [intensityPts, setIntensityPts] = useState<ControlPoint[]>(DEFAULT_INTENSITY_PTS);

  const totalWeeks = Math.round(settings.months * 4.33);

  const weekData = useMemo(
    () => computeWeeklyData(totalWeeks, volumePts, intensityPts, settings),
    [totalWeeks, volumePts, intensityPts, settings]
  );

  const totalVolumeHours = useMemo(
    () =>
      weekData.reduce((acc, w) => acc + w.volumeMod * settings.maxVolume, 0),
    [weekData, settings.maxVolume]
  );

  const peakVolume = useMemo(
    () =>
      weekData.reduce((max, w) => Math.max(max, w.volumeMod * settings.maxVolume), 0),
    [weekData, settings.maxVolume]
  );

  const numCycles = Math.floor(totalWeeks / (settings.loadWeeks + 1));

  // Volume control point handlers
  const addVolumePt = useCallback((x: number, y: number) => {
    setVolumePts((pts) => [...pts, { id: makeId(), x, y }]);
  }, []);

  const removeVolumePt = useCallback((id: string) => {
    setVolumePts((pts) => {
      if (pts.length <= 2) return pts;
      return pts.filter((p) => p.id !== id);
    });
  }, []);

  const dragVolumePt = useCallback((id: string, x: number, y: number) => {
    setVolumePts((pts) =>
      pts.map((p) => (p.id === id ? { ...p, x, y } : p))
    );
  }, []);

  // Intensity control point handlers
  const addIntensityPt = useCallback((x: number, y: number) => {
    setIntensityPts((pts) => [...pts, { id: makeId(), x, y }]);
  }, []);

  const removeIntensityPt = useCallback((id: string) => {
    setIntensityPts((pts) => {
      if (pts.length <= 2) return pts;
      return pts.filter((p) => p.id !== id);
    });
  }, []);

  const dragIntensityPt = useCallback((id: string, x: number, y: number) => {
    setIntensityPts((pts) =>
      pts.map((p) => (p.id === id ? { ...p, x, y } : p))
    );
  }, []);

  const updateSetting = <K extends keyof PlanSettings>(
    key: K,
    val: PlanSettings[K]
  ) => setSettings((s) => ({ ...s, [key]: val }));

  return (
    <div
      style={{
        minHeight: "100vh",
        background:
          "radial-gradient(ellipse at 20% 20%, #0d1f3c 0%, #050d1a 60%, #030810 100%)",
        color: "#e2e8f0",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      {/* Grid overlay */}
      <div
        style={{
          position: "fixed",
          inset: 0,
          backgroundImage:
            "linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
          pointerEvents: "none",
          zIndex: 0,
        }}
      />

      <div
        style={{
          position: "relative",
          zIndex: 1,
          maxWidth: "1400px",
          margin: "0 auto",
          padding: "24px 20px",
        }}
      >
        {/* Header */}
        <div style={{ marginBottom: "24px" }}>
          <h1
            style={{
              fontSize: "clamp(24px, 4vw, 42px)",
              fontFamily: "monospace",
              fontWeight: 900,
              letterSpacing: "0.15em",
              background: `linear-gradient(90deg, ${VOLUME_COLOR}, ${INTENSITY_COLOR})`,
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
              margin: 0,
              lineHeight: 1,
            }}
          >
            PLAN DESIGNER
          </h1>
          <div
            style={{
              marginTop: "6px",
              fontSize: "12px",
              fontFamily: "monospace",
              color: "rgba(255,255,255,0.35)",
              letterSpacing: "0.1em",
            }}
          >
            {totalWeeks} WEEKS &nbsp;·&nbsp; {settings.months} MONTHS &nbsp;·&nbsp; CYCLIC PERIODIZATION
          </div>

          {/* Header stat cards */}
          <div
            style={{
              display: "flex",
              gap: "10px",
              marginTop: "16px",
              flexWrap: "wrap",
            }}
          >
            <StatCard
              label="Total Volume"
              value={`${totalVolumeHours.toFixed(0)}h`}
              color={VOLUME_COLOR}
            />
            <StatCard
              label="Peak Week"
              value={`${peakVolume.toFixed(1)}h`}
              color={VOLUME_COLOR}
            />
            <StatCard
              label="Total Weeks"
              value={`${totalWeeks}`}
              color={INTENSITY_COLOR}
            />
            <StatCard
              label="Cycles"
              value={`${numCycles}`}
              color={CYCLE_COLOR}
            />
          </div>
        </div>

        {/* Main layout: charts (left) + sidebar (right) */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 280px",
            gap: "20px",
            alignItems: "start",
          }}
        >
          {/* Charts column */}
          <div>
            <CurveChart
              label="Volume"
              color={VOLUME_COLOR}
              gradientId="volGrad"
              glowId="volGlow"
              controlPoints={volumePts}
              weekData={weekData}
              totalWeeks={totalWeeks}
              valueKey="volumeMod"
              onAddPoint={addVolumePt}
              onRemovePoint={removeVolumePt}
              onDragPoint={dragVolumePt}
              unitLabel="h"
              maxValue={settings.maxVolume}
            />

            <CurveChart
              label="Intensity"
              color={INTENSITY_COLOR}
              gradientId="intGrad"
              glowId="intGlow"
              controlPoints={intensityPts}
              weekData={weekData}
              totalWeeks={totalWeeks}
              valueKey="intensityMod"
              onAddPoint={addIntensityPt}
              onRemovePoint={removeIntensityPt}
              onDragPoint={dragIntensityPt}
              unitLabel="%"
              maxValue={settings.maxIntensity}
            />

            <WeeklySummaryChart
              weekData={weekData}
              totalWeeks={totalWeeks}
              maxVolume={settings.maxVolume}
              maxIntensity={settings.maxIntensity}
            />
          </div>

          {/* Sidebar */}
          <div
            style={{
              position: "sticky",
              top: "20px",
              background: "rgba(255,255,255,0.025)",
              border: "1px solid rgba(255,255,255,0.07)",
              borderRadius: "14px",
              padding: "20px",
              backdropFilter: "blur(12px)",
            }}
          >
            <div
              style={{
                fontSize: "10px",
                letterSpacing: "0.15em",
                textTransform: "uppercase",
                fontFamily: "monospace",
                color: "rgba(255,255,255,0.35)",
                marginBottom: "16px",
              }}
            >
              Controls
            </div>

            <FuturisticSlider
              label="Duration"
              value={settings.months}
              min={2}
              max={9}
              color={VOLUME_COLOR}
              unit=" mo"
              onChange={(v) => updateSetting("months", v)}
              format={(v) => `${v} mo`}
            />

            <FuturisticSlider
              label="Max Volume"
              value={settings.maxVolume}
              min={4}
              max={30}
              color={VOLUME_COLOR}
              unit="h"
              onChange={(v) => updateSetting("maxVolume", v)}
              format={(v) => `${v}h/wk`}
            />

            <FuturisticSlider
              label="Max Intensity"
              value={settings.maxIntensity}
              min={50}
              max={100}
              color={INTENSITY_COLOR}
              unit="%"
              onChange={(v) => updateSetting("maxIntensity", v)}
              format={(v) => `${v}%`}
            />

            {/* Divider */}
            <div
              style={{
                height: "1px",
                background:
                  "linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent)",
                margin: "16px 0",
              }}
            />

            <FuturisticSlider
              label="Load Weeks"
              value={settings.loadWeeks}
              min={1}
              max={4}
              color={CYCLE_COLOR}
              onChange={(v) => updateSetting("loadWeeks", v)}
              format={(v) => `${v} wk`}
            />

            <FuturisticSlider
              label="Recovery Depth"
              value={Math.round(settings.recoveryDepth * 100)}
              min={20}
              max={60}
              color="rgba(255,80,80,0.9)"
              unit="%"
              onChange={(v) => updateSetting("recoveryDepth", v / 100)}
              format={(v) => `${v}% drop`}
            />

            {/* Cycle pattern preview */}
            <div
              style={{
                fontSize: "10px",
                fontFamily: "monospace",
                color: "rgba(255,255,255,0.3)",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                marginTop: "16px",
              }}
            >
              Cycle Pattern
            </div>
            <CyclePatternPreview loadWeeks={settings.loadWeeks} />

            {/* Divider */}
            <div
              style={{
                height: "1px",
                background:
                  "linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent)",
                margin: "16px 0",
              }}
            />

            {/* Stats */}
            <div
              style={{
                display: "grid",
                gap: "8px",
                fontFamily: "monospace",
                fontSize: "11px",
              }}
            >
              {[
                {
                  label: "Total Weeks",
                  val: `${totalWeeks}`,
                  color: INTENSITY_COLOR,
                },
                {
                  label: "Cycles",
                  val: `${numCycles}`,
                  color: CYCLE_COLOR,
                },
                {
                  label: "Total Volume",
                  val: `${totalVolumeHours.toFixed(0)}h`,
                  color: VOLUME_COLOR,
                },
                {
                  label: "Vol Points",
                  val: `${volumePts.length}`,
                  color: VOLUME_COLOR,
                },
                {
                  label: "Int Points",
                  val: `${intensityPts.length}`,
                  color: INTENSITY_COLOR,
                },
              ].map((s) => (
                <div
                  key={s.label}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span style={{ color: "rgba(255,255,255,0.4)" }}>
                    {s.label}
                  </span>
                  <span style={{ color: s.color, fontWeight: 700 }}>
                    {s.val}
                  </span>
                </div>
              ))}
            </div>

            {/* Reset button */}
            <button
              onClick={() => {
                setVolumePts(DEFAULT_VOLUME_PTS.map((p) => ({ ...p, id: makeId() })));
                setIntensityPts(DEFAULT_INTENSITY_PTS.map((p) => ({ ...p, id: makeId() })));
                setSettings({
                  months: 6,
                  maxVolume: 14,
                  maxIntensity: 100,
                  loadWeeks: 3,
                  recoveryDepth: 0.35,
                });
              }}
              style={{
                marginTop: "20px",
                width: "100%",
                padding: "8px 0",
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
                color: "rgba(255,255,255,0.4)",
                fontSize: "10px",
                fontFamily: "monospace",
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                cursor: "pointer",
                transition: "all 0.2s",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background =
                  "rgba(255,255,255,0.08)";
                (e.currentTarget as HTMLButtonElement).style.color =
                  "rgba(255,255,255,0.7)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background =
                  "rgba(255,255,255,0.04)";
                (e.currentTarget as HTMLButtonElement).style.color =
                  "rgba(255,255,255,0.4)";
              }}
            >
              Reset to Defaults
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
