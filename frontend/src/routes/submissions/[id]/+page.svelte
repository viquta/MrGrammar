<script lang="ts">
	import { page } from '$app/state';
	import { auth } from '$lib/stores/auth';
	import { api } from '$lib/api';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import type { TextSubmission, DetectedError, CorrectionAttemptResult } from '$lib/types';

	let submission = $state<TextSubmission | null>(null);
	let errors = $state<DetectedError[]>([]);
	let activeError = $state<DetectedError | null>(null);
	let attemptText = $state('');
	let lastResult = $state<CorrectionAttemptResult | null>(null);
	let analyzing = $state(false);
	let loading = $state(true);

	const id = page.params.id;

	const categoryLabels: Record<string, string> = {
		grammar: '📝 Grammar',
		spelling: '🔤 Spelling',
		article: '📌 Article',
		preposition: '🔗 Preposition',
		verb_tense: '⏱ Verb Tense',
		punctuation: '✏️ Punctuation',
		other: '❓ Other',
	};

	const categoryColors: Record<string, string> = {
		grammar: 'bg-red-200 border-red-400',
		spelling: 'bg-orange-200 border-orange-400',
		article: 'bg-purple-200 border-purple-400',
		preposition: 'bg-blue-200 border-blue-400',
		verb_tense: 'bg-yellow-200 border-yellow-400',
		punctuation: 'bg-pink-200 border-pink-400',
		other: 'bg-gray-200 border-gray-400',
	};

	onMount(async () => {
		await auth.loadUser();
		if (!$auth.user) { goto('/login'); return; }

		submission = await api.get<TextSubmission>(`/submissions/${id}/`, $auth.token);
		if (submission.status !== 'submitted') {
			const errRes = await api.get<DetectedError[]>(
				`/feedback/submissions/${id}/errors/`,
				$auth.token,
			);
			errors = errRes;
		}
		loading = false;
	});

	async function analyzeText() {
		analyzing = true;
		try {
			await api.post(`/nlp/submissions/${id}/analyze/`, {}, $auth.token);
			const errRes = await api.get<DetectedError[]>(
				`/feedback/submissions/${id}/errors/`,
				$auth.token,
			);
			errors = errRes;
			if (submission) submission.status = 'in_review';
		} finally {
			analyzing = false;
		}
	}

	async function submitAttempt(e: SubmitEvent) {
		e.preventDefault();
		if (!activeError) return;
		lastResult = await api.post<CorrectionAttemptResult>(
			`/feedback/errors/${activeError.id}/attempt/`,
			{ attempted_text: attemptText },
			$auth.token,
		);

		if (lastResult.is_correct) {
			activeError.is_resolved = true;
			errors = errors.map((e) => (e.id === activeError!.id ? { ...e, is_resolved: true } : e));
		}

		activeError.attempt_count = lastResult.attempt_number;
		attemptText = '';
	}

	async function requestSolution() {
		if (!activeError) return;
		lastResult = await api.post<CorrectionAttemptResult>(
			`/feedback/errors/${activeError.id}/solution/`,
			{},
			$auth.token,
		);
		activeError.is_resolved = true;
		errors = errors.map((e) => (e.id === activeError!.id ? { ...e, is_resolved: true } : e));
	}

	function selectError(err: DetectedError) {
		activeError = err;
		lastResult = null;
		attemptText = '';
	}

	function buildHighlightedText(text: string, errs: DetectedError[]): Array<{ text: string; error?: DetectedError }> {
		const segments: Array<{ text: string; error?: DetectedError }> = [];
		let pos = 0;
		const sorted = [...errs].sort((a, b) => a.start_offset - b.start_offset);
		for (const err of sorted) {
			if (err.start_offset > pos) {
				segments.push({ text: text.slice(pos, err.start_offset) });
			}
			segments.push({ text: text.slice(err.start_offset, err.end_offset), error: err });
			pos = err.end_offset;
		}
		if (pos < text.length) {
			segments.push({ text: text.slice(pos) });
		}
		return segments;
	}

	let segments = $derived(
		submission ? buildHighlightedText(submission.content, errors) : []
	);

	let resolvedCount = $derived(errors.filter((e) => e.is_resolved).length);
</script>

