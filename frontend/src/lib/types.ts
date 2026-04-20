export interface User {
	id: number;
	username: string;
	email: string;
	first_name: string;
	last_name: string;
	role: 'student' | 'teacher' | 'admin';
}

export interface Classroom {
	id: number;
	name: string;
	language: string;
	created_by: string;
	created_at: string;
	student_count: number;
}

export interface TextSubmission {
	id: number;
	student: number;
	student_name: string;
	classroom: number;
	title: string;
	content: string;
	language: string;
	status: 'submitted' | 'analyzing' | 'in_review' | 'completed';
	submitted_at: string;
	updated_at: string;
}

export interface DetectedError {
	id: number;
	submission: number;
	error_category: string;
	severity: string;
	start_offset: number;
	end_offset: number;
	original_text: string;
	is_resolved: boolean;
	attempt_count: number;
	created_at: string;
}

export interface CorrectionAttemptResult {
	attempt_number: number;
	is_correct: boolean;
	is_resolved: boolean;
	hint?: string;
	solution?: string;
}

export interface TokenResponse {
	access: string;
	refresh: string;
}

export interface PaginatedResponse<T> {
	count: number;
	next: string | null;
	previous: string | null;
	results: T[];
}
