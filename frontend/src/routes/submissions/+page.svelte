<script lang="ts">
	import { auth } from '$lib/stores/auth';
	import { api } from '$lib/api';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import type { TextSubmission, Classroom, PaginatedResponse } from '$lib/types';

	let submissions = $state<TextSubmission[]>([]);
	let classrooms = $state<Classroom[]>([]);
	let loading = $state(true);

	// New submission form
	let showForm = $state(false);
	let title = $state('');
	let content = $state('');
	let classroomId = $state<number | null>(null);
	let submitting = $state(false);

	onMount(async () => {
		await auth.loadUser();
		if (!$auth.user) { goto('/login'); return; }

		const [subRes, classRes] = await Promise.all([
			api.get<PaginatedResponse<TextSubmission>>('/submissions/', $auth.token),
			api.get<PaginatedResponse<Classroom>>('/classrooms/', $auth.token),
		]);
		submissions = subRes.results;
		classrooms = classRes.results;
		if (classrooms.length > 0) classroomId = classrooms[0].id;
		loading = false;
	});

	async function handleSubmit() {
		if (!classroomId) return;
		submitting = true;
		try {
			const sub = await api.post<TextSubmission>('/submissions/', {
				title,
				content,
				classroom: classroomId,
			}, $auth.token);
			submissions = [sub, ...submissions];
			showForm = false;
			title = '';
			content = '';
		} finally {
			submitting = false;
		}
	}

	const statusColors: Record<string, string> = {
		submitted: 'bg-gray-200 text-gray-700',
		analyzing: 'bg-yellow-200 text-yellow-800',
		in_review: 'bg-blue-200 text-blue-800',
		completed: 'bg-green-200 text-green-800',
	};
</script>

<div class="max-w-4xl mx-auto p-6">
	<div class="flex items-center justify-between mb-6">
		<h1 class="text-2xl font-bold">My Submissions</h1>
		{#if $auth.user?.role === 'student'}
			<button
				onclick={() => (showForm = !showForm)}
				class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
			>
				{showForm ? 'Cancel' : '+ New Submission'}
			</button>
		{/if}
	</div>

	{#if showForm}
		<form onsubmit={handleSubmit} class="bg-white p-6 rounded-lg shadow mb-6 space-y-4">
			<div>
				<label for="title" class="block text-sm font-medium text-gray-700">Title</label>
				<input
					id="title"
					type="text"
					bind:value={title}
					required
					class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
				/>
			</div>
			<div>
				<label for="classroom" class="block text-sm font-medium text-gray-700">Classroom</label>
				<select
					id="classroom"
					bind:value={classroomId}
					class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
				>
					{#each classrooms as c}
						<option value={c.id}>{c.name}</option>
					{/each}
				</select>
			</div>
			<div>
				<label for="content" class="block text-sm font-medium text-gray-700">Your Text (German)</label>
				<textarea
					id="content"
					bind:value={content}
					required
					rows={8}
					class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
					placeholder="Write your German text here..."
				></textarea>
				<p class="text-xs text-gray-500 mt-1">{content.split(/\s+/).filter(Boolean).length} words</p>
			</div>
			<button
				type="submit"
				disabled={submitting}
				class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
			>
				{submitting ? 'Submitting...' : 'Submit for Analysis'}
			</button>
		</form>
	{/if}

	{#if loading}
		<p class="text-gray-500">Loading...</p>
	{:else if submissions.length === 0}
		<p class="text-gray-500">No submissions yet. Create your first one!</p>
	{:else}
		<div class="space-y-3">
			{#each submissions as sub}
				<a
					href="/submissions/{sub.id}"
					class="block bg-white p-4 rounded-lg shadow hover:shadow-md transition"
				>
					<div class="flex items-center justify-between">
						<h3 class="font-semibold text-lg">{sub.title}</h3>
						<span class="text-xs px-2 py-1 rounded-full {statusColors[sub.status] ?? 'bg-gray-200'}">
							{sub.status.replace('_', ' ')}
						</span>
					</div>
					<p class="text-sm text-gray-500 mt-1">
						{new Date(sub.submitted_at).toLocaleDateString()} · {sub.language.toUpperCase()}
					</p>
				</a>
			{/each}
		</div>
	{/if}
</div>
