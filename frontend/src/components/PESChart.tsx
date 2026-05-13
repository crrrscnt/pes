import { useMemo, useRef, useCallback } from 'react';
import Plot from 'react-plotly.js';
import type { Layout } from 'plotly.js';
import { useJobStatus } from '../hooks/useJobStatus';

interface PESChartProps {
  jobId: string | null;
  isPublic?: boolean;
}

export default function PESChart({ jobId, isPublic = false }: PESChartProps) {
  const { job, partialResults, loading, error } = useJobStatus(jobId, { isPublic });
  const plotRef = useRef<any>(null);

  // Объединяем финальные + промежуточные результаты
  const combinedResults = useMemo(() => {
    const results: Record<string, any> = {};

    if (!isPublic) {
      partialResults.forEach(pr => {
        results[pr.distance.toString()] = {
          vqe: pr.vqe,
          numpy: pr.numpy,
          distance: pr.distance,
        };
      });
    }

    if (job?.results) {
      Object.entries(job.results).forEach(([dist, result]) => {
        results[dist] = result;
      });
    }

    return results;
  }, [job?.results, partialResults, isPublic]);

  // Вычисляем конфигурацию графика синхронно через useMemo
  const plotConfig = useMemo(() => {
    const hasData = Object.keys(combinedResults).length > 0;
    const isCompleted = job?.status === 'completed';

    if (!hasData || !job?.molecule) {
      return null;
    }

    const distances: number[] = [];
    const vqeEnergies: number[] = [];
    const numpyEnergies: number[] = [];

    Object.entries(combinedResults).forEach(([distanceStr, result]) => {
      const distance = parseFloat(distanceStr);
      if ('error' in result) return;
      distances.push(distance);
      vqeEnergies.push(result.vqe);
      numpyEnergies.push(result.numpy);
    });

    if (distances.length === 0) {
      return {
        data: [],
        layout: {
          title: { text: 'Нет валидных точек данных' },
          xaxis: { title: 'Длина связи (Å)' },
          yaxis: { title: 'Полная энергия (Hartree)' },
        } as Partial<Layout>,
      };
    }

    const sortedIndices = distances.map((_, i) => i).sort((a, b) => distances[a] - distances[b]);
    const sortedDistances = sortedIndices.map(i => distances[i]);
    const sortedVQE = sortedIndices.map(i => vqeEnergies[i]);
    const sortedNumPy = sortedIndices.map(i => numpyEnergies[i]);

    const minIndex = sortedVQE.indexOf(Math.min(...sortedVQE));
    const minDistance = sortedDistances[minIndex];

    const minDist = Math.min(...sortedDistances);
    const maxDist = Math.max(...sortedDistances);
    const padding = (maxDist - minDist) * 0.1 || 0.1;

    const data: any[] = [
      {
        x: sortedDistances,
        y: sortedVQE,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'VQE',
        line: { color: '#3b82f6', width: 2, shape: 'spline' },
        marker: { size: 6, symbol: 'x' },
      },
      {
        x: sortedDistances,
        y: sortedNumPy,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'NumPy Minimum Eigensolver',
        line: { color: '#d19404', width: 2, dash: 'dot', shape: 'spline' },
        marker: { size: 4 },
      },
    ];

    if (isCompleted) {
      data.push({
        x: [minDistance, minDistance],
        y: [Math.min(...sortedVQE), Math.max(...sortedVQE)],
        type: 'scatter',
        mode: 'lines',
        name: 'Minimum',
        line: { color: '#6b7280', width: 2, dash: 'dash' },
        showlegend: false,
      });
    }

    // Типизируем layout как Partial<Layout> чтобы избежать ошибок TS
    const layout: Partial<Layout> = {
      title: {
        text: `${job.molecule} Кривая диссоциации (ПЭП-скан)${!isCompleted ? ' (В процессе)' : ''}`,
        font: { size: 16, color: 'var(--text-main)' },
      },
      xaxis: {
        title: { text: 'Длина связи (Å)', font: { size: 14 } },
        tickfont: { size: 12 },
        gridcolor: 'var(--gray-200)',
        range: [minDist - padding, maxDist + padding],
      },
      yaxis: {
        title: { text: 'Полная энергия (Hartree)', font: { size: 14 } },
        tickfont: { size: 12 },
        gridcolor: 'var(--gray-200)',
      },
      plot_bgcolor: 'var(--bg-card)',
      paper_bgcolor: 'var(--bg-body)',
      margin: { t: 60, r: 40, b: 60, l: 60 },
      hovermode: 'closest' as const,  // <-- as const для литерального типа
      showlegend: true,
      legend: {
        x: 0.02,
        y: 0.98,
        bgcolor: 'rgba(255,255,255,0.8)',
        bordercolor: 'var(--gray-200)',
        borderwidth: 1,
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
        bordercolor: 'var(--gray-500)',
        borderwidth: 1,
      }] : [],
    };

    return { data, layout };
  }, [combinedResults, job]);

  // Экспорт PNG через Plotly.downloadImage
  const handleExportPNG = useCallback(() => {
    const Plotly = (window as any).Plotly;
    if (!Plotly?.downloadImage) {
      console.error('Plotly.downloadImage not available');
      return;
    }
    const graphDiv = plotRef.current?.el;
    if (!graphDiv) return;

    Plotly.downloadImage(graphDiv, {
      format: 'png',
      width: 1200,
      height: 800,
      filename: `pes-scan-${job?.molecule}-${job?.id}`,
    });
  }, [job?.molecule, job?.id]);

  const handleExportData = useCallback(() => {
    if (!job?.results) return;
    const dataStr = JSON.stringify(job.results, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `pes-scan-${job.molecule}-${job.id}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }, [job]);

  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ height: '400px' }}>
        <div className="spinner" />
        <span className="ml-2" style={{ color: 'var(--gray-600)' }}>Загрузка графика...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p style={{ color: 'var(--status-failed-text)' }}>Ошибка загрузки графика</p>
        <p className="text-sm mt-2" style={{ color: 'var(--gray-500)' }}>{error}</p>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="text-center py-12">
        <p style={{ color: 'var(--gray-500)' }}>График недоступен</p>
      </div>
    );
  }

  if (!plotConfig) {
    return (
      <div className="text-center py-12">
        <p style={{ color: 'var(--gray-500)' }}>Ожидание данных...</p>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Export Buttons */}
      <div className="absolute top-0 right-0 flex gap-2 z-10">
        <button
          onClick={handleExportPNG}
          className="export-btn"
          disabled={!plotConfig}
          title="Экспорт графика в PNG"
        >
          Экспорт PNG
        </button>
        <button
          onClick={handleExportData}
          className="export-btn"
          disabled={!job?.results}
          title={!job?.results ? 'Нет данных' : 'Экспорт результатов в JSON'}
        >
          Экспорт данных
        </button>
      </div>

      {/* Chart */}
      <div className="chart-container">
        <Plot
          ref={plotRef}
          data={plotConfig.data}
          layout={plotConfig.layout}
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
