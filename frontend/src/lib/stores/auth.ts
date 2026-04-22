import { writable } from 'svelte/store';
import { api } from '$lib/api';
import type { User, TokenResponse } from '$lib/types';

interface AuthState {
	user: User | null;
	token: string | null;
	loading: boolean;
}

function createAuthStore() {
	const initial: AuthState = {
		user: null,
		token: typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null,
		loading: false,
	};

	const { subscribe, set, update } = writable<AuthState>(initial);

	return {
		subscribe,

		async login(username: string, password: string) {
			const data = await api.post<TokenResponse>('/auth/login/', { username, password });
			localStorage.setItem('token', data.access);
			localStorage.setItem('refresh_token', data.refresh);

			const user = await api.get<User>('/auth/me/', data.access);
			set({ user, token: data.access, loading: false });
		},

		async register(userData: {
			username: string;
			email: string;
			password: string;
			first_name: string;
			last_name: string;
			role: string;
		}) {
			await api.post('/auth/register/', userData);
		},

		async loadUser() {
			const token = localStorage.getItem('token');
			if (!token) return;

			try {
				update((s) => ({ ...s, loading: true }));
				const user = await api.get<User>('/auth/me/', token);
				set({ user, token, loading: false });
			} catch {
				localStorage.removeItem('token');
				localStorage.removeItem('refresh_token');
				set({ user: null, token: null, loading: false });
			}
		},

		logout() {
			localStorage.removeItem('token');
			localStorage.removeItem('refresh_token');
			set({ user: null, token: null, loading: false });
		},
	};
}

export const auth = createAuthStore();
