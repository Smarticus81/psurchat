import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

export interface Session {
    id: number;
    device_name: string;
    udi_di: string;
    period_start: string;
    period_end: string;
    status: string;
    created_at: string;
    workflow?: {
        current_section: string;
        sections_completed: number;
        total_sections: number;
        status: string;
    };
}

export interface ChatMessage {
    id: number;
    from_agent: string;
    to_agent: string;
    message: string;
    message_type: 'normal' | 'system' | 'error' | 'success';
    timestamp: string;
}

export interface Agent {
    id: string;
    name: string;
    role: string;
    ai_provider: string;
    model: string;
    status: 'idle' | 'working' | 'complete' | 'waiting';
    last_activity?: string;
}

export interface SectionDoc {
    section_id: string;
    section_name: string;
    author_agent: string;
    status: string;
    word_count: number;
    created_at: string;
    qc_feedback?: string;
}

export const api = {
    // Session Management
    async createSession(device_name: string, udi_di: string, start_date: string, end_date: string) {
        const response = await axios.post(`${API_BASE_URL}/sessions`, null, {
            params: { device_name, udi_di, start_date, end_date }
        });
        return response.data;
    },

    async getSession(sessionId: number): Promise<Session> {
        const response = await axios.get(`${API_BASE_URL}/sessions/${sessionId}`);
        return response.data;
    },

    async getSessions(): Promise<Session[]> {
        const response = await axios.get(`${API_BASE_URL}/sessions`);
        return response.data;
    },

    async deleteSession(sessionId: number) {
        const response = await axios.delete(`${API_BASE_URL}/sessions/${sessionId}`);
        return response.data;
    },

    // File Upload
    async uploadFile(sessionId: number, file: File, fileType: string) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await axios.post(
            `${API_BASE_URL}/sessions/${sessionId}/upload`,
            formData,
            {
                params: { file_type: fileType },
                headers: { 'Content-Type': 'multipart/form-data' }
            }
        );
        return response.data;
    },

    async getSessionFiles(sessionId: number) {
        const response = await axios.get(`${API_BASE_URL}/sessions/${sessionId}/files`);
        return response.data;
    },

    async setMasterContextIntake(sessionId: number, intake: {
        denominator_scope?: string;
        inference_policy?: string;
        closure_definition?: string;
        baseline_year?: number | null;
        external_vigilance_searched?: boolean;
        complaint_closures_complete?: boolean;
        rmf_hazard_list_available?: boolean;
        intended_use_provided?: boolean;
    }) {
        const response = await axios.patch(`${API_BASE_URL}/sessions/${sessionId}/intake`, intake);
        return response.data;
    },

    async validateSession(sessionId: number) {
        const response = await axios.get(`${API_BASE_URL}/sessions/${sessionId}/validate`);
        return response.data;
    },

    async startGeneration(sessionId: number) {
        const response = await axios.post(`${API_BASE_URL}/sessions/${sessionId}/start`);
        return response.data;
    },

    // Messages
    async getMessages(sessionId: number, limit: number = 100): Promise<ChatMessage[]> {
        const response = await axios.get(`${API_BASE_URL}/sessions/${sessionId}/messages`, {
            params: { limit }
        });
        return response.data;
    },

    async sendMessage(sessionId: number, message: string) {
        const response = await axios.post(`${API_BASE_URL}/sessions/${sessionId}/messages`, {
            message,
            from_agent: 'User',
            to_agent: 'all',
            message_type: 'normal'
        });
        return response.data;
    },

    // Agents
    async getAgents(sessionId: number): Promise<Agent[]> {
        const response = await axios.get(`${API_BASE_URL}/sessions/${sessionId}/agents`);
        return response.data;
    },

    // Sections
    async getSections(sessionId: number): Promise<SectionDoc[]> {
        const response = await axios.get(`${API_BASE_URL}/sessions/${sessionId}/sections`);
        return response.data;
    },

    async getSectionContent(sessionId: number, sectionId: string) {
        const response = await axios.get(
            `${API_BASE_URL}/sessions/${sessionId}/sections/${sectionId}`
        );
        return response.data;
    },

    // Workflow
    async getWorkflow(sessionId: number) {
        const response = await axios.get(`${API_BASE_URL}/sessions/${sessionId}/workflow`);
        return response.data;
    },

    // Interactive Workflow Control
    async pauseWorkflow(sessionId: number) {
        const response = await axios.post(`${API_BASE_URL}/sessions/${sessionId}/pause`);
        return response.data;
    },

    async resumeWorkflow(sessionId: number) {
        const response = await axios.post(`${API_BASE_URL}/sessions/${sessionId}/resume`);
        return response.data;
    },

    async askAgent(sessionId: number, agent: string, question: string) {
        const response = await axios.post(`${API_BASE_URL}/sessions/${sessionId}/ask`, {
            agent,
            question
        });
        return response.data;
    },

    async getWorkflowStatus(sessionId: number) {
        const response = await axios.get(`${API_BASE_URL}/sessions/${sessionId}/workflow-status`);
        return response.data;
    },

    async getAvailableAgents() {
        const response = await axios.get(`${API_BASE_URL}/agents`);
        return response.data;
    }
};
