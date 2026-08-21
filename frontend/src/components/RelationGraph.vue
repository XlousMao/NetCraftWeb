<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { Network } from 'vis-network/standalone'
import { useRouter } from 'vue-router'

const props = defineProps<{ nodes: any[]; edges: any[] }>()
const router = useRouter()
const container = ref<HTMLElement>()
let network: Network | null = null

function build() {
  if (!container.value) return
  const nodeColor = (type: string) => {
    switch (type) {
      case 'item':
        return { background: '#3b82f6', border: '#2563eb', highlight: '#60a5fa' }
      case 'dungeon':
        return { background: '#8b5cf6', border: '#7c3aed', highlight: '#a78bfa' }
      case 'recipe':
        return { background: '#f59e0b', border: '#d97706', highlight: '#fbbf24' }
      case 'equipment':
        return { background: '#10b981', border: '#059669', highlight: '#34d399' }
      default:
        return { background: '#6b7280', border: '#4b5563', highlight: '#9ca3af' }
    }
  }

  const visNodes = props.nodes.map((n) => ({
    id: n.id,
    label: n.label,
    color: nodeColor(n.type),
    font: { color: '#374151', size: 14 },
    shape: 'box',
    margin: 8,
  }))
  const visEdges = props.edges.map((e) => ({
    from: e.from,
    to: e.to,
    label: `${e.label}${e.quantity ? ' ×' + e.quantity : ''}`,
    arrows: 'to',
    font: { size: 11, color: '#6b7280', align: 'middle' },
    color: { color: '#c0c4cc', highlight: '#3b82f6' },
  }))

  network = new Network(container.value, { nodes: visNodes, edges: visEdges }, {
    physics: { enabled: true, solver: 'forceAtlas2Based' },
    interaction: { hover: true, tooltipDelay: 100 },
  })
  network.on('click', (params: any) => {
    if (params.nodes.length) {
      const id: string = params.nodes[0]
      const [type, rawId] = id.split(':')
      if (type === 'item') router.push(`/items/${rawId}`)
      else if (type === 'dungeon') router.push('/dungeons')
      else if (type === 'recipe') router.push('/recipes')
      else if (type === 'equipment') router.push('/equipments')
    }
  })
}

onMounted(build)
onBeforeUnmount(() => network?.destroy())

watch(() => [props.nodes, props.edges], () => {
  network?.destroy()
  build()
})
</script>

<template>
  <div ref="container" class="graph-container"></div>
</template>
