import { useEffect, useState, useMemo, useRef } from 'react';
import Plot from 'react-plotly.js';
import { useJobStatus } from '../hooks/useJobStatus';
import type { PESResults } from '../types';

interface PESChartProps {
  jobId: string | null;
  isPublic?: boolean; // Флаг для публичного режима
}

const MOLECULE_RANGES = {
  H2: [0.4, 1.2],
  LiH: [1.2, 2.0],
  BH: [1.0, 1.8],
  BeH: [1.0, 1.8],
  CH: [0.6, 1.4],
  NH: [0.6, 1.4],
  OH: [0.6, 1.4],
  FH: [0.6, 1.4],
} as const;

export default function PESChart({ jobId, isPublic = false }: PESChartProps) {
  const { job, partialResults, loading, error } = useJobStatus(jobId, { isPublic });
  const [plotData, setPlotData] = useState<any>(null);
  const plotRef = useRef<any>(null);

  // Сброс plotData при смене jobId
  useEffect(() => {
    setPlotData(null);
  }, [jobId]);

  // Объединить финальные + промежуточные результаты
  const combinedResults = useMemo(() => {
    const results: Record<string, any> = {};

    // Добавить промежуточные результаты (только для приватного режима)
    if (!isPublic) {
      partialResults.forEach(pr => {
        results[pr.distance.toString()] = {
          vqe: pr.vqe,
          numpy: pr.numpy,
          distance: pr.distance,
        };
      });
    }

    // Перезаписать финальными результатами (если есть)
    if (job?.results) {
      Object.entries(job.results).forEach(([dist, result]) => {
        results[dist] = result;
      });
    }

    return results;
  }, [job?.results, partialResults, isPublic]);

  useEffect(() => {
    const hasData = Object.keys(combinedResults).length > 0;
    const isCompleted = job?.status === 'completed';

    if (hasData && job?.molecule) {
      // Extract data points
      const distances: number[] = [];
      const vqeEnergies: number[] = [];
      const numpyEnergies: number[] = [];
      const errors: string[] = [];

      Object.entries(combinedResults).forEach(([distanceStr, result]) => {
        const distance = parseFloat(distanceStr);
        if ('error' in result) {
          errors.push(`Error at ${distance} Å: ${result.error}`);
        } else {
          distances.push(distance);
          vqeEnergies.push(result.vqe);
          numpyEnergies.push(result.numpy);
        }
      });

      if (distances.length === 0) {
        setPlotData({
          data: [],
          layout: {
            title: 'No valid data points',
            xaxis: { title: 'Bond Length (Å)' },
            yaxis: { title: 'Total Energy (Hartree)' },
          }
        });
        return;
      }

      // Sort by distance
      const sortedIndices = distances.map((_, i) => i).sort((a, b) => distances[a] - distances[b]);
      const sortedDistances = sortedIndices.map(i => distances[i]);
      const sortedVQE = sortedIndices.map(i => vqeEnergies[i]);
      const sortedNumPy = sortedIndices.map(i => numpyEnergies[i]);

      // Find minimum
      const minIndex = sortedVQE.indexOf(Math.min(...sortedVQE));
      const minDistance = sortedDistances[minIndex];

      const data = [
        {
          x: sortedDistances,
          y: sortedVQE,
          type: 'scatter',
          mode: 'lines+markers',
          name: 'VQE',
          line: { color: '#3b82f6', width: 2 },
          marker: { size: 6, symbol: 'x' },
        },
        {
          x: sortedDistances,
          y: sortedNumPy,
          type: 'scatter',
          mode: 'lines+markers',
          name: 'NumPy Minimum Eigensolver',
          line: { color: '#d19404', width: 2, dash: 'dot' },
          marker: { size: 4 },
        },
      ];

      // Добавить линию минимума только если расчет завершен
      if (isCompleted) {
        data.push({
          x: [minDistance, minDistance],
          y: [Math.min(...sortedVQE), Math.max(...sortedVQE)],
          type: 'scatter',
          mode: 'lines',
          name: 'Minimum',
          line: { color: '#6b7280', width: 2, dash: 'dash' },
          showlegend: false,
        } as any);
      }

      const moleculeRange = MOLECULE_RANGES[job.molecule as keyof typeof MOLECULE_RANGES];

      const layout = {
        title: {
          text: `${job.molecule} Dissociation Curve (PES Scan)${!isCompleted ? ' (In Progress)' : ''}`,
          font: { size: 16 }
        },
        xaxis: {
          title: 'Bond Length (Å)',
          titlefont: { size: 14 },
          tickfont: { size: 12 },
          gridcolor: '#e5e7eb',
          range: moleculeRange,
        },
        yaxis: {
          title: 'Total Energy (Hartree)',
          titlefont: { size: 14 },
          tickfont: { size: 12 },
          gridcolor: '#e5e7eb',
        },
        plot_bgcolor: '#ffffff',
        paper_bgcolor: '#ffffff',
        margin: { t: 60, r: 40, b: 60, l: 60 },
        hovermode: 'closest',
        showlegend: true,
        legend: {
          x: 0.02,
          y: 0.98,
          bgcolor: 'rgba(255,255,255,0.8)',
          bordercolor: '#e5e7eb',
          borderwidth: 1
        },
        annotations: isCompleted ? [{
          x: minDistance,
          y: Math.min(...sortedVQE),
          text: `Min: ${minDistance.toFixed(4)} Å`,
          showarrow: true,
          arrowhead: 2,
          ax: 0,
          ay: -40,
          bgcolor: 'rgba(255,255,255,0.9)',
          bordercolor: '#6b7280',
          borderwidth: 1,
        }] : []
      };

      setPlotData({ data, layout });
    }
  }, [combinedResults, job, isPublic]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="spinner"></div>
        <span className="ml-2 text-gray-600">Загрузка графика...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">Ошибка загрузки графика</p>
        <p className="text-sm text-gray-500 mt-2">{error}</p>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">График недоступен</p>
      </div>
    );
  }

  if (!plotData) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Ожидание данных...</p>
      </div>
    );
  }

  const handleExportPNG = () => {
    if (plotRef.current) {
      const plot = plotRef.current;
      if (plot && plot.el) {
        const gd = plot.el;
        window.Plotly.downloadImage(gd, {
          format: 'png',
          width: 1200,
          height: 800,
          filename: `pes-scan-${job.molecule}-${job.id}`,
        });
      }
    }
  };

  const handleExportData = () => {
    if (job.results) {
      const dataStr = JSON.stringify(job.results, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `pes-scan-${job.molecule}-${job.id}.json`;
      link.click();
      URL.revokeObjectURL(url);
    }
  };

  return (
    <div className="relative">
      {/* Export Buttons */}
      <div className="absolute top-0 right-0 flex gap-2 z-10">
        <button
          onClick={handleExportPNG}
          className="export-btn"
          disabled={!plotData}
          title="Export chart as PNG"
        >
          Экспорт PNG
        </button>
        <button
          onClick={handleExportData}
          className="export-btn"
          disabled={!job?.results}
          title={!job?.results ? 'No data available' : 'Export results as JSON'}
        >
          Экспорт данных
        </button>
      </div>

      {/* Chart */}
      <div className="chart-container">
        <Plot
          ref={plotRef}
          data={plotData.data}
          layout={plotData.layout}
          config={{
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
            responsive: true,
            toImageButtonOptions: {
              format: 'png',
              filename: job ? `pes-scan-${job.molecule}-${job.id}` : 'pes-scan',
              height: 800,
              width: 1200,
            }
          }}
          style={{ width: '100%', height: '100%' }}
        />
      </div>
    </div>
  );
}
