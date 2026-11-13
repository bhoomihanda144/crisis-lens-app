import { useEffect, useMemo, useState } from 'react'
import { ReactFlow, Background, Controls, MiniMap, useNodesState } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import EmptyState from '../ui/EmptyState'
import ReportNode from './ReportNode'
import GraphLegend from './GraphLegend'
import NodeDetails from './NodeDetails'
import { buildFlow } from './graphLayout'
import { ROLE_STYLE } from './roleStyle'

const nodeTypes = { report: ReportNode }

export default function EvidenceGraph({ graph }) {
  const initial = useMemo(() => buildFlow(graph), [graph])
  const [nodes, setNodes, onNodesChange] = useNodesState(initial.nodes)
  const [selectedId, setSelectedId] = useState(null)

  useEffect(() => {
    setNodes(initial.nodes)
  }, [initial, setNodes])

  if (graph.nodes.length === 0) {
    return <EmptyState title="No evidence yet" description="This incident has no reports to draw." />
  }

  const selected = graph.nodes.find((n) => n.id === selectedId) || null

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
      <div
        role="group"
        aria-label="Evidence relationship graph. Use the controls to zoom and drag to pan."
        className="h-[520px] overflow-hidden rounded-xl border border-navy-700 bg-navy-900"
      >
        <ReactFlow
          nodes={nodes}
          edges={initial.edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onNodeClick={(_, node) => setSelectedId(node.id)}
          onPaneClick={() => setSelectedId(null)}
          nodesConnectable={false}
          fitView
          fitViewOptions={{ padding: 0.25 }}
          minZoom={0.3}
          maxZoom={1.5}
          colorMode="dark"
        >
          <Background color="#223660" gap={20} />
          <Controls showInteractive={false} />
          <MiniMap
            pannable
            zoomable
            nodeColor={(n) => ROLE_STYLE[n.data?.role]?.color || '#94a3b8'}
            maskColor="rgba(6, 11, 24, 0.7)"
            style={{ background: '#0a1224' }}
          />
        </ReactFlow>
      </div>

      <div className="space-y-4">
        <NodeDetails node={selected} graph={graph} />
        <GraphLegend />
      </div>
    </div>
  )
}