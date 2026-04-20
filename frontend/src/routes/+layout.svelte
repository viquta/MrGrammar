<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { auth } from '$lib/stores/auth';
	import { goto } from '$app/navigation';

	let { children } = $props();

	function logout() {
		auth.logout();
		goto('/login');
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{#if $auth.user}
	<nav class="bg-indigo-700 text-white px-6 py-3 flex items-center justify-between">
		<a href="/" class="text-xl font-bold">MrGrammar</a>
		<div class="flex items-center gap-4">
			<span class="text-sm">{$auth.user.first_name || $auth.user.username} ({$auth.user.role})</span>
			<button onclick={logout} class="text-sm underline hover:no-underline">Logout</button>
		</div>
	</nav>
{/if}

<main class="min-h-screen bg-gray-50">
	{@render children()}
</main>
