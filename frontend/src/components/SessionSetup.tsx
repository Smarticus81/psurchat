import React, { useState, useCallback } from 'react';
import { Upload, X, FileText, Calendar, Server, ChevronDown, ChevronUp } from 'lucide-react';
import { useDropzone } from 'react-dropzone';
import { api } from '../api';
import './SessionSetup.css';

interface SessionSetupProps {
    onSessionCreated: (sessionId: number) => void;
    onCancel?: () => void;
}

export const SessionSetup: React.FC<SessionSetupProps> = ({ onSessionCreated, onCancel }) => {
    const [deviceName, setDeviceName] = useState('Endosee Hysteroscope');
    const [startDate, setStartDate] = useState('2024-01-01');
    const [endDate, setEndDate] = useState('2024-12-31');
    const [files, setFiles] = useState<File[]>([]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [showMasterContext, setShowMasterContext] = useState(false);
    const [denominatorScope, setDenominatorScope] = useState<'reporting_period_only' | 'cumulative_with_baseline'>('reporting_period_only');
    const [baselineYear, setBaselineYear] = useState<string>('');
    const [inferencePolicy, setInferencePolicy] = useState<'strictly_factual' | 'allow_reasonable_inference'>('strictly_factual');
    const [closureDefinition, setClosureDefinition] = useState('');
    const [externalVigilanceSearched, setExternalVigilanceSearched] = useState(false);
    const [complaintClosuresComplete, setComplaintClosuresComplete] = useState(false);
    const [rmfHazardListAvailable, setRmfHazardListAvailable] = useState(false);
    const [intendedUseProvided, setIntendedUseProvided] = useState(false);

    const onDrop = useCallback((acceptedFiles: File[]) => {
        setFiles(prev => [...prev, ...acceptedFiles]);
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'text/csv': ['.csv'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
            'application/vnd.ms-excel': ['.xls'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
        }
    });

    const removeFile = (index: number) => {
        setFiles(files.filter((_, i) => i !== index));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!deviceName || !startDate || !endDate || files.length === 0) {
            alert('Please fill all fields and upload at least one file.');
            return;
        }

        setIsSubmitting(true);
        try {
            // 1. Create Session
            const session = await api.createSession(
                deviceName,
                "Pending Extraction",
                startDate,
                endDate
            );

            // 2. Upload Files
            for (const file of files) {
                let type = 'other';
                const name = file.name.toLowerCase();
                if (name.includes('complaint')) type = 'complaints';
                else if (name.includes('sales')) type = 'sales';
                else if (name.includes('risk') || name.includes('rmf')) type = 'risk';
                else if (name.includes('cer') || name.includes('clinical')) type = 'cer';
                else if (name.includes('vigilance') || name.includes('maude')) type = 'vigilance';
                await api.uploadFile(session.session_id, file, type);
            }

            // 3. Set master context intake (optional; skip if backend does not support it)
            try {
                await api.setMasterContextIntake(session.session_id, {
                    denominator_scope: denominatorScope,
                    baseline_year: baselineYear ? parseInt(baselineYear, 10) : null,
                    inference_policy: inferencePolicy,
                    closure_definition: closureDefinition || undefined,
                    external_vigilance_searched: externalVigilanceSearched,
                    complaint_closures_complete: complaintClosuresComplete,
                    rmf_hazard_list_available: rmfHazardListAvailable,
                    intended_use_provided: intendedUseProvided,
                });
            } catch (_) {
                // 404 or other: intake endpoint may be missing on older backend; continue
            }

            // 4. Transition to dashboard/chat immediately so user sees the interface
            onSessionCreated(session.session_id);

            // 5. Start generation in background (extractor runs first, then orchestrator)
            api.startGeneration(session.session_id).catch((err) => {
                console.error('Start generation failed:', err);
            });
        } catch (error) {
            console.error('Setup failed:', error);
            alert('Failed to create session. Check console.');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="session-setup-card">
            <div className="setup-header">
                <h2><Server size={20} style={{ display: 'inline', marginBottom: -3, marginRight: 8 }} /> New PSUR Session</h2>
                <span style={{ fontSize: '0.8rem', color: '#666' }}>v2.5.0</span>
            </div>

            <form onSubmit={handleSubmit} className="setup-form">
                <div className="form-grid">
                    {/* Row 1: Device Name */}
                    <div className="form-group" style={{ gridColumn: 'span 2' }}>
                        <label>Device Name</label>
                        <input
                            type="text"
                            className="form-input"
                            value={deviceName}
                            onChange={(e) => setDeviceName(e.target.value)}
                            placeholder="e.g. Endosee Hysteroscope"
                        />
                    </div>

                    {/* Row 2: Dates */}
                    <div className="form-group">
                        <label>Start Date</label>
                        <div style={{ position: 'relative' }}>
                            <Calendar size={16} style={{ position: 'absolute', left: 10, top: 12, color: '#666' }} />
                            <input
                                type="date"
                                className="form-input"
                                style={{ paddingLeft: '2.5rem' }}
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label>End Date</label>
                        <div style={{ position: 'relative' }}>
                            <Calendar size={16} style={{ position: 'absolute', left: 10, top: 12, color: '#666' }} />
                            <input
                                type="date"
                                className="form-input"
                                style={{ paddingLeft: '2.5rem' }}
                                value={endDate}
                                onChange={(e) => setEndDate(e.target.value)}
                            />
                        </div>
                    </div>

                    {/* Row 3: Files */}
                    <div className="file-upload-section">
                        <label>Data Sources (CSV, Excel, DOCX)</label>
                        <div {...getRootProps()} className={`drop-zone ${isDragActive ? 'active' : ''}`}>
                            <input {...getInputProps()} />
                            <Upload className="upload-icon" size={32} />
                            <span className="upload-text">
                                {isDragActive ? 'Drop files here...' : 'Drag & drop files here, or click to select'}
                            </span>
                            <span className="upload-subtext">Supported: Complaints, Sales, Risk, CER, Vigilance data</span>
                        </div>

                        {files.length > 0 && (
                            <div className="file-list">
                                {files.map((file, idx) => (
                                    <div key={idx} className="file-item">
                                        <FileText size={14} color="#57C7E3" />
                                        <span className="file-name">{file.name}</span>
                                        <button type="button" onClick={() => removeFile(idx)} className="remove-file">
                                            <X size={14} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Master context intake - single golden source for all agents */}
                    <div className="master-context-section" style={{ gridColumn: 'span 2' }}>
                        <button
                            type="button"
                            className="master-context-toggle"
                            onClick={() => setShowMasterContext(!showMasterContext)}
                        >
                            {showMasterContext ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                            <span>Master context (exposure denominator, inference policy, data availability)</span>
                        </button>
                        {showMasterContext && (
                            <div className="master-context-fields">
                                <div className="form-group" style={{ gridColumn: 'span 2' }}>
                                    <label>Exposure denominator scope</label>
                                    <select
                                        className="form-input"
                                        value={denominatorScope}
                                        onChange={(e) => setDenominatorScope(e.target.value as 'reporting_period_only' | 'cumulative_with_baseline')}
                                    >
                                        <option value="reporting_period_only">Reporting period only (e.g. 2023-2025)</option>
                                        <option value="cumulative_with_baseline">Cumulative including baseline year</option>
                                    </select>
                                </div>
                                {denominatorScope === 'cumulative_with_baseline' && (
                                    <div className="form-group">
                                        <label>Baseline year (inclusive)</label>
                                        <input
                                            type="number"
                                            className="form-input"
                                            placeholder="e.g. 2022"
                                            value={baselineYear}
                                            onChange={(e) => setBaselineYear(e.target.value)}
                                            min={1990}
                                            max={2030}
                                        />
                                    </div>
                                )}
                                <div className="form-group">
                                    <label>Inference policy</label>
                                    <select
                                        className="form-input"
                                        value={inferencePolicy}
                                        onChange={(e) => setInferencePolicy(e.target.value as 'strictly_factual' | 'allow_reasonable_inference')}
                                    >
                                        <option value="strictly_factual">Strictly factual (do not infer missing data)</option>
                                        <option value="allow_reasonable_inference">Allow reasonable inference</option>
                                    </select>
                                </div>
                                <div className="form-group" style={{ gridColumn: 'span 2' }}>
                                    <label>Closure definition (optional)</label>
                                    <input
                                        type="text"
                                        className="form-input"
                                        placeholder="e.g. Closed = investigation completed with root cause documented"
                                        value={closureDefinition}
                                        onChange={(e) => setClosureDefinition(e.target.value)}
                                    />
                                </div>
                                <div className="form-group" style={{ gridColumn: 'span 2' }}>
                                    <span className="checkbox-label">Data availability (uncheck if not done / not available)</span>
                                    <label className="checkbox-row">
                                        <input
                                            type="checkbox"
                                            checked={externalVigilanceSearched}
                                            onChange={(e) => setExternalVigilanceSearched(e.target.checked)}
                                        />
                                        External vigilance database search performed
                                    </label>
                                    <label className="checkbox-row">
                                        <input
                                            type="checkbox"
                                            checked={complaintClosuresComplete}
                                            onChange={(e) => setComplaintClosuresComplete(e.target.checked)}
                                        />
                                        Complaint closures complete (single canonical snapshot)
                                    </label>
                                    <label className="checkbox-row">
                                        <input
                                            type="checkbox"
                                            checked={rmfHazardListAvailable}
                                            onChange={(e) => setRmfHazardListAvailable(e.target.checked)}
                                        />
                                        RMF hazard list available
                                    </label>
                                    <label className="checkbox-row">
                                        <input
                                            type="checkbox"
                                            checked={intendedUseProvided}
                                            onChange={(e) => setIntendedUseProvided(e.target.checked)}
                                        />
                                        Intended use statement provided
                                    </label>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Footer Actions */}
                    <div className="form-actions">
                        {onCancel && (
                            <button type="button" className="btn-secondary" onClick={onCancel} disabled={isSubmitting}>
                                Cancel
                            </button>
                        )}
                        <button type="submit" className="btn-primary" disabled={isSubmitting}>
                            {isSubmitting ? 'Initializing Swarm...' : 'Launch Agents'}
                        </button>
                    </div>
                </div>
            </form>
        </div>
    );
};
