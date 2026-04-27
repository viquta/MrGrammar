<script lang="ts">
	let { points = '' } = $props<{ points?: string }>();
</script>

<svg viewBox="0 0 80 36" class="mt-4 h-16 w-full overflow-visible">
	<polyline
		fill="none"
		stroke="rgb(15 23 42)"
		stroke-width="2.5"
		stroke-linecap="round"
		stroke-linejoin="round"
		points={points}
	></polyline>
</svg>
