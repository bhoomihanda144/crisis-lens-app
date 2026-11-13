import { useEffect, useRef } from 'react'
import { Waves, ShieldAlert, Compass, Layers, CheckCircle2, AlertOctagon } from 'lucide-react'

// Topographical tile definitions: [gridX, gridY, baseElevation, label, type]
// type: 'water' | 'lowland' | 'road' | 'hill' | 'hospital' | 'residential'
const TERRAIN_TILES = [
  // Lake basin (Low elevation)
  { x: 1, y: 1, z: 0.3, type: 'water', label: 'Bellandur Lake' },
  { x: 2, y: 1, z: 0.5, type: 'lowland', label: 'Lake Bank East' },
  { x: 3, y: 1, z: 0.8, type: 'lowland', label: 'Wetland Margin' },
  { x: 1, y: 2, z: 0.4, type: 'lowland', label: 'Lake Bank North' },
  { x: 2, y: 2, z: 0.6, type: 'water', label: 'Drainage Canal' },
  { x: 3, y: 2, z: 0.9, type: 'lowland', label: 'Basin Edge' },

  // Arterial Access Corridor (Roads)
  { x: 0, y: 3, z: 1.2, type: 'road', label: 'West Approach' },
  { x: 1, y: 3, z: 0.7, type: 'road', label: 'Lake Road Bridge' }, // Vulnerable
  { x: 2, y: 3, z: 0.8, type: 'road', label: 'Canal Crossing' },   // Vulnerable
  { x: 3, y: 3, z: 1.4, type: 'road', label: 'East Junction' },
  { x: 4, y: 3, z: 1.8, type: 'road', label: 'Ring Road Highway' },

  // Residential high-density sectors
  { x: 0, y: 1, z: 1.5, type: 'residential', label: 'Sector 4 Highrise' },
  { x: 0, y: 2, z: 1.4, type: 'residential', label: 'Outer Settlement' },
  { x: 4, y: 1, z: 2.1, type: 'residential', label: 'East Ward Upper' },
  { x: 4, y: 2, z: 1.9, type: 'residential', label: 'Greenwood Colony' },

  // High elevation safe ground (Medical & Relief)
  { x: 1, y: 0, z: 2.4, type: 'hill', label: 'North Ridge' },
  { x: 2, y: 0, z: 2.6, type: 'hospital', label: 'District Hospital' },
  { x: 3, y: 0, z: 2.3, type: 'hill', label: 'Relief Staging Point' },
  { x: 4, y: 0, z: 2.5, type: 'hill', label: 'Higher Ground Camp' },
]

