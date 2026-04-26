<script setup lang="ts">
import type { TopicData } from '../types';

defineProps<{
  isOpen: boolean;
  title: string;
  subtitle?: string;
  data: any;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();
</script>

<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="emit('close')">
    <div class="modal-content">
      <button class="close-btn" @click="emit('close')">✕</button>
      <h2>{{ title }}</h2>
      <h4 v-if="subtitle" class="subtitle">{{ subtitle }}</h4>

      <hr />

      <div class="topics-list" v-if="data && data.length > 0">
        <div v-for="(item, index) in data" :key="index" class="topic-card">
          <div class="topic-header">
            <strong>{{ item.topic || item.Topic }}</strong>
            <span class="topic-count">Count: {{ item.count || item.Count }}</span>
          </div>
          <div class="topic-type">Type: {{ item.type || item.Type }}</div>

          <div v-if="item.subtopics && Object.keys(item.subtopics).length > 0" class="subtopics">
            <span v-for="(count, year) in item.subtopics" :key="year" class="subtopic-badge">
              {{ year }}: {{ count }}
            </span>
          </div>
        </div>
      </div>

      <div class="debug-dump">
        <p style="margin: 0 0 8px 0; color: #ffeb3b;"><b>Debug - Raw Data Shape:</b></p>
        <pre>{{ JSON.stringify(data, null, 2) }}</pre>
      </div>

    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-content {
  background: white;
  padding: 24px;
  border-radius: 12px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
  position: relative;
  box-shadow: 0 10px 25px rgba(0,0,0,0.2);
}

.close-btn {
  position: absolute;
  top: 16px; right: 16px;
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #666;
}

.subtitle {
  color: #666;
  margin-top: -10px;
  margin-bottom: 15px;
}

hr {
  border: 0;
  height: 1px;
  background: #eee;
  margin-bottom: 16px;
}

.topics-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.topic-card {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 12px;
}

.topic-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.topic-count {
  font-size: 12px;
  background: #e9ecef;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 600;
}

.topic-type {
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
}

.subtopics {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.subtopic-badge {
  font-size: 11px;
  background: #e3f2fd;
  color: #1976d2;
  padding: 2px 6px;
  border-radius: 4px;
}

/* Debug Box Styles */
.debug-dump {
  margin-top: 20px;
  background: #2d2d2d;
  color: #a4e400;
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  overflow-x: auto;
  max-height: 300px;
}
</style>