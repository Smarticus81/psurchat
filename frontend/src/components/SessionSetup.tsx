import React, { useState, useCallback } from 'react';
import { Upload, X, FileText, Calendar, Server, ChevronDown, ChevronUp, AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react';
import { useDropzone } from 'react-dropzone';
import { api } from '../api';
import './SessionSetup.css';

interface ValidationIssue {
    severity: 'error' | 'warning';
    message: string;
}

interface ValidationResult {
    valid: boolean;
    issues: ValidationIssue[];
    extracted_data: {
        exposure_denominator_value: number;
        total_complaints_canonical: number;
        complaints_closed_canonical: number;
        annual_units_canonical: Record<string, number>;
        has_sales: boolean;
        has_complaints: boolean;
        has_vigilance: boolean;
        column_mapping: Record<string, unknown>;
    };
}

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
    const [fileTypes, setFileTypes] = useState<Record<string, string>>({});
    
    // Validation state
    const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
    const [pendingSessionId, setPendingSessionId] = useState<number | null>(null);
    const [isValidating, setIsValidating] = useState(false);

    // Infer file type from filename as initial suggestion
    const inferFileType = (filename: string): string => {
        const name = filename.toLowerCase();
        if (name.includes('complaint')) return 'complaints';
        if (name.includes('sales') || name.includes('distribution')) return 'sales';
        if (name.includes('risk') || name.includes('rmf')) return 'risk';
        if (name.includes('cer') || name.includes('clinical')) return 'cer';
        if (name.includes('vigilance') || name.includes('maude') || name.includes('incident')) return 'vigilance';
        return 'sales'; // Default to sales instead of 'other'
    };

    const onDrop = useCallback((acceptedFiles: File[]) => {
        setFiles(prev => [...prev, ...acceptedFiles]);
        // Set initial file types based on filename inference
        setFileTypes(prev => {
            const newTypes = { ...prev };
            for (const file of acceptedFiles) {
                if (!newTypes[file.name]) {
                    newTypes[file.name] = inferFileType(file.name);
                }
            }
            return newTypes;
        });
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
        const fileToRemove = files[index];
        setFiles(files.filter((_, i) => i !== index));
        if (fileToRemove) {
            setFileTypes(prev => {
                const newTypes = { ...prev };
                delete newTypes[fileToRemove.name];
                return newTypes;
            });
        }
    };

    const updateFileType = (filename: string, type: string) => {
        setFileTypes(prev => ({ ...prev, [filename]: type }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!deviceName || !startDate || !endDate || files.length === 0) {
            alert('Please fill all fields and upload at least one file.');
            return;
        }

        setIsSubmitting(true);
        setValidationResult(null);
        
        try {
            // 1. Create Session
            const session = await api.createSession(
                deviceName,
                "Pending Extraction",
                startDate,
                endDate
            );

            // 2. Upload Files with user-selected types
            for (const file of files) {
                const type = fileTypes[file.name] || 'sales';
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

            // 4. Run validation before proceeding
            setIsValidating(true);
            const validation = await api.validateSession(session.session_id);
            setValidationResult(validation);
            setPendingSessionId(session.session_id);
            setIsValidating(false);
            
            // If there are errors, stop and show results
            if (!validation.valid) {
                setIsSubmitting(false);
                return;
            }
            
            // 5. No errors - proceed to generation
            onSessionCreated(session.session_id);
            api.startGeneration(session.session_id).catch((err) => {
                console.error('Start generation failed:', err);
            });
        } catch (error) {
            console.error('Setup failed:', error);
            alert('Failed to create session. Check console.');
        } finally {
            setIsSubmitting(false);
            setIsValidating(false);
        }
    };
    
    const proceedWithWarnings = () => {
        if (pendingSessionId) {
            onSessionCreated(pendingSessionId);
            api.startGeneration(pendingSessionId).catch((err) => {
                console.error('Start generation failed:', err);
            });
        }
    };
    
    const cancelAndRestart = () => {
        // Reset validation state but keep the form data
        setValidationResult(null);
        setPendingSessionId(null);
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
                                    <div key={idx} className="file-item file-item-with-type">
                                        <FileText size={14} color="#57C7E3" />
                                        <span className="file-name">{file.name}</span>
                                        <select
                                            className="file-type-select"
                                            value={fileTypes[file.name] || 'sales'}
                                            onChange={(e) => updateFileType(file.name, e.target.value)}
                                        >
                                            <option value="sales">Sales/Distribution</option>
                                            <option value="complaints">Complaints</option>
                                            <option value="vigilance">Vigilance/MAUDE</option>
                                            <option value="risk">Risk Management</option>
                                            <option value="cer">Clinical Evaluation</option>
                                            <option value="pmcf">PMCF Data</option>
                                        </select>
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

                    {/* Validation Results */}
                    {validationResult && (
                        <div className="validation-results" style={{ gridColumn: 'span 2' }}>
                            <div className={`validation-header ${validationResult.valid ? 'valid' : 'invalid'}`}>
                                {validationResult.valid ? (
                                    <><CheckCircle size={18} /> Data Validation Passed</>
                                ) : (
                                    <><AlertCircle size={18} /> Data Issues Detected</>
                                )}
                            </div>
                            
                            {validationResult.issues.length > 0 && (
                                <div className="validation-issues">
                                    {validationResult.issues.map((issue, idx) => (
                                        <div key={idx} className={`validation-issue ${issue.severity}`}>
                                            {issue.severity === 'error' ? (
                                                <AlertCircle size={14} />
                                            ) : (
                                                <AlertTriangle size={14} />
                                            )}
                                            <span>{issue.message}</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                            
                            <div className="validation-summary">
                                <div className="summary-row">
                                    <span>Units Distributed:</span>
                                    <span className={validationResult.extracted_data.exposure_denominator_value === 0 ? 'value-error' : 'value-ok'}>
                                        {validationResult.extracted_data.exposure_denominator_value.toLocaleString()}
                                    </span>
                                </div>
                                <div className="summary-row">
                                    <span>Total Complaints:</span>
                                    <span>{validationResult.extracted_data.total_complaints_canonical}</span>
                                </div>
                                <div className="summary-row">
                                    <span>Closed Complaints:</span>
                                    <span>{validationResult.extracted_data.complaints_closed_canonical}</span>
                                </div>
                            </div>
                            
                            {!validationResult.valid && (
                                <div className="validation-actions">
                                    <button type="button" className="btn-secondary" onClick={cancelAndRestart}>
                                        Go Back
                                    </button>
                                    <button type="button" className="btn-warning" onClick={proceedWithWarnings}>
                                        Proceed Anyway
                                    </button>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Footer Actions */}
                    <div className="form-actions">
                        {onCancel && (
                            <button type="button" className="btn-secondary" onClick={onCancel} disabled={isSubmitting || isValidating}>
                                Cancel
                            </button>
                        )}
                        <button type="submit" className="btn-primary" disabled={isSubmitting || isValidating || Boolean(validationResult && !validationResult.valid)}>
                            {isValidating ? 'Validating Data...' : isSubmitting ? 'Initializing Swarm...' : 'Launch Agents'}
                        </button>
                    </div>
                </div>
            </form>
        </div>
    );
};
