<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	import { analyticsApi, ApiError } from '$lib/api';
	import { auth } from '$lib/stores/auth';
	import type {
		AnalyticsCategoryBreakdown,
		AnalyticsCategorySubmissionPoint,
		StudentAnalyticsResponse,
	} from '$lib/types';

	let analytics = $state<StudentAnalyticsResponse | null>(null);
	let loading = $state(true);
	let errorMessage = $state('');
	let Sparkline = $state<any>(null);

	onMount(async () => {
		const sparklineImport = import('$lib/components/Sparkline.svelte').then((module) => {
			Sparkline = module.default;
		});

		await auth.loadUser();
		if (!$auth.user) {
			goto('/login');
			return;
		}

		if ($auth.user.role !== 'student') {
			goto('/');
			return;
		}

		try {
			analytics = await analyticsApi.getStudentProgress($auth.user.id, $auth.token);
		} catch (error) {
			errorMessage = extractApiDetail(error, 'Could not load your progress right now.');
		} finally {
			loading = false;
		}

		await sparklineImport;
	});

	function extractApiDetail(error: unknown, fallback: string) {
		if (error instanceof ApiError && typeof error.data === 'object' && error.data !== null && 'detail' in error.data) {
			return String((error.data as { detail?: string }).detail ?? fallback);
		}
		return fallback;
	}

	function formatDate(value: string | null | undefined) {
		if (!value) {
			return 'No submissions yet';
		}
		return new Date(value).toLocaleDateString(undefined, {
			day: 'numeric',
			month: 'short',
			year: 'numeric',
		});
	}

	function formatPercent(value: number) {
		return `${Math.round(value * 100)}%`;
	}

	function barWidth(value: number, max: number) {
		if (max <= 0) {
			return '0%';
		}
		return `${Math.max(8, Math.round((value / max) * 100))}%`;
	}

	function categoryTrendLabel(category: AnalyticsCategoryBreakdown) {
		const points = category.timeline;
		if (points.length < 2) {
			return 'Need at least two submissions to show change';
		}

		const first = points[0].total_errors;
		const last = points[points.length - 1].total_errors;
		if (last < first) {
			return `Improving: down from ${first} to ${last}`;
		}
		if (last > first) {
			return `Increasing: up from ${first} to ${last}`;
		}
		return `Stable: ${last} in the first and latest submission`;
	}

	function sparkline(points: AnalyticsCategorySubmissionPoint[]) {
		if (points.length === 0) {
			return '';
		}

		const values = points.map((point) => point.total_errors);
		const max = Math.max(...values, 1);
		const step = points.length === 1 ? 80 : 80 / (points.length - 1);

		return values
			.map((value, index) => {
				const x = index * step;
				const y = 34 - (value / max) * 28;
				return `${x},${y}`;
			})
			.join(' ');
	}

	let maxCategoryErrors = $derived(
		analytics ? Math.max(...analytics.category_breakdown.map((category) => category.total_errors), 1) : 1,
	);

	let maxSubmissionErrors = $derived(
		analytics ? Math.max(...analytics.submissions.map((submission) => submission.total_errors), 1) : 1,
	);

	let headlineCards = $derived(
		analytics
			? [
				{
					label: 'Submissions',
					value: analytics.overview.submission_count,
					detail: `Last submission ${formatDate(analytics.overview.last_submission_at)}`,
				},
				{
					label: 'Resolved Errors',
					value: analytics.overview.resolved_errors,
					detail: `${formatPercent(analytics.overview.resolution_rate)} resolution rate`,
				},
				{
					label: 'First-Try Success',
					value: analytics.overview.first_attempt_successes,
					detail: `${formatPercent(analytics.overview.first_attempt_success_rate)} of all errors`,
				},
				{
					label: 'Hint Usage',
					value: analytics.overview.hint_shown_errors,
					detail: `${formatPercent(analytics.overview.hint_usage_rate)} needed support`,
				},
			]
			: [],
	);
</script>

