export const API_URL = import.meta.env.PUBLIC_API_URL ?? 'http://localhost:8000/api';

import type { ClassroomAnalyticsResponse, StudentAnalyticsResponse } from '$lib/types';

interface RequestOptions {
	method?: string;
	body?: unknown;
	token?: string | null;
}

class ApiError extends Error {
	status: number;
	data: unknown;

	constructor(status: number, data: unknown) {
		super(`API error ${status}`);
		this.status = status;
		this.data = data;
	}
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
	const { method = 'GET', body, token } = options;

	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
	};

	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}

	const response = await fetch(`${API_URL}${endpoint}`, {
		method,
		headers,
		body: body ? JSON.stringify(body) : undefined,
	});

	if (!response.ok) {
		const data = await response.json().catch(() => null);
		throw new ApiError(response.status, data);
	}

	if (response.status === 204) {
		return undefined as T;
	}

	return response.json();
}

export const api = {
	get: <T>(endpoint: string, token?: string | null) =>
		request<T>(endpoint, { token }),

	post: <T>(endpoint: string, body: unknown, token?: string | null) =>
		request<T>(endpoint, { method: 'POST', body, token }),

	put: <T>(endpoint: string, body: unknown, token?: string | null) =>
		request<T>(endpoint, { method: 'PUT', body, token }),

	delete: <T>(endpoint: string, token?: string | null) =>
		request<T>(endpoint, { method: 'DELETE', token }),
};

export const analyticsApi = {
	getStudentProgress: (studentId: number, token?: string | null) =>
		api.get<StudentAnalyticsResponse>(`/analytics/student/${studentId}/progress/`, token),

	getClassroomPatterns: (classroomId: number, token?: string | null) =>
		api.get<ClassroomAnalyticsResponse>(`/analytics/classroom/${classroomId}/patterns/`, token),
};

interface AnalysisResponse {
	submission_id: number;
	task_id?: string;
	status: 'submitted' | 'analyzing' | 'in_review' | 'completed';
	errors_found?: number | null;
	message?: string;
	status_url?: string;
}

interface AnalysisStatusResponse {
	submission_id: number;
	status: 'submitted' | 'analyzing' | 'in_review' | 'completed';
	task_id: string | null;
	is_complete: boolean;
	errors_found: number | null;
	task_state?: string;
	error?: string;
}

export const submissionApi = {
	/**
	 * Trigger async analysis of a submission.
	 * Returns 200 if already complete, 202 if queued/in-progress.
	 */
	analyzeSubmission: (submissionId: number, token?: string | null) =>
		api.post<AnalysisResponse>(`/nlp/submissions/${submissionId}/analyze/`, {}, token),

	/**
	 * Poll analysis status. Call this repeatedly until is_complete is true.
	 */
	getAnalysisStatus: (submissionId: number, token?: string | null) =>
		api.get<AnalysisStatusResponse>(`/nlp/submissions/${submissionId}/status/`, token),

	/**
	 * Subscribe to analysis status with polling.
	 * Returns a promise that resolves when analysis is complete.
	 */
	subscribeToAnalysisStatus: async (
		submissionId: number,
		token?: string | null,
		pollInterval: number = 500,
		maxAttempts: number = 120,
	): Promise<AnalysisStatusResponse> => {
		let attempts = 0;

		while (attempts < maxAttempts) {
			try {
				const status = await submissionApi.getAnalysisStatus(submissionId, token);

				if (status.is_complete) {
					return status;
				}

				if (status.error) {
					throw new Error(status.error);
				}

				// Wait before next poll
				await new Promise((resolve) => setTimeout(resolve, pollInterval));
				attempts++;
			} catch (error) {
				if (error instanceof ApiError && error.status === 404) {
					throw error;
				}
				// For other errors, retry
				await new Promise((resolve) => setTimeout(resolve, pollInterval));
				attempts++;
			}
		}

		throw new Error(`Analysis polling timeout after ${maxAttempts} attempts`);
	},
};

export { ApiError };
