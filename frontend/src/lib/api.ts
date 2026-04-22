const API_URL = import.meta.env.PUBLIC_API_URL ?? 'http://localhost:8000/api';

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

export { ApiError };
