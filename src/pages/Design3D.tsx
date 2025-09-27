import React, { useState, useCallback, useEffect } from 'react';
import { SolarPanelViewer } from '../components/3d/SolarPanelViewer';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Spinner } from '../components/ui/Spinner';

interface PanelData {
  id: string;
  position: [number, number, number];
  rotation: [number, number, number];
  selected: boolean;
}

interface ProjectData {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
}

interface IrradianceData {
  total_irradiance: number;
  panel_efficiency: number;
  energy_yield: number;
  performance_ratio: number;
}

export function Design3D() {
  const [panels, setPanels] = useState<PanelData[]>([]);
  const [selectedPanelId, setSelectedPanelId] = useState<string | null>(null);
  const [projectData, setProjectData] = useState<ProjectData>({
    id: 'demo-project-1',
    name: 'Demo Solar Installation',
    latitude: -26.2041,
    longitude: 28.0473
  });
  const [irradianceData, setIrradianceData] = useState<IrradianceData | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [layoutId, setLayoutId] = useState<string | null>(null);

  // Load initial demo panels
  useEffect(() => {
    const demoPanel: PanelData = {
      id: 'panel-1',
      position: [0, 0.5, 0],
      rotation: [0, 0, 0],
      selected: false
    };
    setPanels([demoPanel]);
  }, []);

  const handlePanelSelect = useCallback((panelId: string) => {
    setSelectedPanelId(panelId);
    setPanels(prev => prev.map(panel => ({
      ...panel,
      selected: panel.id === panelId
    })));
  }, []);

  const handlePanelAdd = useCallback((position: [number, number, number]) => {
    const newPanel: PanelData = {
      id: `panel-${Date.now()}`,
      position,
      rotation: [0, 0, 0],
      selected: false
    };
    setPanels(prev => [...prev, newPanel]);
  }, []);

  const handlePanelDelete = useCallback((panelId: string) => {
    setPanels(prev => prev.filter(panel => panel.id !== panelId));
    if (selectedPanelId === panelId) {
      setSelectedPanelId(null);
    }
  }, [selectedPanelId]);

  const calculateIrradiance = useCallback(async () => {
    if (!layoutId) {
      alert('Please save the layout first');
      return;
    }

    setIsCalculating(true);
    try {
      const response = await fetch(`http://localhost:8000/api/v1/3d/irradiance-calculation/${layoutId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setIrradianceData(data);
      } else {
        console.error('Failed to calculate irradiance');
        alert('Failed to calculate irradiance');
      }
    } catch (error) {
      console.error('Error calculating irradiance:', error);
      alert('Error calculating irradiance');
    } finally {
      setIsCalculating(false);
    }
  }, [layoutId]);

  const saveLayout = useCallback(async () => {
    setIsSaving(true);
    try {
      const layoutData = {
        project_id: projectData.id,
        building_model: {
          geometry: {
            vertices: [
              [-10, 0, -10], [10, 0, -10], [10, 0, 10], [-10, 0, 10],
              [-10, 3, -10], [10, 3, -10], [10, 3, 10], [-10, 3, 10]
            ],
            faces: [
              [0, 1, 2, 3], // bottom
              [4, 7, 6, 5], // top
              [0, 4, 5, 1], // front
              [2, 6, 7, 3], // back
              [0, 3, 7, 4], // left
              [1, 5, 6, 2]  // right
            ]
          },
          roof_surfaces: [
            {
              surface_id: 'roof-1',
              area: 400,
              tilt_angle: 0,
              azimuth: 180
            }
          ]
        },
        panel_layout: panels.map(panel => ({
          panel_id: panel.id,
          position: {
            x: panel.position[0],
            y: panel.position[1],
            z: panel.position[2]
          },
          rotation: {
            x: panel.rotation[0],
            y: panel.rotation[1],
            z: panel.rotation[2]
          },
          panel_type: 'standard-400w'
        })),
        simulation_params: {
          latitude: projectData.latitude,
          longitude: projectData.longitude,
          timezone: 'Africa/Johannesburg'
        }
      };

      const response = await fetch('http://localhost:8000/api/v1/3d/3d-layout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(layoutData),
      });

      if (response.ok) {
        const result = await response.json();
        setLayoutId(result.layout_id);
        alert(`Layout saved successfully! Energy output: ${result.energy_output.toFixed(2)} kWh/year`);
      } else {
        console.error('Failed to save layout');
        alert('Failed to save layout');
      }
    } catch (error) {
      console.error('Error saving layout:', error);
      alert('Error saving layout');
    } finally {
      setIsSaving(false);
    }
  }, [panels, projectData]);

  const exportCAD = useCallback(async () => {
    if (!layoutId) {
      alert('Please save the layout first');
      return;
    }

    try {
      const exportData = {
        layout_id: layoutId,
        format: 'dxf',
        include_annotations: true,
        coordinate_system: 'local'
      };

      const response = await fetch('http://localhost:8000/api/v1/3d/export-cad', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(exportData),
      });

      if (response.ok) {
        const result = await response.json();
        window.open(result.download_url, '_blank');
      } else {
        console.error('Failed to export CAD');
        alert('Failed to export CAD');
      }
    } catch (error) {
      console.error('Error exporting CAD:', error);
      alert('Error exporting CAD');
    }
  }, [layoutId]);

  return (
    <div className="h-screen flex flex-col p-4">
      <div className="mb-4">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">3D Solar Design</h1>
        <p className="text-gray-600">Design and optimize solar panel layouts in 3D</p>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* 3D Viewer */}
        <div className="lg:col-span-3">
          <SolarPanelViewer
            panels={panels}
            onPanelSelect={handlePanelSelect}
            onPanelAdd={handlePanelAdd}
            onPanelDelete={handlePanelDelete}
          />
        </div>

        {/* Control Panel */}
        <div className="space-y-4">
          {/* Project Info */}
          <Card className="p-4">
            <h3 className="font-semibold mb-3">Project Information</h3>
            <div className="space-y-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Project Name
                </label>
                <Input
                  value={projectData.name}
                  onChange={(e) => setProjectData(prev => ({ ...prev, name: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Latitude
                </label>
                <Input
                  type="number"
                  step="0.0001"
                  value={projectData.latitude}
                  onChange={(e) => setProjectData(prev => ({ ...prev, latitude: parseFloat(e.target.value) }))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Longitude
                </label>
                <Input
                  type="number"
                  step="0.0001"
                  value={projectData.longitude}
                  onChange={(e) => setProjectData(prev => ({ ...prev, longitude: parseFloat(e.target.value) }))}
                />
              </div>
            </div>
          </Card>

          {/* Actions */}
          <Card className="p-4">
            <h3 className="font-semibold mb-3">Actions</h3>
            <div className="space-y-2">
              <Button
                onClick={saveLayout}
                disabled={isSaving || panels.length === 0}
                className="w-full"
              >
                {isSaving ? <Spinner className="mr-2" /> : null}
                Save Layout
              </Button>
              
              <Button
                onClick={calculateIrradiance}
                disabled={isCalculating || !layoutId}
                variant="outline"
                className="w-full"
              >
                {isCalculating ? <Spinner className="mr-2" /> : null}
                Calculate Irradiance
              </Button>
              
              <Button
                onClick={exportCAD}
                disabled={!layoutId}
                variant="outline"
                className="w-full"
              >
                Export CAD
              </Button>
            </div>
          </Card>

          {/* Irradiance Results */}
          {irradianceData && (
            <Card className="p-4">
              <h3 className="font-semibold mb-3">Irradiance Analysis</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>Total Irradiance:</span>
                  <span className="font-medium">{irradianceData.total_irradiance.toFixed(1)} kWh/m²/year</span>
                </div>
                <div className="flex justify-between">
                  <span>Panel Efficiency:</span>
                  <span className="font-medium">{irradianceData.panel_efficiency.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span>Energy Yield:</span>
                  <span className="font-medium">{irradianceData.energy_yield.toFixed(0)} kWh/year</span>
                </div>
                <div className="flex justify-between">
                  <span>Performance Ratio:</span>
                  <span className="font-medium">{irradianceData.performance_ratio.toFixed(2)}</span>
                </div>
              </div>
            </Card>
          )}

          {/* Panel Statistics */}
          <Card className="p-4">
            <h3 className="font-semibold mb-3">Panel Statistics</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span>Total Panels:</span>
                <span className="font-medium">{panels.length}</span>
              </div>
              <div className="flex justify-between">
                <span>Estimated Power:</span>
                <span className="font-medium">{panels.length * 400}W</span>
              </div>
              <div className="flex justify-between">
                <span>Selected Panel:</span>
                <span className="font-medium">{selectedPanelId || 'None'}</span>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default Design3D;