import { MarkerType } from '@xyflow/react'
import { ROLE_STYLE } from './roleStyle'

const COL_WIDTH = 340
const ROW_HEIGHT = 150

function layoutGraph(rawNodes, rawEdges) {
  const outgoing = new Map(rawNodes.map((n) => [n.id, []]))
  rawEdges.forEach((e) => {
    if (outgoing.has(e.source)) outgoing.get(e.source).push(e.target)
  })

  const depthCache = new Map()
  function depthOf(id, trail) {
    if (depthCache.has(id)) return depthCache.get(id)
    const targets = (outgoing.get(id) || []).filter((t) => outgoing.has(t) && !trail.has(t))
    if (targets.length === 0) {
      depthCache.set(id, 0)
      return 0
    }
    const nextTrail = new Set(trail).add(id)
    const depth = 1 + Math.min(...targets.map((t) => depthOf(t, nextTrail)))
    depthCache.set(id, depth)
    return depth
  }

  const sorted = [...rawNodes].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
  const columns = new Map()
  sorted.forEach((n) => {
    const d = depthOf(n.id, new Set())
    if (!columns.has(d)) columns.set(d, [])
    columns.get(d).push(n)
  })

  const positions = {}
  columns.forEach((column, d) => {
    column.forEach((n, i) => {
      positions[n.id] = { x: d * COL_WIDTH, y: (i - (column.length - 1) / 2) * ROW_HEIGHT }
    })
  })
  return positions
}

// Converts the contract's { nodes, edges } into React Flow nodes and edges.
export function buildFlow(graph) {
  const positions = layoutGraph(graph.nodes, graph.edges)
  const nodes = graph.nodes.map((n) => ({
    id: n.id,
    type: 'report',
    position: positions[n.id],
    data: n,
  }))
  const edges = graph.edges.map((e) => {
    const color = ROLE_STYLE[e.type]?.color || '#94a3b8'
    return {
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      animated: e.type === 'conflicting',
      style: { stroke: color, strokeWidth: 2, strokeDasharray: e.type === 'conflicting' ? '6 4' : undefined },
      markerEnd: { type: MarkerType.ArrowClosed, color },
      labelStyle: { fill: '#e6edf8', fontSize: 11 },
      labelBgStyle: { fill: '#0f1b33' },
      labelBgPadding: [6, 3],
      labelBgBorderRadius: 4,
    }
  })
  return { nodes, edges }
}