export default function IsometricFloodMap({
  severity = 3,
  blockedRoads = 2,
  affectedPop = 12000,
  result = null,
  loading = false,
}) {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animationId
    let tick = 0

    const render = () => {
      tick += 0.03
      const width = canvas.width
      const height = canvas.height

      // Clear dark background with radial tactical glow
      ctx.fillStyle = '#0a101d'
      ctx.fillRect(0, 0, width, height)

      // Tactical grid subtle backdrop lines
      ctx.strokeStyle = 'rgba(30, 58, 95, 0.25)'
      ctx.lineWidth = 1
      for (let x = 0; x < width; x += 30) {
        ctx.beginPath()
        ctx.moveTo(x, 0)
        ctx.lineTo(x, height)
        ctx.stroke()
      }
      for (let y = 0; y < height; y += 30) {
        ctx.beginPath()
        ctx.moveTo(0, y)
        ctx.lineTo(width, y)
        ctx.stroke()
      }

      // Isometric projection center
      const originX = width / 2
      const originY = height / 2 - 20
      const tileWidth = 64
      const tileHeight = 32
      const elevationScale = 34

      // Current dynamic water level (based on 1-5 severity)
      const targetWaterHeight = 0.35 + severity * 0.35
      const waveOffset = Math.sin(tick * 1.5) * 0.04
      const currentWaterHeight = targetWaterHeight + waveOffset

      // Convert 3D world (gx, gy, gz) to 2D screen (sx, sy)
      const toIso = (gx, gy, gz) => {
        const sx = originX + (gx - gy) * (tileWidth / 2)
        const sy = originY + (gx + gy) * (tileHeight / 2) - gz * elevationScale
        return { x: sx, y: sy }
      }

      // Draw an isometric 3D prism tile
      const drawIsoPrism = (gx, gy, gz, topColor, leftColor, rightColor) => {
        const halfW = tileWidth / 2
        const halfH = tileHeight / 2
        const topH = gz * elevationScale

        const cx = originX + (gx - gy) * halfW
        const cy = originY + (gx + gy) * halfH

        // Bottom base points (z=0)
        const bTop = { x: cx, y: cy - halfH }
        const bRight = { x: cx + halfW, y: cy }
        const bBottom = { x: cx, y: cy + halfH }
        const bLeft = { x: cx - halfW, y: cy }

        // Top elevated points (z=gz)
        const tTop = { x: bTop.x, y: bTop.y - topH }
        const tRight = { x: bRight.x, y: bRight.y - topH }
        const tBottom = { x: bBottom.x, y: bBottom.y - topH }
        const tLeft = { x: bLeft.x, y: bLeft.y - topH }

        // Left Face
        ctx.fillStyle = leftColor
        ctx.beginPath()
        ctx.moveTo(tLeft.x, tLeft.y)
        ctx.lineTo(tBottom.x, tBottom.y)
        ctx.lineTo(bBottom.x, bBottom.y)
        ctx.lineTo(bLeft.x, bLeft.y)
        ctx.closePath()
        ctx.fill()
        ctx.strokeStyle = 'rgba(15, 23, 42, 0.4)'
        ctx.stroke()

        // Right Face
        ctx.fillStyle = rightColor
        ctx.beginPath()
        ctx.moveTo(tBottom.x, tBottom.y)
        ctx.lineTo(tRight.x, tRight.y)
        ctx.lineTo(bRight.x, bRight.y)
        ctx.lineTo(bBottom.x, bBottom.y)
        ctx.closePath()
        ctx.fill()
        ctx.strokeStyle = 'rgba(15, 23, 42, 0.4)'
        ctx.stroke()

        // Top Face
        ctx.fillStyle = topColor
        ctx.beginPath()
        ctx.moveTo(tTop.x, tTop.y)
        ctx.lineTo(tRight.x, tRight.y)
        ctx.lineTo(tBottom.x, tBottom.y)
        ctx.lineTo(tLeft.x, tLeft.y)
        ctx.closePath()
        ctx.fill()
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)'
        ctx.stroke()

        return { tTop, tRight, tBottom, tLeft, center: { x: cx, y: cy - topH } }
      }

      // Sort tiles from back to front for correct painter's depth
      const sortedTiles = [...TERRAIN_TILES].sort((a, b) => a.x + a.y - (b.x + b.y))

      // Keep track of hospital and vulnerable sectors for evacuation path rendering
      let hospitalPos = null
      let vulnerablePos = null

      // Render terrain blocks
      sortedTiles.forEach((tile) => {
        const isSubmerged = currentWaterHeight >= tile.z

        let topColor = '#1e293b'
        let leftColor = '#0f172a'
        let rightColor = '#172554'

        if (tile.type === 'hospital') {
          topColor = '#065f46'
          leftColor = '#044e39'
          rightColor = '#022c22'
        } else if (tile.type === 'road') {
          if (isSubmerged || (blockedRoads >= 2 && tile.z < 1.0)) {
            topColor = '#b91c1c' // Flooded blocked arterial
            leftColor = '#7f1d1d'
            rightColor = '#450a0a'
          } else {
            topColor = '#475569'
            leftColor = '#334155'
            rightColor = '#1e293b'
          }
        } else if (tile.type === 'residential') {
          topColor = isSubmerged ? '#991b1b' : '#334155'
          leftColor = '#1e293b'
          rightColor = '#0f172a'
        } else if (tile.type === 'hill') {
          topColor = '#1e3a5f'
          leftColor = '#172554'
          rightColor = '#0f172a'
        } else if (tile.type === 'water') {
          topColor = '#0284c7'
          leftColor = '#0369a1'
          rightColor = '#075985'
        }

        const faces = drawIsoPrism(tile.x, tile.y, tile.z, topColor, leftColor, rightColor)

        if (tile.type === 'hospital') {
          hospitalPos = faces.center
          ctx.fillStyle = '#10b981'
          ctx.beginPath()
          ctx.arc(faces.center.x, faces.center.y, 4, 0, Math.PI * 2)
          ctx.fill()
          ctx.fillStyle = '#ffffff'
          ctx.font = 'bold 9px monospace'
          ctx.fillText('HOSPITAL (SAFE)', faces.center.x - 35, faces.center.y - 8)
        } else if (tile.type === 'residential' && isSubmerged) {
          if (!vulnerablePos) vulnerablePos = faces.center
          // Submerged residential warning beacon
          ctx.fillStyle = '#ef4444'
          ctx.beginPath()
          ctx.arc(faces.center.x, faces.center.y, 5 + Math.sin(tick * 3) * 1.5, 0, Math.PI * 2)
          ctx.fill()
          ctx.fillStyle = '#fca5a5'
          ctx.font = 'bold 8px monospace'
          ctx.fillText('EVACUATE', faces.center.x - 20, faces.center.y - 10)
        } else if (tile.type === 'road' && (isSubmerged || (blockedRoads >= 2 && tile.z < 1.0))) {
          ctx.fillStyle = '#f97316'
          ctx.font = 'bold 8px monospace'
          ctx.fillText('CUT-OFF', faces.center.x - 18, faces.center.y - 6)

          // 3D Barrier Crossbars
          ctx.strokeStyle = '#ef4444'
          ctx.lineWidth = 2
          ctx.beginPath()
          ctx.moveTo(faces.center.x - 8, faces.center.y - 4)
          ctx.lineTo(faces.center.x + 8, faces.center.y + 4)
          ctx.moveTo(faces.center.x + 8, faces.center.y - 4)
          ctx.lineTo(faces.center.x - 8, faces.center.y + 4)
          ctx.stroke()
        }
      })

      // 3D Flood Water Volume Overlay (Semi-transparent rising plane)
      if (severity >= 2) {
        ctx.save()
        const waterP1 = toIso(-0.5, -0.5, currentWaterHeight)
        const waterP2 = toIso(4.5, -0.5, currentWaterHeight)
        const waterP3 = toIso(4.5, 4.5, currentWaterHeight)
        const waterP4 = toIso(-0.5, 4.5, currentWaterHeight)

        const gradient = ctx.createLinearGradient(waterP1.x, waterP1.y, waterP3.x, waterP3.y)
        gradient.addColorStop(0, 'rgba(6, 182, 212, 0.42)')
        gradient.addColorStop(0.5, 'rgba(14, 116, 144, 0.48)')
        gradient.addColorStop(1, 'rgba(3, 105, 161, 0.55)')

        ctx.fillStyle = gradient
        ctx.beginPath()
        ctx.moveTo(waterP1.x, waterP1.y)
        ctx.lineTo(waterP2.x, waterP2.y)
        ctx.lineTo(waterP3.x, waterP3.y)
        ctx.lineTo(waterP4.x, waterP4.y)
        ctx.closePath()
        ctx.fill()

        // Water surface outline reflection
        ctx.strokeStyle = 'rgba(165, 243, 252, 0.6)'
        ctx.lineWidth = 1.5
        ctx.stroke()
        ctx.restore()
      }

      // 3D Rescue Units & Evacuation Path when Simulation Results are Present
      if (result) {
        ctx.save()
        // Draw Animated 3D Rescue Boat Units deployed at perimeter
        const boat1 = toIso(1.5, 2.5, currentWaterHeight + 0.05)
        const boat2 = toIso(2.5, 1.5, currentWaterHeight + 0.05)

        const drawBoatMarker = (pt, label) => {
          ctx.fillStyle = '#22d3ee'
          ctx.beginPath()
          ctx.arc(pt.x, pt.y, 6 + Math.sin(tick * 4) * 1.5, 0, Math.PI * 2)
          ctx.fill()
          ctx.fillStyle = '#083344'
          ctx.beginPath()
          ctx.arc(pt.x, pt.y, 3, 0, Math.PI * 2)
          ctx.fill()
          ctx.fillStyle = '#67e8f9'
          ctx.font = 'bold 9px monospace'
          ctx.fillText(`🚤 ${label}`, pt.x - 24, pt.y - 10)
        }

        drawBoatMarker(boat1, 'RESCUE BOAT #1')
        drawBoatMarker(boat2, 'RESCUE BOAT #2')

        // Draw Pulsing Evacuation Corridor vector toward safe hospital
        if (vulnerablePos && hospitalPos) {
          ctx.strokeStyle = 'rgba(16, 185, 129, 0.8)'
          ctx.lineWidth = 2
          ctx.setLineDash([6, 4])
          ctx.lineDashOffset = -tick * 10
          ctx.beginPath()
          ctx.moveTo(vulnerablePos.x, vulnerablePos.y)
          ctx.quadraticCurveTo(originX + 20, originY - 10, hospitalPos.x, hospitalPos.y)
          ctx.stroke()
          ctx.setLineDash([])

          ctx.fillStyle = '#34d399'
          ctx.font = 'bold 8px monospace'
          ctx.fillText('EVACUATION ROUTE', originX - 30, originY - 24)
        }
        ctx.restore()
      }

      // Radar Scan Animation while AI Engine is Computing
      if (loading) {
        ctx.save()
        ctx.strokeStyle = 'rgba(6, 182, 212, 0.7)'
        ctx.lineWidth = 2
        const radarRadius = (tick * 40) % (width / 2)
        ctx.beginPath()
        ctx.arc(originX, originY, radarRadius, 0, Math.PI * 2)
        ctx.stroke()

        ctx.fillStyle = 'rgba(14, 116, 144, 0.85)'
        ctx.font = 'bold 12px monospace'
        ctx.fillText('⚡ AI SIMULATING WATER SURGE & CASCADE HAZARDS...', originX - 160, originY - 40)
        ctx.restore()
      }

      animationId = requestAnimationFrame(render)
    }

    render()

    return () => {
      cancelAnimationFrame(animationId)
    }
  }, [severity, blockedRoads, affectedPop, result, loading])

  // Count how many tiles are currently submerged
  const currentWaterHeight = 0.35 + severity * 0.35
  const submergedCount = TERRAIN_TILES.filter((t) => t.z <= currentWaterHeight).length
  const shortages = result?.results?.shortages || []

  return (
    <div className="relative rounded-xl border border-navy-700 bg-navy-950 overflow-hidden shadow-2xl">
      {/* Top Tactical HUD Header */}
      <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none z-10">
        <div className="flex items-center gap-2 bg-navy-900/85 backdrop-blur-md px-3 py-1.5 rounded-lg border border-navy-700 text-xs">
          <Compass className="h-4 w-4 text-accent animate-spin" style={{ animationDuration: '16s' }} />
          <span className="font-mono font-bold text-text-primary tracking-wider uppercase">
            3D Elevation & Inundation Model
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="bg-navy-900/85 backdrop-blur-md px-2.5 py-1.5 rounded-lg border border-navy-700 font-mono text-xs flex items-center gap-1.5">
            <Waves className="h-3.5 w-3.5 text-cyan-400" />
            <span className="text-text-muted">Inundation Depth:</span>
            <span className="text-cyan-300 font-bold">{(severity * 0.45).toFixed(2)}m</span>
          </div>

          <div
            className={`backdrop-blur-md px-2.5 py-1.5 rounded-lg border font-mono text-xs font-bold flex items-center gap-1.5 ${
              submergedCount > 6
                ? 'bg-red-950/80 border-red-500/50 text-red-300'
                : 'bg-navy-900/85 border-navy-700 text-amber-300'
            }`}
          >
            <ShieldAlert className="h-3.5 w-3.5" />
            <span>{submergedCount} Sectors Submerged</span>
          </div>
        </div>
      </div>

      {/* 3D Canvas Rendering */}
      <div className="w-full flex justify-center items-center py-4">
        <canvas
          ref={canvasRef}
          width={640}
          height={320}
          className="w-full h-auto max-h-[320px] object-contain rounded-lg"
        />
      </div>

      {/* Dynamic Simulation Outcome Alert Bar */}
      {result && (
        <div className="px-4 py-2 bg-navy-900/95 border-t border-b border-navy-750 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
            <span className="font-mono text-emerald-300 font-bold">
              3D Tactical Simulation Applied:
            </span>
            <span className="text-text-muted">{result.results.summary}</span>
          </div>
          {shortages.length > 0 && (
            <span className="text-red-400 font-bold font-mono flex items-center gap-1 shrink-0">
              <AlertOctagon className="h-3.5 w-3.5" /> Shortfall: -{shortages[0].shortfall} {shortages[0].resource}
            </span>
          )}
        </div>
      )}

      {/* Bottom Tactical Map Legend */}
      <div className="p-3 bg-navy-900/90 border-t border-navy-800 flex flex-wrap items-center justify-between text-xs text-text-muted gap-2">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm bg-emerald-600 border border-emerald-400" />
            <span>Highland / Hospital (Safe Ground)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm bg-slate-500 border border-slate-300" />
            <span>Dry Arterial Route</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm bg-red-600 border border-red-400" />
            <span>Submerged / Cut-off Road</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm bg-cyan-500 border border-cyan-300" />
            <span>Rising Flood Water Plane</span>
          </div>
          {result && (
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-cyan-400 animate-ping" />
              <span className="text-cyan-300 font-semibold">Active Rescue Boats Deployed</span>
            </div>
          )}
        </div>

        <div className="font-mono text-[11px] text-accent flex items-center gap-1">
          <Layers className="h-3.5 w-3.5" />
          <span>Real-time Dynamic 3D Projection</span>
        </div>
      </div>
    </div>
  )
}
