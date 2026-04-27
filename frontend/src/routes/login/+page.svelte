<script lang="ts">
	import { ApiError, API_URL } from '$lib/api';
	import { auth } from '$lib/stores/auth';
	import { goto } from '$app/navigation';

	let username = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);

	async function handleLogin(event?: SubmitEvent) {
		event?.preventDefault();
		error = '';
		loading = true;
		try {
			await auth.login(username, password);
			goto('/');
		} catch (e: unknown) {
			if (e instanceof ApiError && e.status === 401) {
				error = 'Invalid username/email or password.';
			} else if (e instanceof ApiError) {
				const detail =
					typeof e.data === 'object' && e.data !== null && 'detail' in e.data
						? String((e.data as { detail?: string }).detail ?? '')
						: '';
				error = detail
					? `Login failed (${e.status}): ${detail}`
					: `Login failed (${e.status}).`;
			} else if (e instanceof TypeError) {
				error = `Cannot reach API at ${API_URL}. Check backend is running and CORS/origin settings.`;
			} else {
				error = 'Login failed. Check backend/API availability and try again.';
			}
		} finally {
			loading = false;
		}
	}
</script>

<div class="flex items-center justify-center min-h-screen">
	<div class="w-full max-w-md p-8 bg-white rounded-lg shadow-md">
		<h1 class="text-2xl font-bold text-center text-indigo-700 mb-6">MrGrammar</h1>
		<h2 class="text-lg font-semibold text-center mb-4">Sign In</h2>

		{#if error}
			<div class="bg-red-50 text-red-700 p-3 rounded mb-4 text-sm">{error}</div>
		{/if}

		<form onsubmit={handleLogin} class="space-y-4">
			<div>
				<label for="username" class="block text-sm font-medium text-gray-700">Username or Email</label>
				<input
					id="username"
					type="text"
					bind:value={username}
					required
					class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="password" class="block text-sm font-medium text-gray-700">Password</label>
				<input
					id="password"
					type="password"
					bind:value={password}
					required
					class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
				/>
			</div>
			<button
				type="submit"
				disabled={loading}
				class="w-full py-2 px-4 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
			>
				{loading ? 'Signing in...' : 'Sign In'}
			</button>
		</form>

		<p class="text-center text-sm text-gray-500 mt-4">
			Don't have an account? <a href="/register" class="text-indigo-600 hover:underline">Register</a>
		</p>
	</div>
</div>
