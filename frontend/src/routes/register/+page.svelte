<script lang="ts">
	import { auth } from '$lib/stores/auth';
	import { goto } from '$app/navigation';

	let username = $state('');
	let email = $state('');
	let password = $state('');
	let firstName = $state('');
	let lastName = $state('');
	let role = $state<'student' | 'teacher'>('student');
	let error = $state('');
	let loading = $state(false);

	async function handleRegister() {
		error = '';
		loading = true;
		try {
			await auth.register({
				username,
				email,
				password,
				first_name: firstName,
				last_name: lastName,
				role,
			});
			await auth.login(username, password);
			goto('/');
		} catch (e: unknown) {
			error = 'Registration failed. Please check your inputs.';
		} finally {
			loading = false;
		}
	}
</script>

<div class="flex items-center justify-center min-h-screen">
	<div class="w-full max-w-md p-8 bg-white rounded-lg shadow-md">
		<h1 class="text-2xl font-bold text-center text-indigo-700 mb-6">MrGrammar</h1>
		<h2 class="text-lg font-semibold text-center mb-4">Create Account</h2>

		{#if error}
			<div class="bg-red-50 text-red-700 p-3 rounded mb-4 text-sm">{error}</div>
		{/if}

		<form onsubmit={handleRegister} class="space-y-4">
			<div class="grid grid-cols-2 gap-3">
				<div>
					<label for="firstName" class="block text-sm font-medium text-gray-700">First Name</label>
					<input
						id="firstName"
						type="text"
						bind:value={firstName}
						required
						class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
					/>
				</div>
				<div>
					<label for="lastName" class="block text-sm font-medium text-gray-700">Last Name</label>
					<input
						id="lastName"
						type="text"
						bind:value={lastName}
						required
						class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
					/>
				</div>
			</div>
			<div>
				<label for="username" class="block text-sm font-medium text-gray-700">Username</label>
				<input
					id="username"
					type="text"
					bind:value={username}
					required
					class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="email" class="block text-sm font-medium text-gray-700">Email</label>
				<input
					id="email"
					type="email"
					bind:value={email}
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
					minlength="8"
					class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="role" class="block text-sm font-medium text-gray-700">I am a...</label>
				<select
					id="role"
					bind:value={role}
					class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
				>
					<option value="student">Student</option>
					<option value="teacher">Teacher</option>
				</select>
			</div>
			<button
				type="submit"
				disabled={loading}
				class="w-full py-2 px-4 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
			>
				{loading ? 'Creating account...' : 'Register'}
			</button>
		</form>

		<p class="text-center text-sm text-gray-500 mt-4">
			Already have an account? <a href="/login" class="text-indigo-600 hover:underline">Sign in</a>
		</p>
	</div>
</div>
