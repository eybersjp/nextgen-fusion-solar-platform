import React, { useRef, useState, useCallback } from 'react';
import { Canvas, useFrame, ThreeElements } from '@react-three/fiber';
import { OrbitControls, Grid, Box, Plane } from '@react-three/drei';
import * as THREE from 'three';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';

interface PanelData {
  id: string;
  position: [number, number, number];
  rotation: [number, number, number];
  selected: boolean;
}

interface SolarPanelProps {
  position: [number, number, number];
  rotation: [number, number, number];
  selected: boolean;
  onClick: () => void;
}

function SolarPanel({ position, rotation, selected, onClick }: SolarPanelProps) {
  const meshRef = useRef<THREE.Mesh>(null!);
  const [hovered, setHovered] = useState(false);

  useFrame((state, delta) => {
    if (hovered && meshRef.current) {
      meshRef.current.rotation.z += delta * 0.1;
    }
  });

  return (
    <mesh
      ref={meshRef}
      position={position}
      rotation={rotation}
      onClick={onClick}
      onPointerOver={() => setHovered(true)}
      onPointerOut={() => setHovered(false)}
    >
      <boxGeometry args={[2, 1, 0.1]} />
      <meshStandardMaterial 
        color={selected ? '#3b82f6' : hovered ? '#60a5fa' : '#1e40af'} 
        transparent
        opacity={0.8}
      />
    </mesh>
  );
}

function RoofSurface() {
  return (
    <mesh position={[0, 0, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[20, 20]} />
      <meshStandardMaterial color="#8b5cf6" transparent opacity={0.3} />
    </mesh>
  );
}

interface SolarPanelViewerProps {
  panels: PanelData[];
  onPanelSelect: (panelId: string) => void;
  onPanelAdd: (position: [number, number, number]) => void;
  onPanelDelete: (panelId: string) => void;
}

export function SolarPanelViewer({ 
  panels, 
  onPanelSelect, 
  onPanelAdd, 
  onPanelDelete 
}: SolarPanelViewerProps) {
  const [selectedPanelId, setSelectedPanelId] = useState<string | null>(null);
  const [isAddingMode, setIsAddingMode] = useState(false);

  const handlePanelClick = useCallback((panelId: string) => {
    setSelectedPanelId(panelId);
    onPanelSelect(panelId);
  }, [onPanelSelect]);

  const handleCanvasClick = useCallback((event: ThreeElements['mesh']) => {
    if (isAddingMode && event.point) {
      const position: [number, number, number] = [
        event.point.x,
        event.point.y + 0.5,
        event.point.z
      ];
      onPanelAdd(position);
      setIsAddingMode(false);
    }
  }, [isAddingMode, onPanelAdd]);

  const handleDeleteSelected = useCallback(() => {
    if (selectedPanelId) {
      onPanelDelete(selectedPanelId);
      setSelectedPanelId(null);
    }
  }, [selectedPanelId, onPanelDelete]);

  return (
    <div className="w-full h-full flex flex-col">
      {/* Control Panel */}
      <Card className="mb-4 p-4">
        <div className="flex gap-2 items-center">
          <Button
            onClick={() => setIsAddingMode(!isAddingMode)}
            variant={isAddingMode ? "default" : "outline"}
            size="sm"
          >
            {isAddingMode ? 'Cancel Add' : 'Add Panel'}
          </Button>
          
          <Button
            onClick={handleDeleteSelected}
            disabled={!selectedPanelId}
            variant="destructive"
            size="sm"
          >
            Delete Selected
          </Button>
          
          <div className="ml-auto text-sm text-gray-600">
            Panels: {panels.length} | Selected: {selectedPanelId || 'None'}
          </div>
        </div>
        
        {isAddingMode && (
          <div className="mt-2 text-sm text-blue-600">
            Click on the roof surface to place a solar panel
          </div>
        )}
      </Card>

      {/* 3D Viewport */}
      <div className="flex-1 border border-gray-300 rounded-lg overflow-hidden">
        <Canvas
          camera={{ position: [10, 10, 10], fov: 60 }}
          style={{ background: '#f0f9ff' }}
        >
          {/* Lighting */}
          <ambientLight intensity={0.6} />
          <directionalLight 
            position={[10, 10, 5]} 
            intensity={1}
            castShadow
            shadow-mapSize-width={2048}
            shadow-mapSize-height={2048}
          />
          
          {/* Controls */}
          <OrbitControls 
            enablePan={true}
            enableZoom={true}
            enableRotate={true}
            maxPolarAngle={Math.PI / 2}
          />
          
          {/* Grid */}
          <Grid 
            args={[20, 20]} 
            cellSize={1} 
            cellThickness={0.5} 
            cellColor="#6b7280" 
            sectionSize={5} 
            sectionThickness={1} 
            sectionColor="#374151"
            fadeDistance={25}
            fadeStrength={1}
          />
          
          {/* Roof Surface */}
          <RoofSurface />
          
          {/* Clickable plane for adding panels */}
          {isAddingMode && (
            <mesh 
              position={[0, 0.01, 0]} 
              rotation={[-Math.PI / 2, 0, 0]}
              onClick={handleCanvasClick}
            >
              <planeGeometry args={[20, 20]} />
              <meshBasicMaterial transparent opacity={0} />
            </mesh>
          )}
          
          {/* Solar Panels */}
          {panels.map((panel) => (
            <SolarPanel
              key={panel.id}
              position={panel.position}
              rotation={panel.rotation}
              selected={panel.id === selectedPanelId}
              onClick={() => handlePanelClick(panel.id)}
            />
          ))}
        </Canvas>
      </div>
    </div>
  );
}

export default SolarPanelViewer;