<script lang="ts">
	import { page } from '$app/state';
	import { auth } from '$lib/stores/auth';
	import { api, ApiError } from '$lib/api';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import type { TextSubmission, DetectedError, CorrectionAttemptResult } from '$lib/types';

	let submission = $state<TextSubmission | null>(null);
	let errors = $state<DetectedError[]>([]);
	let activeError = $state<DetectedError | null>(null);
	let attemptText = $state('');
	let lastResult = $state<CorrectionAttemptResult | null>(null);
	let analyzing = $state(false);
	let analyzeError = $state('');
	let correctionError = $state('');
	let loading = $state(true);

	const id = page.params.id;

	const groupLabels: Record<string, string> = {
		verb_phrase: 'Verb Phrase',
		noun_phrase: 'Noun Phrase',
		adjective: 'Adjective',
		spelling_word_choice: 'Spelling / Word Choice',
		syntax: 'Syntax',
	};

	const groupColors: Record<string, string> = {
		verb_phrase: 'bg-sky-200 border-sky-400 text-sky-950',
		noun_phrase: 'bg-yellow-200 border-yellow-400 text-yellow-950',
		adjective: 'bg-pink-200 border-pink-400 text-pink-950',
		spelling_word_choice: 'bg-red-200 border-red-400 text-red-950',
		syntax: 'bg-emerald-200 border-emerald-400 text-emerald-950',
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
		analyzeError = '';
		try {
			await api.post(`/nlp/submissions/${id}/analyze/`, {}, $auth.token);
			const errRes = await api.get<DetectedError[]>(
				`/feedback/submissions/${id}/errors/`,
				$auth.token,
			);
			errors = errRes;
			if (submission) submission.status = 'in_review';
		} catch (error) {
			if (error instanceof ApiError && typeof error.data === 'object' && error.data !== null && 'detail' in error.data) {
				analyzeError = String((error.data as { detail?: string }).detail ?? 'Analysis failed. Please try again.');
			} else {
				analyzeError = 'Analysis failed. Please try again.';
			}
			if (submission && submission.status === 'analyzing') {
				submission.status = 'submitted';
			}
		} finally {
			analyzing = false;
		}
	}

	async function submitAttempt(e: SubmitEvent) {
		e.preventDefault();
		if (!activeError) return;
		correctionError = '';
		try {
			lastResult = await api.post<CorrectionAttemptResult>(
				`/feedback/errors/${activeError.id}/attempt/`,
				{ attempted_text: attemptText },
				$auth.token,
			);

			updateErrorState(activeError.id, {
				attempt_count: lastResult.attempt_number,
				is_resolved: lastResult.is_resolved,
				can_request_solution: lastResult.can_request_solution,
				next_try_number: lastResult.display_attempt_number + 1,
			});
			attemptText = '';
		} catch (error) {
			correctionError = extractApiDetail(error, 'Could not submit the correction.');
		}
	}

	async function requestSolution() {
		if (!activeError) return;
		correctionError = '';
		try {
			lastResult = await api.post<CorrectionAttemptResult>(
				`/feedback/errors/${activeError.id}/solution/`,
				{ attempted_text: attemptText },
				$auth.token,
			);
			updateErrorState(activeError.id, {
				is_resolved: true,
				can_request_solution: false,
			});
			attemptText = '';
		} catch (error) {
			correctionError = extractApiDetail(error, 'Could not reveal the answer yet.');
		}
	}

	function selectError(err: DetectedError) {
		activeError = err;
		lastResult = null;
		attemptText = '';
		correctionError = '';
	}

	function updateErrorState(errorId: number, updates: Partial<DetectedError>) {
		errors = errors.map((err) => (err.id === errorId ? { ...err, ...updates } : err));
		if (activeError?.id === errorId) {
			activeError = { ...activeError, ...updates };
		}
	}

	function extractApiDetail(error: unknown, fallback: string) {
		if (error instanceof ApiError && typeof error.data === 'object' && error.data !== null && 'detail' in error.data) {
			return String((error.data as { detail?: string }).detail ?? fallback);
		}
		return fallback;
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

	let canAnalyze = $derived(
		submission
			? submission.status === 'submitted' || (submission.status === 'analyzing' && errors.length === 0)
			: false
	);

	let resolvedCount = $derived(errors.filter((e) => e.is_resolved).length);
	let displayGroups = $derived(Array.from(new Set(errors.map((error) => error.display_group))));

	function getPhaseTitle(error: DetectedError) {
		return error.attempt_count === 0 ? 'Phase 2' : 'Phase 3';
	}

	function getTryLabel(error: DetectedError) {
		return error.attempt_count === 0 ? 'Second try' : 'Third try';
	}

	function getActiveRevealAvailability(error: DetectedError) {
		if (lastResult && activeError?.id === error.id) {
			return lastResult.can_request_solution;
		}
		return error.can_request_solution;
	}
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

		{#if canAnalyze}
			<div class="bg-white p-6 rounded-2xl shadow mb-6 border border-stone-200">
				<div class="mb-4 rounded-2xl border border-stone-200 bg-stone-50 p-4">
					<p class="text-xs font-semibold uppercase tracking-[0.2em] text-stone-500">Phase 1</p>
					<h2 class="mt-2 text-xl font-semibold text-stone-900">Analyze and mark grammar targets</h2>
					<p class="mt-2 text-sm text-stone-600">
						Run the hybrid analysis first. The result will group highlights by grammatical role so the correction flow can move into the second and third try phases.
					</p>
				</div>
				<p class="text-gray-700 whitespace-pre-wrap">{submission.content}</p>
				<button
					onclick={analyzeText}
					disabled={analyzing}
					class="mt-4 px-4 py-2 bg-stone-900 text-white rounded-xl hover:bg-stone-700 disabled:opacity-50"
				>
					{analyzing ? 'Analyzing...' : submission.status === 'analyzing' ? 'Retry Analysis' : 'Analyze Text'}
				</button>
				{#if analyzeError}
					<p class="mt-3 text-sm text-red-600">{analyzeError}</p>
				{/if}
			</div>
		{:else}
			<!-- Main content area: highlighted text + correction panel -->
			<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
				<!-- Text with highlights -->
				<div class="lg:col-span-2 bg-white p-6 rounded-2xl shadow border border-stone-200">
					<div class="mb-4 rounded-2xl border border-stone-200 bg-stone-50 p-4">
						<p class="text-xs font-semibold uppercase tracking-[0.2em] text-stone-500">Phase 1</p>
						<h2 class="mt-2 text-xl font-semibold text-stone-900">Read the highlighted text</h2>
						<p class="mt-2 text-sm text-stone-600">
							Each highlight represents a grammatical target. Click one to open the second-try correction step.
						</p>
					</div>
					<h2 class="text-sm font-semibold text-gray-500 mb-3 uppercase tracking-wide">Your Text</h2>
					<div class="text-lg leading-[2.8rem] whitespace-pre-wrap">
						{#each segments as seg}
							{#if seg.error}
								<button
									onclick={() => selectError(seg.error!)}
									class="relative inline-flex align-baseline border-b-2 rounded-sm px-0.5 pt-5 pb-0.5 cursor-pointer transition
										{groupColors[seg.error.display_group] ?? 'bg-gray-200 border-gray-400 text-gray-900'}
										{seg.error.is_resolved ? 'opacity-40 line-through' : ''}
										{activeError?.id === seg.error.id ? 'ring-2 ring-stone-900' : ''}"
									title="{seg.error.display_label}"
								>
									{seg.text}
									<span class="absolute left-0 top-1 text-[11px] font-medium whitespace-nowrap pointer-events-none text-stone-700">
										{seg.error.display_label}
									</span>
								</button>
							{:else}
								{seg.text}
							{/if}
						{/each}
					</div>

					<!-- Legend -->
					<div class="mt-6 pt-4 border-t flex flex-wrap gap-3">
						{#each displayGroups as group}
							<span class="text-xs px-2 py-1 rounded border {groupColors[group] ?? 'bg-gray-200 border-gray-400 text-gray-900'}">
								{groupLabels[group] ?? group}
							</span>
						{/each}
					</div>
				</div>

				<!-- Correction panel -->
				<div class="bg-white p-6 rounded-2xl shadow border border-stone-200">
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
							<div class="rounded-2xl border border-stone-200 bg-stone-50 p-4">
								<p class="text-xs font-semibold uppercase tracking-[0.2em] text-stone-500">{getPhaseTitle(activeError)}</p>
								<h3 class="mt-2 text-xl font-semibold text-stone-900">{getTryLabel(activeError)}</h3>
								<p class="mt-2 text-sm text-stone-600">
									Work on the highlighted {activeError.display_label.toLowerCase()} issue. If the second try fails, the third-try step unlocks with a hint and the answer can be revealed.
								</p>
							</div>

							<div>
								<p class="text-sm text-gray-500">Original text:</p>
								<p class="font-mono text-stone-900 bg-stone-100 p-2 rounded-xl">"{activeError.original_text}"</p>
							</div>

							<div>
								<p class="text-sm text-gray-500 mb-1">Highlight group:</p>
								<span class="text-xs px-2 py-1 rounded border {groupColors[activeError.display_group] ?? 'bg-gray-200 border-gray-400 text-gray-900'}">
									{activeError.display_label}
								</span>
							</div>

							{#if correctionError}
								<div class="bg-red-50 p-3 rounded-xl border border-red-200 text-sm text-red-700">
									{correctionError}
								</div>
							{/if}

							{#if lastResult}
								{#if lastResult.is_correct}
									<div class="bg-green-50 p-4 rounded-2xl border border-green-200">
										<p class="text-green-700 font-semibold">Correct on the {lastResult.display_attempt_number === 2 ? 'second' : 'third'} try.</p>
										<p class="mt-1 text-sm text-green-700">The highlight is now resolved.</p>
									</div>
								{:else}
									<div class="bg-amber-50 p-4 rounded-2xl border border-amber-200">
										<p class="text-amber-700 font-semibold">
											{lastResult.outcome === 'solution_revealed' || lastResult.outcome === 'manual_reveal'
												? 'The answer is now revealed.'
												: 'The answer is not correct yet.'}
										</p>
										{#if lastResult.hint && !lastResult.solution}
											<p class="text-sm text-amber-700 mt-2">Hint: {lastResult.hint}</p>
											<p class="mt-2 text-sm text-amber-800">Phase 3 is now unlocked.</p>
										{/if}
										{#if lastResult.solution}
											<p class="text-sm text-green-700 mt-2">
												Answer: <span class="font-mono font-bold">{lastResult.solution}</span>
											</p>
										{/if}
										{#if lastResult.explanation}
											<p class="mt-2 text-sm text-stone-700">{lastResult.explanation}</p>
										{/if}
									</div>
								{/if}
							{/if}

							{#if !activeError.is_resolved}
								<form onsubmit={submitAttempt} class="space-y-2">
									<label for="attempt" class="block text-sm font-medium text-gray-700">
										Your correction ({getTryLabel(activeError).toLowerCase()}):
									</label>
									<input
										id="attempt"
										type="text"
										bind:value={attemptText}
										required
										class="w-full px-3 py-2 border border-stone-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-stone-900 font-mono"
										placeholder="Type the corrected text..."
									/>
									<div class="flex gap-2">
										<button
											type="submit"
											class="flex-1 py-2 bg-stone-900 text-white rounded-xl hover:bg-stone-700 text-sm"
										>
											Submit {getTryLabel(activeError).toLowerCase()}
										</button>
										{#if getActiveRevealAvailability(activeError)}
											<button
												type="button"
												onclick={requestSolution}
												class="py-2 px-3 bg-stone-200 text-stone-800 rounded-xl hover:bg-stone-300 text-sm"
											>
												Reveal answer
											</button>
										{/if}
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
