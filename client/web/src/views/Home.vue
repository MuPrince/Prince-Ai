<script setup lang="ts">
import { ref } from 'vue'
import FeatureList from '@/components/FeatureList.vue'
import FeatureTabs from '@/components/FeatureTabs.vue'

const activeFeature = ref('rag')

const handleFeatureSelect = (code: string) => {
  activeFeature.value = code
}
</script>

<template>
  <div class="home-page">
    <div class="main-container">
      <div class="left-panel">
        <FeatureList @select="handleFeatureSelect" />
      </div>
      <div class="right-panel">
        <FeatureTabs :initial-code="activeFeature" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-page {
  height: 100vh;
  width: 100vw;
  background: #f1f5f9;
  padding: 20px;
  box-sizing: border-box;
}

.main-container {
  display: flex;
  height: 100%;
  gap: 16px;
}

.left-panel {
  width: 20%;
  height: 100%;
}

.right-panel {
  width: 80%;
  height: 100%;
}
</style>