{#if loading}
	<div class="flex items-center justify-center min-h-screen">
		<p class="text-gray-500">Loading...</p>
	</div>
{:else if submission}
	<div class="max-w-6xl mx-auto p-6">
		<div class="flex items-center justify-between mb-4">
			<div>
				<h1 class="text-2xl font-bold">{submission.title}</h1>
				<p class="text-sm text-gray-500">
					{new Date(submission.submitted_at).toLocaleDateString()} · {submission.language.toUpperCase()}
				</p>
			</div>
			{#if errors.length > 0}
				<div class="text-sm text-gray-600">
					{resolvedCount}/{errors.length} errors resolved
				</div>
			{/if}
		</div>

		{#if submission.status === 'submitted'}
			<div class="bg-white p-6 rounded-lg shadow mb-6">
				<p class="text-gray-700 whitespace-pre-wrap">{submission.content}</p>
				<button
					onclick={analyzeText}
					disabled={analyzing}
					class="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
				>
					{analyzing ? 'Analyzing...' : 'Analyze Text'}
				</button>
			</div>
		{:else}
			<!-- Main content area: highlighted text + correction panel -->
			<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
				<!-- Text with highlights -->
				<div class="lg:col-span-2 bg-white p-6 rounded-lg shadow">
					<h2 class="text-sm font-semibold text-gray-500 mb-3 uppercase tracking-wide">Your Text</h2>
					<div class="text-lg leading-relaxed whitespace-pre-wrap">
						{#each segments as seg}
							{#if seg.error}
								<button
									onclick={() => selectError(seg.error!)}
									class="relative inline border-b-2 rounded-sm px-0.5 cursor-pointer transition
										{categoryColors[seg.error.error_category] ?? 'bg-gray-200 border-gray-400'}
										{seg.error.is_resolved ? 'opacity-40 line-through' : ''}
										{activeError?.id === seg.error.id ? 'ring-2 ring-indigo-500' : ''}"
									title="{categoryLabels[seg.error.error_category] ?? seg.error.error_category}"
								>
									{seg.text}
									<span class="absolute -top-5 left-0 text-xs font-medium whitespace-nowrap pointer-events-none">
										{categoryLabels[seg.error.error_category] ?? seg.error.error_category}
									</span>
								</button>
							{:else}
								{seg.text}
							{/if}
						{/each}
					</div>

					<!-- Legend -->
					<div class="mt-6 pt-4 border-t flex flex-wrap gap-3">
						{#each Object.entries(categoryLabels) as [key, label]}
							{#if errors.some((e) => e.error_category === key)}
								<span class="text-xs px-2 py-1 rounded {categoryColors[key] ?? 'bg-gray-200'}">
									{label}
								</span>
							{/if}
						{/each}
					</div>
				</div>

				<!-- Correction panel -->
				<div class="bg-white p-6 rounded-lg shadow">
					<h2 class="text-sm font-semibold text-gray-500 mb-3 uppercase tracking-wide">Correction</h2>

					{#if !activeError}
						<p class="text-gray-400 text-sm">Click on a highlighted error to start correcting.</p>
					{:else if activeError.is_resolved && !lastResult?.solution}
						<div class="space-y-3">
							<p class="text-green-700 font-semibold">✓ This error has been resolved.</p>
							<p class="text-sm text-gray-500">Click another error to continue.</p>
						</div>
					{:else}
						<div class="space-y-4">
							<div>
								<p class="text-sm text-gray-500">Original text:</p>
								<p class="font-mono text-red-600 bg-red-50 p-2 rounded">"{activeError.original_text}"</p>
							</div>

							<div>
								<p class="text-sm text-gray-500 mb-1">Category:</p>
								<span class="text-xs px-2 py-1 rounded {categoryColors[activeError.error_category] ?? 'bg-gray-200'}">
									{categoryLabels[activeError.error_category] ?? activeError.error_category}
								</span>
							</div>

							{#if lastResult}
								{#if lastResult.is_correct}
									<div class="bg-green-50 p-3 rounded border border-green-200">
										<p class="text-green-700 font-semibold">✓ Correct!</p>
									</div>
								{:else}
									<div class="bg-amber-50 p-3 rounded border border-amber-200">
										<p class="text-amber-700 font-semibold">✗ Not quite right.</p>
										{#if lastResult.hint && !lastResult.solution}
											<p class="text-sm text-amber-600 mt-1">💡 Hint: {lastResult.hint}</p>
										{/if}
										{#if lastResult.solution}
											<p class="text-sm text-green-700 mt-2">
												✅ Solution: <span class="font-mono font-bold">{lastResult.solution}</span>
											</p>
										{/if}
									</div>
								{/if}
							{/if}

							{#if !activeError.is_resolved}
								<form onsubmit={submitAttempt} class="space-y-2">
									<label for="attempt" class="block text-sm font-medium text-gray-700">
										Your correction (attempt {activeError.attempt_count + 1}):
									</label>
									<input
										id="attempt"
										type="text"
										bind:value={attemptText}
										required
										class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
										placeholder="Type the corrected text..."
									/>
									<div class="flex gap-2">
										<button
											type="submit"
											class="flex-1 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm"
										>
											Submit
										</button>
										<button
											type="button"
											onclick={requestSolution}
											class="py-2 px-3 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 text-sm"
										>
											Show Solution
										</button>
									</div>
								</form>
							{/if}
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</div>
{/if}
