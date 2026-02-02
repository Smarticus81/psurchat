import React, { useState, useCallback } from 'react';
import { Upload, X, FileText, Calendar, Server } from 'lucide-react';
import { useDropzone } from 'react-dropzone';
import { api } from '../api';
import './SessionSetup.css';

interface SessionSetupProps {
    onSessionCreated: (sessionId: number) => void;
    onCancel?: () => void;
}

export const SessionSetup: React.FC<SessionSetupProps> = ({ onSessionCreated, onCancel }) => {
    const [deviceName, setDeviceName] = useState('Endosee Hysteroscope'); // Default for demo
    const [startDate, setStartDate] = useState('2024-01-01');
    const [endDate, setEndDate] = useState('2024-12-31');
    const [files, setFiles] = useState<File[]>([]);
    const [isSubmitting, setIsSubmitting] = useState(false);

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
                "Pending Extraction", // Auto-extract
                startDate,
                endDate
            );

            // 2. Upload Files
            for (const file of files) {
                // Initial naive type detection
                let type = 'other';
                const name = file.name.toLowerCase();
                if (name.includes('complaint')) type = 'complaints';
                else if (name.includes('sales')) type = 'sales';
                else if (name.includes('risk') || name.includes('rmf')) type = 'risk';
                else if (name.includes('cer') || name.includes('clinical')) type = 'cer';
                else if (name.includes('vigilance') || name.includes('maude')) type = 'vigilance';

                await api.uploadFile(session.session_id, file, type);
            }

            // 3. Start Generation
            await api.startGeneration(session.session_id);

            onSessionCreated(session.session_id);
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
