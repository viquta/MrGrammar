<script lang="ts">
	import { auth } from '$lib/stores/auth';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(async () => {
		await auth.loadUser();
		if (!$auth.user) {
			goto('/login');
		}
	});
</script>

{#if $auth.user}
	<div class="max-w-4xl mx-auto p-6">
		<h1 class="text-3xl font-bold mb-6">
			Welcome, {$auth.user.first_name || $auth.user.username}!
		</h1>

		{#if $auth.user.role === 'student'}
			<div class="grid gap-4 md:grid-cols-2">
				<a
					href="/submissions"
					class="block p-6 bg-white rounded-lg shadow hover:shadow-md transition"
				>
					<h2 class="text-xl font-semibold text-indigo-700">My Submissions</h2>
					<p class="text-gray-600 mt-2">View and create text submissions</p>
				</a>
				<a
					href="/progress"
					class="block p-6 bg-white rounded-lg shadow hover:shadow-md transition"
				>
					<h2 class="text-xl font-semibold text-indigo-700">My Progress</h2>
					<p class="text-gray-600 mt-2">Track your improvement over time</p>
				</a>
			</div>
		{:else if $auth.user.role === 'teacher'}
			<div class="grid gap-4 md:grid-cols-2">
				<a
					href="/classrooms"
					class="block p-6 bg-white rounded-lg shadow hover:shadow-md transition"
				>
					<h2 class="text-xl font-semibold text-indigo-700">My Classes</h2>
					<p class="text-gray-600 mt-2">View classes and student work</p>
				</a>
				<a
					href="/analytics"
					class="block p-6 bg-white rounded-lg shadow hover:shadow-md transition"
				>
					<h2 class="text-xl font-semibold text-indigo-700">Analytics</h2>
					<p class="text-gray-600 mt-2">View class and student patterns</p>
				</a>
			</div>
		{/if}
	</div>
{:else}
	<div class="flex items-center justify-center min-h-screen">
		<p class="text-gray-500">Loading...</p>
	</div>
{/if}
