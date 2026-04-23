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

export interface AnalyticsStudentIdentity {
	id: number;
	username: string;
	full_name: string;
}

export interface AnalyticsOverview {
	submission_count: number;
	total_errors: number;
	resolved_errors: number;
	resolution_rate: number;
	first_attempt_successes: number;
	first_attempt_success_rate: number;
	hint_shown_errors: number;
	hint_usage_rate: number;
	manual_reveal_count: number;
	solution_reveal_count: number;
	avg_attempts_per_error: number;
	last_submission_at?: string | null;
}

export interface AnalyticsCategorySubmissionPoint {
	submission_id: number;
	submission_title: string;
	submitted_at: string;
	total_errors: number;
	resolved_errors: number;
	first_attempt_successes: number;
	avg_hints_used?: number;
	hint_shown_errors: number;
	manual_reveal_count: number;
	student_id?: number;
	student_name?: string;
}

export interface AnalyticsSubmissionCategory {
	error_category: string;
	total_errors: number;
	resolved_errors: number;
	first_attempt_successes: number;
	avg_hints_used: number;
	hint_shown_errors: number;
	manual_reveal_count: number;
	attempt_count: number;
}

export interface AnalyticsStudentSubmission {
	submission_id: number;
	title: string;
	status: TextSubmission['status'];
	submitted_at: string;
	total_errors: number;
	resolved_errors: number;
	first_attempt_successes: number;
	hint_shown_errors: number;
	manual_reveal_count: number;
	solution_reveal_count: number;
	attempt_count: number;
	categories: AnalyticsSubmissionCategory[];
}

export interface AnalyticsCategoryBreakdown {
	error_category: string;
	total_errors: number;
	resolved_errors: number;
	resolution_rate?: number;
	first_attempt_successes: number;
	first_attempt_success_rate: number;
	avg_hints_used: number;
	hint_shown_errors: number;
	hint_usage_rate?: number;
	manual_reveal_count: number;
	avg_attempts_per_error: number;
	timeline: AnalyticsCategorySubmissionPoint[];
}

export interface StudentAnalyticsResponse {
	student: AnalyticsStudentIdentity;
	overview: AnalyticsOverview;
	submissions: AnalyticsStudentSubmission[];
	category_breakdown: AnalyticsCategoryBreakdown[];
}

export interface AnalyticsClassroomIdentity {
	id: number;
	name: string | null;
	language: string | null;
}

export interface ClassroomAnalyticsTimelineEntry {
	submission_id: number;
	submission_title: string;
	submitted_at: string;
	student_id: number;
	student_name: string;
	total_errors: number;
	resolved_errors: number;
	first_attempt_successes: number;
	hint_shown_errors: number;
	manual_reveal_count: number;
}

export interface ClassroomStudentAnalyticsRow {
	student_id: number;
	username: string;
	full_name: string;
	submission_count: number;
	total_errors: number;
	resolved_errors: number;
	resolution_rate: number;
	first_attempt_successes: number;
	first_attempt_success_rate: number;
	hint_shown_errors: number;
	hint_usage_rate: number;
	manual_reveal_count: number;
	avg_attempts_per_error: number;
	top_error_category: string | null;
	last_submission_at: string | null;
}

export interface ClassroomAnalyticsResponse {
	classroom: AnalyticsClassroomIdentity;
	overview: Omit<AnalyticsOverview, 'last_submission_at'> & {
		student_count: number;
	};
	timeline: ClassroomAnalyticsTimelineEntry[];
	category_breakdown: AnalyticsCategoryBreakdown[];
	students: ClassroomStudentAnalyticsRow[];
}
