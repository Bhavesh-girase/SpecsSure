"use client";

import { useMemo, useState, useCallback } from "react";
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  Position,
  Handle,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { GraphData, GraphNode as IGraphNode } from "@/types";
import { ShieldCheck, BookOpen, Layers, X, ExternalLink, Activity } from "lucide-react";
import { getStatusColor } from "@/lib/utils";

// Custom Custom Node Component for Standards
function StandardNodeComponent({ data }: { data: IGraphNode }) {
  const getNodeBorderAndBg = () => {
    switch (data.node_type) {
      case "primary":
        return "border-sky-500 bg-sky-950/80 shadow-sky-500/20";
      case "test_method":
        return "border-emerald-500 bg-emerald-950/80 shadow-emerald-500/20";
      case "safety":
        return "border-rose-500 bg-rose-950/80 shadow-rose-500/20";
      case "installation":
        return "border-amber-500 bg-amber-950/80 shadow-amber-500/20";
      case "superseded":
        return "border-gray-600 bg-gray-900/80 shadow-gray-600/20 opacity-75";
      default:
        return "border-indigo-500 bg-indigo-950/80 shadow-indigo-500/20";
    }
  };

  const getTypeBadge = () => {
    switch (data.node_type) {
      case "primary":
        return <span className="bg-sky-500/20 text-sky-300 border border-sky-500/30 px-1.5 py-0.5 rounded text-[0.75rem] font-bold uppercase">Primary Spec</span>;
      case "test_method":
        return <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-1.5 py-0.5 rounded text-[0.75rem] font-bold uppercase">Test Code</span>;
      case "safety":
        return <span className="bg-rose-500/20 text-rose-300 border border-rose-500/30 px-1.5 py-0.5 rounded text-[0.75rem] font-bold uppercase">Safety Code</span>;
      case "installation":
        return <span className="bg-amber-500/20 text-amber-300 border border-amber-500/30 px-1.5 py-0.5 rounded text-[0.75rem] font-bold uppercase">Installation</span>;
      default:
        return <span className="bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-1.5 py-0.5 rounded text-[0.75rem] font-bold uppercase">Allied Code</span>;
    }
  };

  return (
    <div className={`w-52 p-3 rounded-xl border-2 shadow-lg backdrop-blur-md transition-all hover:scale-105 cursor-pointer ${getNodeBorderAndBg()}`}>
      <Handle type="target" position={Position.Top} className="w-2.5 h-2.5 bg-sky-400" />
      
      <div className="flex items-center justify-between gap-1 mb-1.5">
        <span className="font-mono font-bold text-xs text-ink truncate">{data.is_number}</span>
        {getTypeBadge()}
      </div>

      <p className="text-[0.8125rem] text-slate-300 line-clamp-2 leading-snug">
        {data.title}
      </p>

      <div className="mt-2 pt-1.5 border-t border-slate-700/60 flex items-center justify-between text-[0.75rem] text-slate-400">
        <span className="truncate max-w-[120px]">{data.division || "BIS Standard"}</span>
        <span className={`px-1 rounded text-[0.75rem] ${getStatusColor(data.status)}`}>
          {data.status}
        </span>
      </div>

      <Handle type="source" position={Position.Bottom} className="w-2.5 h-2.5 bg-sky-400" />
    </div>
  );
}

const nodeTypes = {
  standardNode: StandardNodeComponent,
};

interface StandardsGraphProps {
  graphData: GraphData;
}

