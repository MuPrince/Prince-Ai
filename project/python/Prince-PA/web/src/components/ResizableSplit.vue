<script setup lang="ts">
import { ref } from 'vue'
import { applyRatio } from '@/utils/resize'

const props = defineProps<{ leftRatio: number }>()
const emit = defineEmits<{ (e: 'update:leftRatio', value: number): void }>()
const root = ref<HTMLDivElement | null>(null)

function onPointerDown(e: PointerEvent) {
  const startX = e.clientX
  const startRatio = props.leftRatio
  const onMove = (ev: PointerEvent) => {
    const rect = root.value?.getBoundingClientRect()
    if (!rect) return
    const deltaPercent = ((ev.clientX - startX) / rect.width) * 100
    const nextRatio = (startRatio + deltaPercent) / 100
    emit('update:leftRatio', applyRatio(nextRatio, 1, 0.2))
  }
  const onUp = () => {
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
  }
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
}
</script>

<template>
  <div ref="root" class="resizable-split">
    <div class="pane left-pane" :style="{ flexBasis: `${leftRatio}%` }">
      <slot name="left" />
    </div>
    <div class="divider" @pointerdown="onPointerDown" />
    <div class="pane right-pane" :style="{ flexBasis: `${100 - leftRatio}%` }">
      <slot name="right" />
    </div>
  </div>
</template>

<style scoped>
.resizable-split {
  display: flex;
  width: 100%;
  height: 100%;
  overflow: hidden;
}
.pane {
  min-width: 0;
  overflow: hidden;
}
.divider {
  width: 6px;
  cursor: col-resize;
  background: #d1d5db;
  flex: 0 0 6px;
}
</style>