{#if loading}
	<div class="flex min-h-screen items-center justify-center">
		<p class="text-gray-500">Loading your progress...</p>
	</div>
{:else if errorMessage}
	<div class="mx-auto max-w-5xl p-6">
		<div class="rounded-3xl border border-red-200 bg-red-50 p-6 text-red-700 shadow-sm">
			<h1 class="text-2xl font-bold">Progress unavailable</h1>
			<p class="mt-3 text-sm">{errorMessage}</p>
		</div>
	</div>
{:else if analytics}
	<div class="mx-auto max-w-6xl p-6">
		<section class="overflow-hidden rounded-[2rem] border border-stone-200 bg-white shadow-sm">
			<div class="bg-[linear-gradient(135deg,#1f2937_0%,#334155_45%,#d1fae5_100%)] px-6 py-10 text-white sm:px-8">
				<p class="text-xs font-semibold uppercase tracking-[0.28em] text-emerald-100">My Progress</p>
				<div class="mt-4 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
					<div class="max-w-2xl">
						<h1 class="text-3xl font-bold tracking-tight sm:text-4xl">
							{analytics.student.full_name || analytics.student.username}
						</h1>
						<p class="mt-3 text-sm leading-6 text-slate-100 sm:text-base">
							This dashboard shows how often each error category appears, how often you solve issues on the first try, and where hints or answer reveals still show up across submissions.
						</p>
					</div>
					<div class="grid gap-3 sm:grid-cols-2">
						<div class="rounded-2xl border border-white/20 bg-white/10 px-4 py-3 backdrop-blur-sm">
							<p class="text-xs uppercase tracking-[0.2em] text-emerald-100">Total Errors</p>
							<p class="mt-2 text-3xl font-bold">{analytics.overview.total_errors}</p>
						</div>
						<div class="rounded-2xl border border-white/20 bg-white/10 px-4 py-3 backdrop-blur-sm">
							<p class="text-xs uppercase tracking-[0.2em] text-emerald-100">Avg Attempts</p>
							<p class="mt-2 text-3xl font-bold">{analytics.overview.avg_attempts_per_error.toFixed(2)}</p>
						</div>
					</div>
				</div>
			</div>

			<div class="grid gap-4 px-6 py-6 sm:grid-cols-2 xl:grid-cols-4 sm:px-8">
				{#each headlineCards as card}
					<div class="rounded-2xl border border-stone-200 bg-stone-50 px-4 py-4">
						<p class="text-xs font-semibold uppercase tracking-[0.2em] text-stone-500">{card.label}</p>
						<p class="mt-3 text-3xl font-bold text-stone-900">{card.value}</p>
						<p class="mt-2 text-sm text-stone-600">{card.detail}</p>
					</div>
				{/each}
			</div>
		</section>

		<section class="mt-8 grid gap-8 xl:grid-cols-[1.4fr_1fr]">
			<div class="rounded-[2rem] border border-stone-200 bg-white p-6 shadow-sm sm:p-8">
				<div class="flex items-end justify-between gap-4">
					<div>
						<p class="text-xs font-semibold uppercase tracking-[0.25em] text-stone-500">Category Trends</p>
						<h2 class="mt-2 text-2xl font-bold text-stone-900">Where grammar patterns repeat</h2>
					</div>
					<p class="max-w-sm text-right text-sm text-stone-500">
						Each row combines a total error count, hint pressure, and a mini time-series across submissions.
					</p>
				</div>

				<div class="mt-6 space-y-4">
					{#each analytics.category_breakdown as category}
						<div class="rounded-3xl border border-stone-200 bg-stone-50/80 p-4">
							<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
								<div class="min-w-0 flex-1">
									<div class="flex flex-wrap items-center gap-3">
										<h3 class="text-lg font-semibold capitalize text-stone-900">
											{category.error_category.replace('_', ' ')}
										</h3>
										<span class="rounded-full bg-stone-900 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-white">
											{category.total_errors} errors
										</span>
									</div>
									<p class="mt-2 text-sm text-stone-600">{categoryTrendLabel(category)}</p>

									<div class="mt-4 h-3 overflow-hidden rounded-full bg-stone-200">
										<div
											class="h-full rounded-full bg-gradient-to-r from-emerald-500 via-sky-500 to-indigo-600"
											style={`width: ${barWidth(category.total_errors, maxCategoryErrors)}`}
										></div>
									</div>

									<div class="mt-4 grid gap-3 sm:grid-cols-3">
										<div class="rounded-2xl bg-white px-3 py-3">
											<p class="text-xs uppercase tracking-[0.18em] text-stone-500">First Try</p>
											<p class="mt-2 text-xl font-bold text-stone-900">{formatPercent(category.first_attempt_success_rate)}</p>
										</div>
										<div class="rounded-2xl bg-white px-3 py-3">
											<p class="text-xs uppercase tracking-[0.18em] text-stone-500">Hints</p>
											<p class="mt-2 text-xl font-bold text-stone-900">{category.hint_shown_errors}</p>
										</div>
										<div class="rounded-2xl bg-white px-3 py-3">
											<p class="text-xs uppercase tracking-[0.18em] text-stone-500">Avg Attempts</p>
											<p class="mt-2 text-xl font-bold text-stone-900">{category.avg_attempts_per_error.toFixed(2)}</p>
										</div>
									</div>
								</div>

								<div class="w-full max-w-[12rem] rounded-3xl border border-stone-200 bg-white p-4">
									<p class="text-xs font-semibold uppercase tracking-[0.2em] text-stone-500">Timeline</p>
									{#if Sparkline}
										<Sparkline points={sparkline(category.timeline)} />
									{:else}
										<div class="mt-4 h-16 w-full animate-pulse rounded bg-stone-200"></div>
									{/if}
									<div class="mt-2 flex items-center justify-between text-xs text-stone-500">
										<span>{formatDate(category.timeline[0]?.submitted_at)}</span>
										<span>{formatDate(category.timeline[category.timeline.length - 1]?.submitted_at)}</span>
									</div>
								</div>
							</div>
						</div>
					{/each}
				</div>
			</div>

			<div class="space-y-8">
				<div class="rounded-[2rem] border border-stone-200 bg-white p-6 shadow-sm sm:p-8">
					<p class="text-xs font-semibold uppercase tracking-[0.25em] text-stone-500">Support Signals</p>
					<h2 class="mt-2 text-2xl font-bold text-stone-900">Revision behavior</h2>
					<div class="mt-6 space-y-4">
						<div class="rounded-2xl bg-amber-50 px-4 py-4">
							<p class="text-xs uppercase tracking-[0.2em] text-amber-700">Hints shown</p>
							<p class="mt-2 text-3xl font-bold text-amber-900">{analytics.overview.hint_shown_errors}</p>
							<p class="mt-2 text-sm text-amber-800">{formatPercent(analytics.overview.hint_usage_rate)} of all errors needed extra support.</p>
						</div>
						<div class="rounded-2xl bg-rose-50 px-4 py-4">
							<p class="text-xs uppercase tracking-[0.2em] text-rose-700">Manual reveals</p>
							<p class="mt-2 text-3xl font-bold text-rose-900">{analytics.overview.manual_reveal_count}</p>
							<p class="mt-2 text-sm text-rose-800">Answer reveals show where independent correction still breaks down.</p>
						</div>
						<div class="rounded-2xl bg-emerald-50 px-4 py-4">
							<p class="text-xs uppercase tracking-[0.2em] text-emerald-700">Resolved</p>
							<p class="mt-2 text-3xl font-bold text-emerald-900">{analytics.overview.resolved_errors}</p>
							<p class="mt-2 text-sm text-emerald-800">{formatPercent(analytics.overview.resolution_rate)} of detected errors are resolved.</p>
						</div>
					</div>
				</div>

				<div class="rounded-[2rem] border border-stone-200 bg-white p-6 shadow-sm sm:p-8">
					<p class="text-xs font-semibold uppercase tracking-[0.25em] text-stone-500">Submission Timeline</p>
					<h2 class="mt-2 text-2xl font-bold text-stone-900">Assignments over time</h2>
					<div class="mt-6 space-y-4">
						{#each analytics.submissions as submission}
							<a
								href={`/submissions/${submission.submission_id}`}
								class="block rounded-3xl border border-stone-200 bg-stone-50/80 p-4 transition hover:border-stone-300 hover:bg-white"
							>
								<div class="flex items-start justify-between gap-4">
									<div>
										<h3 class="text-lg font-semibold text-stone-900">{submission.title}</h3>
										<p class="mt-1 text-sm text-stone-500">{formatDate(submission.submitted_at)} · {submission.status.replace('_', ' ')}</p>
									</div>
									<span class="rounded-full bg-stone-900 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-white">
										{submission.total_errors} errors
									</span>
								</div>

								<div class="mt-4 h-2 overflow-hidden rounded-full bg-stone-200">
									<div
										class="h-full rounded-full bg-gradient-to-r from-sky-500 to-indigo-600"
										style={`width: ${barWidth(submission.total_errors, maxSubmissionErrors)}`}
									></div>
								</div>

								<div class="mt-4 grid gap-3 sm:grid-cols-3">
									<div>
										<p class="text-xs uppercase tracking-[0.18em] text-stone-500">Resolved</p>
										<p class="mt-1 text-lg font-semibold text-stone-900">{submission.resolved_errors}</p>
									</div>
									<div>
										<p class="text-xs uppercase tracking-[0.18em] text-stone-500">First Try</p>
										<p class="mt-1 text-lg font-semibold text-stone-900">{submission.first_attempt_successes}</p>
									</div>
									<div>
										<p class="text-xs uppercase tracking-[0.18em] text-stone-500">Hints</p>
										<p class="mt-1 text-lg font-semibold text-stone-900">{submission.hint_shown_errors}</p>
									</div>
								</div>
							</a>
						{/each}
					</div>
				</div>
			</div>
		</section>
	</div>
{/if}