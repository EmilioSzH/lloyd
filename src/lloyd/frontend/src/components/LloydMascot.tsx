import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { useTheme } from '../hooks/useTheme'

interface LloydMascotProps {
  size?: number
  status?: 'idle' | 'working' | 'thinking' | 'complete' | 'error'
  className?: string
}

interface HairTuftData {
  baseRotZ: number
  phase: number
}

// Mini Three.js implementation for Lloyd mascot
export function LloydMascot({ size = 120, status = 'idle', className = '' }: LloydMascotProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const { resolvedTheme } = useTheme()
  const [statusText, setStatusText] = useState('Ready')

  // Status text rotation
  useEffect(() => {
    const messages: Record<string, string[]> = {
      idle: ['Ready', 'Waiting...', 'Standing by'],
      working: ['Working...', 'Processing...', 'On it!', 'Making progress'],
      thinking: ['Thinking...', 'Analyzing...', 'Considering...'],
      complete: ['Done!', 'Complete', 'Finished'],
      error: ['Oops...', 'Error', 'Issue found'],
    }

    const interval = setInterval(() => {
      const statusMessages = messages[status] || messages.idle
      setStatusText(statusMessages[Math.floor(Math.random() * statusMessages.length)])
    }, 3000)

    return () => clearInterval(interval)
  }, [status])

  useEffect(() => {
    const canvas = canvasRef.current
    const container = containerRef.current
    if (!canvas || !container) return

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(50, 1, 1, 500)
    camera.position.z = 100

    const renderer = new THREE.WebGLRenderer({
      canvas,
      alpha: true,
      antialias: true
    })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(size, size)

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
    scene.add(ambientLight)

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8)
    dirLight.position.set(50, 50, 50)
    scene.add(dirLight)

    // Materials based on theme
    const isDark = resolvedTheme === 'dark'
    const bodyColor = isDark ? 0xd4c4b0 : 0xe8ddd0
    const glassesColor = 0x1a1a1a
    const lensColor = isDark ? 0x87ceeb : 0x6bb3d9
    const hairColor = isDark ? 0x3d2314 : 0x4a2c1a

    const bodyMat = new THREE.MeshLambertMaterial({ color: bodyColor })
    const glassesMat = new THREE.MeshLambertMaterial({ color: glassesColor })
    const lensMat = new THREE.MeshLambertMaterial({
      color: lensColor,
      transparent: true,
      opacity: 0.7
    })
    const hairMat = new THREE.MeshLambertMaterial({ color: hairColor })

    // Character group
    const lloyd = new THREE.Group()

    // Body
    const bodyGeom = new THREE.CylinderGeometry(18, 22, 35, 8)
    const body = new THREE.Mesh(bodyGeom, bodyMat)
    body.position.y = -25
    lloyd.add(body)

    // Head group
    const head = new THREE.Group()
    head.position.y = 5

    // Face
    const faceGeom = new THREE.BoxGeometry(32, 28, 28)
    const face = new THREE.Mesh(faceGeom, bodyMat)
    head.add(face)

    // Glasses
    const glassesGroup = new THREE.Group()
    const lensGeom = new THREE.CylinderGeometry(7, 7, 2, 12)
    lensGeom.rotateX(Math.PI / 2)

    const leftLens = new THREE.Mesh(lensGeom, lensMat)
    leftLens.position.set(10, 2, 15)
    const rightLens = leftLens.clone()
    rightLens.position.x = -10

    const rimGeom = new THREE.TorusGeometry(7.5, 1, 6, 12)
    const leftRim = new THREE.Mesh(rimGeom, glassesMat)
    leftRim.position.set(10, 2, 14)
    const rightRim = leftRim.clone()
    rightRim.position.x = -10

    const bridgeGeom = new THREE.BoxGeometry(6, 1.5, 1.5)
    const bridge = new THREE.Mesh(bridgeGeom, glassesMat)
    bridge.position.set(0, 2, 14)

    glassesGroup.add(leftLens, rightLens, leftRim, rightRim, bridge)
    head.add(glassesGroup)

    // Hair tufts
    const hairPositions = [
      { x: 0, y: 18, z: 5, rot: 0.2 },
      { x: 8, y: 16, z: 3, rot: -0.3 },
      { x: -7, y: 17, z: 4, rot: 0.35 },
    ]

    const hairTufts: THREE.Mesh[] = []
    hairPositions.forEach(pos => {
      const tuftGeom = new THREE.ConeGeometry(3, 10, 4)
      const tuft = new THREE.Mesh(tuftGeom, hairMat)
      tuft.position.set(pos.x, pos.y, pos.z)
      tuft.rotation.z = pos.rot
      tuft.userData = { baseRotZ: pos.rot, phase: Math.random() * Math.PI * 2 } as HairTuftData
      head.add(tuft)
      hairTufts.push(tuft)
    })

    lloyd.add(head)
    scene.add(lloyd)

    // Mouse tracking
    let targetRotY = 0
    let targetRotX = 0

    const handleMouseMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect()
      const mouseX = e.clientX - rect.left - rect.width / 2
      const mouseY = e.clientY - rect.top - rect.height / 2

      // Map to rotation range
      targetRotY = (mouseX / 200) * 0.3
      targetRotX = (mouseY / 200) * 0.2
    }

    document.addEventListener('mousemove', handleMouseMove)

    // Animation loop
    let animationId: number
    const animate = () => {
      animationId = requestAnimationFrame(animate)
      const time = Date.now() * 0.001

      // Smooth head movement
      head.rotation.y += (targetRotY - head.rotation.y) * 0.1
      head.rotation.x += (targetRotX - head.rotation.x) * 0.1

      // Idle bob based on status
      const bobSpeed = status === 'working' ? 2.5 : status === 'thinking' ? 1 : 1.5
      const bobAmount = status === 'error' ? 0.5 : 1.5
      lloyd.position.y = Math.sin(time * bobSpeed) * bobAmount

      // Hair animation
      hairTufts.forEach(tuft => {
        const userData = tuft.userData as HairTuftData
        tuft.rotation.z = userData.baseRotZ + Math.sin(time * 0.5 + userData.phase) * 0.05
      })

      renderer.render(scene, camera)
    }

    animate()

    // Cleanup
    return () => {
      cancelAnimationFrame(animationId)
      document.removeEventListener('mousemove', handleMouseMove)
      renderer.dispose()
    }
  }, [size, resolvedTheme, status])

  const statusColors: Record<string, string> = {
    idle: 'text-[var(--text-tertiary)]',
    working: 'text-accent-500',
    thinking: 'text-amber-500',
    complete: 'text-emerald-500',
    error: 'text-red-500',
  }

  return (
    <div
      ref={containerRef}
      className={`relative flex flex-col items-center ${className}`}
    >
      <canvas
        ref={canvasRef}
        width={size}
        height={size}
        className="rounded-lg"
      />
      <p className={`text-xs mt-1 ${statusColors[status] || statusColors.idle}`}>
        {statusText}
      </p>
    </div>
  )
}
