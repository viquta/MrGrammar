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
	display_group: string;
	display_label: string;
	can_request_solution: boolean;
	next_try_number: number;
	created_at: string;
}

export interface CorrectionAttemptResult {
	attempt_number: number;
	display_attempt_number: number;
	phase: 'phase_2' | 'phase_3';
	outcome: 'retry' | 'hint' | 'correct' | 'solution_revealed' | 'manual_reveal' | 'locked';
	is_correct: boolean;
	is_resolved: boolean;
	can_request_solution: boolean;
	hint?: string;
	solution?: string;
	explanation?: string;
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
