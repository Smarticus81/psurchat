import React, { useEffect, useState } from 'react';
import { api, ChartInfo } from '../api';
import { BarChart3, Loader2 } from 'lucide-react';
import './ChartPanel.css';

interface ChartPanelProps {
    sessionId: number;
}

export const ChartPanel: React.FC<ChartPanelProps> = ({ sessionId }) => {
    const [charts, setCharts] = useState<ChartInfo[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedChart, setSelectedChart] = useState<string | null>(null);
    const [filter, setFilter] = useState<string>('all');

    useEffect(() => {
        let active = true;
        const load = async () => {
            try {
                const data = await api.getCharts(sessionId);
                if (active) {
                    setCharts(data);
                    setLoading(false);
                }
            } catch {
                if (active) setLoading(false);
            }
        };
        load();
        const interval = setInterval(load, 10000);
        return () => { active = false; clearInterval(interval); };
    }, [sessionId]);

    const categories = ['all', ...new Set(charts.map(c => c.category))];
    const filtered = filter === 'all' ? charts : charts.filter(c => c.category === filter);

    if (loading) {
        return (
            <div className="chart-panel chart-panel--loading">
                <Loader2 size={20} className="spin" />
                <span>Loading charts...</span>
            </div>
        );
    }

    if (charts.length === 0) {
        return (
            <div className="chart-panel chart-panel--empty">
                <BarChart3 size={24} strokeWidth={1.5} />
                <span>Charts will appear after PSUR generation completes.</span>
            </div>
        );
    }

    return (
        <div className="chart-panel">
            <div className="chart-panel__header">
                <BarChart3 size={14} />
                <span>MDCG 2022-21 Charts</span>
                <span className="chart-panel__count">{charts.length} charts</span>
            </div>

            <div className="chart-panel__filters">
                {categories.map(cat => (
                    <button
                        key={cat}
                        className={`chart-filter ${filter === cat ? 'chart-filter--active' : ''}`}
                        onClick={() => setFilter(cat)}
                    >
                        {cat === 'all' ? 'All' : cat.replace('_', ' ')}
                    </button>
                ))}
            </div>

            <div className="chart-grid">
                {filtered.map(chart => (
                    <div
                        key={chart.chart_id}
                        className={`chart-card ${selectedChart === chart.chart_id ? 'chart-card--selected' : ''}`}
                        onClick={() => setSelectedChart(
                            selectedChart === chart.chart_id ? null : chart.chart_id
                        )}
                    >
                        <img
                            src={api.getChartPngUrl(sessionId, chart.chart_id)}
                            alt={chart.title}
                            className="chart-card__image"
                            loading="lazy"
                        />
                        <div className="chart-card__info">
                            <span className="chart-card__title">{chart.title}</span>
                            <span className="chart-card__meta">
                                Section {chart.section_id} | {chart.category}
                            </span>
                        </div>
                    </div>
                ))}
            </div>

            {selectedChart && (
                <div className="chart-detail-overlay" onClick={() => setSelectedChart(null)}>
                    <div className="chart-detail" onClick={e => e.stopPropagation()}>
                        <img
                            src={api.getChartPngUrl(sessionId, selectedChart)}
                            alt={charts.find(c => c.chart_id === selectedChart)?.title || ''}
                            className="chart-detail__image"
                        />
                        <div className="chart-detail__title">
                            {charts.find(c => c.chart_id === selectedChart)?.title}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
