import React from "react";

// ============================================================
// 雷达图（四维评分）
// ============================================================
interface RadarProps {
  data: { label: string; value: number }[];
  max?: number;
  size?: number;
}

export function RadarChart({ data, max = 10, size = 200 }: RadarProps) {
  const margin = 28; // 为标签留出足够空间
  const cx = size / 2;
  const cy = size / 2;
  const radius = size * 0.32; // 缩小半径，确保标签不溢出
  const n = data.length;
  const angleStep = (2 * Math.PI) / n;
  const startAngle = -Math.PI / 2; // 从顶部开始

  const getPoint = (i: number, val: number, r: number) => {
    const angle = startAngle + i * angleStep;
    const ratio = Math.max(0, Math.min(val / max, 1)); // 限制在 0-1
    return {
      x: cx + r * ratio * Math.cos(angle),
      y: cy + r * ratio * Math.sin(angle),
    };
  };

  // 背景网格
  const gridLevels = [0.25, 0.5, 0.75, 1.0];
  const gridPolygons = gridLevels.map((level) => {
    const points = data
      .map((_, i) => {
        const pt = getPoint(i, max * level, radius);
        return `${pt.x},${pt.y}`;
      })
      .join(" ");
    return points;
  });

  // 数据多边形
  const dataPoints = data
    .map((d, i) => {
      const pt = getPoint(i, d.value, radius);
      return `${pt.x},${pt.y}`;
    })
    .join(" ");

  // 标签位置
  const labelPoints = data.map((d, i) => {
    const angle = startAngle + i * angleStep;
    const labelR = radius + 22;
    return {
      x: cx + labelR * Math.cos(angle),
      y: cy + labelR * Math.sin(angle),
      label: d.label,
      value: d.value,
    };
  });

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="shrink-0"
    >
      {/* 网格 */}
      {gridPolygons.map((pts, i) => (
        <polygon
          key={i}
          points={pts}
          fill="none"
          stroke="#ccc5b9"
          strokeWidth="1"
          opacity={0.4}
        />
      ))}
      {/* 轴线 */}
      {data.map((_, i) => {
        const pt = getPoint(i, max, radius);
        return (
          <line
            key={i}
            x1={cx}
            y1={cy}
            x2={pt.x}
            y2={pt.y}
            stroke="#ccc5b9"
            strokeWidth="1"
            opacity={0.25}
          />
        );
      })}
      {/* 数据多边形 */}
      <polygon
        points={dataPoints}
        fill="#403d39"
        fillOpacity={0.1}
        stroke="#403d39"
        strokeWidth="2"
      />
      {/* 数据点 */}
      {data.map((d, i) => {
        const pt = getPoint(i, d.value, radius);
        const hasData = d.value > 0;
        return (
          <circle
            key={i}
            cx={pt.x}
            cy={pt.y}
            r={hasData ? 4 : 2.5}
            fill={hasData ? "#403d39" : "#ccc5b9"}
            stroke={hasData ? "#fffcf2" : "none"}
            strokeWidth={hasData ? 1.5 : 0}
          />
        );
      })}
      {/* 标签 + 数值 */}
      {labelPoints.map((lp, i) => (
        <g key={i}>
          <text
            x={lp.x}
            y={lp.y - 6}
            textAnchor="middle"
            dominantBaseline="middle"
            className="text-[10px] font-medium"
            fill="#403d39"
            fontFamily="Inter, sans-serif"
          >
            {lp.label}
          </text>
          <text
            x={lp.x}
            y={lp.y + 8}
            textAnchor="middle"
            dominantBaseline="middle"
            className="text-[11px] font-bold font-mono"
            fill={lp.value > 0 ? "#252422" : "#ccc5b9"}
          >
            {lp.value > 0 ? lp.value.toFixed(1) : "--"}
          </text>
        </g>
      ))}
    </svg>
  );
}

// ============================================================
// 柱状图（评分对比）— 保留但标记为可选
// ============================================================
interface BarChartProps {
  data: { label: string; value: number; color?: string }[];
  height?: number;
  max?: number;
}

export function BarChart({ data, height = 140, max = 10 }: BarChartProps) {
  const barWidth = Math.max(24, Math.min(48, 280 / data.length));
  const chartW = data.length * (barWidth + 24) + 20;

  return (
    <svg
      width="100%"
      height={height + 30}
      viewBox={`0 0 ${chartW} ${height + 30}`}
      preserveAspectRatio="xMidYMid meet"
    >
      {/* 基准线 */}
      {[2, 4, 6, 8, 10].map((level) => (
        <line
          key={level}
          x1={10}
          y1={height - (height * level) / max}
          x2={chartW - 10}
          y2={height - (height * level) / max}
          stroke="#ccc5b9"
          strokeWidth="1"
          opacity={0.3}
          strokeDasharray="4 4"
        />
      ))}
      {/* 柱子 */}
      {data.map((d, i) => {
        const barH = Math.max(0, (d.value / max) * height);
        const x = 10 + i * (barWidth + 24) + 12;
        const y = height - barH;
        const hasData = d.value > 0;
        return (
          <g key={i}>
            <rect
              x={x}
              y={y}
              width={barWidth}
              height={barH || 2}
              rx={3}
              fill={hasData ? (d.color || "#403d39") : "#ccc5b9"}
              fillOpacity={hasData ? 0.8 : 0.3}
            />
            <text
              x={x + barWidth / 2}
              y={hasData ? y - 6 : height - 8}
              textAnchor="middle"
              className="text-[11px] font-medium"
              fill={hasData ? "#252422" : "#ccc5b9"}
            >
              {hasData ? d.value.toFixed(1) : "--"}
            </text>
            <text
              x={x + barWidth / 2}
              y={height + 16}
              textAnchor="middle"
              className="text-[11px]"
              fill="#403d39"
              opacity={0.7}
            >
              {d.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