export function StandardsGraph({ graphData }: StandardsGraphProps) {
  const [selectedNode, setSelectedNode] = useState<IGraphNode | null>(null);

  // Layout nodes radially / hierarchically
  const initialNodes = useMemo(() => {
    if (!graphData.nodes || graphData.nodes.length === 0) return [];
    
    const primary = graphData.nodes.find(n => n.node_type === "primary") || graphData.nodes[0];
    const allied = graphData.nodes.filter(n => n.id !== primary?.id);

    const nodesList = [];
    
    // Center primary node
    if (primary) {
      nodesList.push({
        id: primary.id,
        type: "standardNode",
        position: { x: 300, y: 50 },
        data: primary,
      });
    }

    // Distribute allied nodes in rows
    const spacingX = 240;
    const rowY = 250;
    allied.forEach((node, index) => {
      const col = index % 4;
      const row = Math.floor(index / 4);
      nodesList.push({
        id: node.id,
        type: "standardNode",
        position: {
          x: (col * spacingX) - ((Math.min(allied.length, 4) * spacingX) / 2) + 300,
          y: rowY + (row * 160)
        },
        data: node,
      });
    });

    return nodesList;
  }, [graphData.nodes]);

  const initialEdges = useMemo(() => {
    if (!graphData.edges) return [];
    return graphData.edges.map(e => {
      let strokeColor = "#1d4f93"; // blue default
      let isDashed = false;

      if (e.relationship_type === "test_method") {
        strokeColor = "#047857"; // green
        isDashed = true;
      } else if (e.relationship_type === "safety_requirement") {
        strokeColor = "#be123c"; // red
      } else if (e.relationship_type === "installation_code") {
        strokeColor = "#b45309"; // amber
      }

      return {
        id: e.id,
        source: e.source,
        target: e.target,
        animated: e.relationship_type === "normative_reference",
        style: {
          stroke: strokeColor,
          strokeWidth: 2,
          strokeDasharray: isDashed ? "5,5" : undefined,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: strokeColor,
        },
        label: e.label || e.relationship_type.replace("_", " "),
        labelStyle: { fill: "#475569", fontSize: 10, fontWeight: 500 },
        labelBgStyle: { fill: "#ffffff", fillOpacity: 0.9 },
      };
    });
  }, [graphData.edges]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onNodeClick = useCallback((_: any, node: any) => {
    setSelectedNode(node.data);
  }, []);

  return (
    <div className="relative w-full h-[550px] bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden">
      
      {/* Legend */}
      <div className="absolute top-4 left-4 z-10 p-3 rounded-xl glass-panel text-xs text-slate-300 space-y-1.5 shadow-xl">
        <div className="font-semibold text-slate-100 flex items-center gap-1.5 mb-2">
          <Layers className="w-3.5 h-3.5 text-sky-400" />
          <span>Knowledge Graph Legend</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-sky-500" />
          <span>Primary Specification Standard</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
          <span>Mandatory Test Method Code</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
          <span>Safety & Environmental Code</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
          <span>Installation / Workmanship Code</span>
        </div>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
        fitView
      >
        <Controls />
        <MiniMap
          nodeColor={(n) => {
            const data = n.data as unknown as IGraphNode;
            if (data.node_type === "primary") return "#0284c7";
            if (data.node_type === "test_method") return "#047857";
            if (data.node_type === "safety") return "#ef4444";
            return "#6366f1";
          }}
          className="!bg-slate-900 !border !border-slate-800 rounded-lg overflow-hidden"
        />
        <Background color="#d5deea" gap={16} />
      </ReactFlow>

      {/* Node Inspector Drawer */}
      {selectedNode && (
        <div className="absolute top-0 right-0 h-full w-80 bg-slate-900/95 border-l border-slate-800 p-6 z-20 backdrop-blur-xl shadow-2xl flex flex-col justify-between animate-in slide-in-from-right duration-200">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <span className="font-mono text-sm font-bold text-sky-400">
                {selectedNode.is_number}
              </span>
              <button
                onClick={() => setSelectedNode(null)}
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-ink"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="mt-4 space-y-4">
              <div>
                <h4 className="text-xs uppercase font-semibold text-slate-400">Title</h4>
                <p className="text-sm font-semibold text-ink mt-1 leading-snug">
                  {selectedNode.title}
                </p>
              </div>

              <div>
                <h4 className="text-xs uppercase font-semibold text-slate-400">Classification</h4>
                <span className="inline-block mt-1 text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-200 font-mono">
                  {selectedNode.division || "BIS Division"}
                </span>
              </div>

              <div>
                <h4 className="text-xs uppercase font-semibold text-slate-400">Status</h4>
                <span className={`inline-block mt-1 text-xs px-2 py-0.5 rounded ${getStatusColor(selectedNode.status)}`}>
                  {selectedNode.status.toUpperCase()}
                </span>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800">
            <a
              href={`https://standards.bis.gov.in`}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full py-2.5 px-4 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-medium text-xs flex items-center justify-center gap-1.5 transition-colors shadow-lg shadow-sky-600/20"
            >
              <span>Verify on BIS Portal</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
