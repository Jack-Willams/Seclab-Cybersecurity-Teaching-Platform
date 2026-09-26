<script setup lang="ts">
import { CommandInjectionExperiment } from '../../../data/CommandInjectionExperiment';
import MarkdownRenderer from "../../../components/MarkdownRenderer.vue";
</script>

<template>
  <div class="container mx-auto px-4 py-8">
    <div class="bg-base-200 p-4 shadow-lg rounded-lg mb-6">
      <div class="flex justify-between items-center">
        <div class="flex items-center gap-2">
          <i class="fas fa-terminal text-primary text-2xl"></i>
          <h1 class="text-2xl font-bold">{{ CommandInjectionExperiment.name }}</h1>
        </div>
        <div class="text-yellow-500">
          <i class="fas fa-star mr-2"></i>
          难度: {{ '★'.repeat(CommandInjectionExperiment.difficulty) + '☆'.repeat(5 - CommandInjectionExperiment.difficulty) }}
        </div>
      </div>
      <p class="mt-2">{{ CommandInjectionExperiment.introduction }}</p>
    </div>

    <div class="space-y-6">
      <div v-for="task in CommandInjectionExperiment.taskPoints" :key="task.id" 
           class="card bg-base-100 shadow-xl">
        <div class="card-body">
          <div class="flex justify-between">
            <h2 class="card-title">
              <i class="fas fa-tasks text-primary mr-2"></i>
              {{ task.name }}
            </h2>
            <div class="badge badge-primary badge-lg">
              <span class="font-bold">{{ task.score }}</span>分
            </div>
          </div>
          
          <p>{{ task.description }}</p>
          
          <div class="mt-4">
            <h3 class="font-semibold mb-2">任务说明</h3>
            <div class="card bg-base-200 p-4 w-full overflow-x-auto">
              <div class="prose prose-sm max-w-none break-words">
                <MarkdownRenderer :content="task.document" />
              </div>
            </div>
          </div>
          
          <div v-if="task.questions && task.questions.length > 0" class="mt-4 space-y-4">
            <h3 class="font-semibold">问题</h3>
            <div v-for="question in task.questions" :key="question.id" 
                 class="card bg-base-300 p-4">
              <div class="flex justify-between items-center">
                <p>{{ question.content }}</p>
                <span class="badge">{{ question.score }}分</span>
              </div>
              
              <div v-if="question.options" class="mt-4 space-y-2">
                <div v-for="(option, index) in question.options" :key="index" 
                     class="flex items-center gap-2">
                  <input type="radio" :name="'q' + question.id" class="radio radio-primary" />
                  <span>{{ option }}</span>
                </div>
              </div>
              
              <div v-if="question.type === 'open-ended-with-answer' || 
                         question.type === 'open-ended-without-answer'" 
                   class="mt-4">
                <textarea class="textarea textarea-bordered w-full h-24" 
                          placeholder="请输入答案"></textarea>
                <button class="btn btn-primary mt-2">提交答案</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template> 