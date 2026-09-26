<script setup lang="ts">
import { XSSExperiment } from '../../../data/XSSExperiment';
</script>

<template>
  <div class="container p-4">
    <h1 class="text-2xl font-bold mb-4">{{ XSSExperiment.name }}</h1>
    <p class="mb-4">{{ XSSExperiment.introduction }}</p>
    
    <div v-for="task in XSSExperiment.taskPoints" :key="task.id" class="mb-6 p-4 border rounded">
      <h2 class="text-xl font-bold">{{ task.name }}</h2>
      <p>{{ task.description }}</p>
      
      <div class="mt-4">
        <h3 class="font-bold">任务文档：</h3>
        <pre class="whitespace-pre-wrap mt-2 p-2 bg-gray-100 rounded">{{ task.document }}</pre>
      </div>
      
      <div v-if="task.questions && task.questions.length > 0" class="mt-4">
        <h3 class="font-bold">问题：</h3>
        <div v-for="question in task.questions" :key="question.id" class="mt-2 p-2 bg-gray-50 rounded">
          <p>{{ question.content }}</p>
          <p class="text-sm text-gray-600">分值：{{ question.score }}</p>
          
          <div v-if="question.options" class="mt-2">
            <div v-for="(option, index) in question.options" :key="index" class="ml-4">
              - {{ option }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template> 