<script setup lang="ts">
import { ref, onMounted, computed, watchEffect } from 'vue';
import { VueFlow, useVueFlow, Position } from '@vue-flow/core';
import { Background } from '@vue-flow/background';
import { Controls } from '@vue-flow/controls';
import '@vue-flow/core/dist/style.css';
import '@vue-flow/core/dist/theme-default.css';
import type { Edge, Node, NodeMouseEvent } from '@vue-flow/core';

// 声明props
interface Module {
  id: number;
  name: string;
  description: string;
  difficulty: 1 | 2 | 3 | 4 | 5;
  type: string;
  status: 'available' | 'locked' | 'completed';
  prerequisites?: number[];
  estimatedTime: string;
  score?: number;
}

interface Props {
  modules: Module[];
  onSelectModule?: (moduleId: number) => void;
}

const props = defineProps<Props>();

const { nodes, edges, onNodesChange, onEdgesChange, onConnect, addNodes, addEdges } = useVueFlow();

// 根据难度获取不同颜色
const getDifficultyColor = (difficulty: number) => {
  const colors = {
    1: 'hsl(142, 76%, 36%)', // 深绿色
    2: 'hsl(122, 39%, 49%)', // 绿色
    3: 'hsl(48, 96%, 53%)',  // 黄色
    4: 'hsl(36, 100%, 50%)', // 橙色
    5: 'hsl(4, 90%, 58%)',   // 红色
  };
  return colors[difficulty as keyof typeof colors];
};

// 根据状态获取样式
const getStatusStyle = (status: string) => {
  const styles = {
    completed: { 
      border: '3px solid hsl(142, 76%, 36%)', 
      background: 'oklch(var(--b1))', 
      boxShadow: '0 4px 12px rgba(76, 175, 80, 0.3)' 
    },
    available: { 
      border: '3px solid hsl(217, 91%, 60%)', 
      background: 'oklch(var(--b1))',
      boxShadow: '0 4px 12px rgba(33, 150, 243, 0.3)' 
    },
    locked: { 
      border: '3px solid hsl(215, 16%, 47%)', 
      background: 'hsl(220, 14%, 96%)',
      boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' 
    },
  };
  return styles[status as keyof typeof styles];
};

// 获取连接线颜色
const getEdgeColor = (status: string) => {
  const colors = {
    available: 'hsl(217, 91%, 60%)',  // 蓝色
    completed: 'hsl(142, 76%, 36%)',  // 绿色
    locked: 'hsl(215, 16%, 47%)'      // 灰色
  };
  return colors[status as keyof typeof colors];
};

// 初始化图表
const initializeGraph = () => {
  const moduleNodes: Node[] = [];
  const moduleEdges: Edge[] = [];
  
  // 创建节点
  props.modules.forEach((module, index) => {
    const statusStyle = getStatusStyle(module.status);
    const nodeData = {
      id: module.id.toString(),
      position: { x: 0, y: 0 }, // 初始位置，后面会自动布局
      data: { 
        label: module.name,
        module: module,
      },
      type: 'default',
      style: {
        width: 200,
        padding: '12px',
        borderRadius: '12px',
        fontSize: '14px',
        ...statusStyle,
      },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
    };
    
    moduleNodes.push(nodeData);
  });

  // 自动布局节点位置（简单的层次布局）
  const levelMap = new Map<number, number[]>();
  
  // 先找出没有前置依赖的节点，放在第一层
  moduleNodes.forEach(node => {
    const module = props.modules.find(m => m.id.toString() === node.id);
    if (!module?.prerequisites || module.prerequisites.length === 0) {
      if (!levelMap.has(0)) levelMap.set(0, []);
      levelMap.get(0)?.push(parseInt(node.id));
    }
  });

  // 根据前置依赖确定其他节点的层级
  let currentLevel = 0;
  const processed = new Set<number>();
  
  while (levelMap.has(currentLevel)) {
    const nodesInCurrentLevel = levelMap.get(currentLevel) || [];
    
    nodesInCurrentLevel.forEach(nodeId => {
      processed.add(nodeId);
      
      // 找出以这个节点为前置依赖的节点
      props.modules.forEach(module => {
        if (module.prerequisites?.includes(nodeId) && !processed.has(module.id)) {
          const nextLevel = currentLevel + 1;
          if (!levelMap.has(nextLevel)) levelMap.set(nextLevel, []);
          levelMap.get(nextLevel)?.push(module.id);
        }
      });
    });
    
    currentLevel++;
  }

  // 根据层级设置节点位置
  const LEVEL_HEIGHT = 180;
  const NODE_WIDTH = 220;
  const NODE_PADDING = 70;
  
  levelMap.forEach((nodeIds, level) => {
    const levelWidth = nodeIds.length * (NODE_WIDTH + NODE_PADDING);
    const startX = -(levelWidth / 2) + (NODE_WIDTH / 2);
    
    nodeIds.forEach((nodeId, index) => {
      const node = moduleNodes.find(n => n.id === nodeId.toString());
      if (node) {
        node.position = {
          x: startX + index * (NODE_WIDTH + NODE_PADDING),
          y: level * LEVEL_HEIGHT
        };
      }
    });
  });

  // 创建边（连接）
  props.modules.forEach(module => {
    if (module.prerequisites && module.prerequisites.length > 0) {
      module.prerequisites.forEach(prereqId => {
        const edge: Edge = {
          id: `e${prereqId}-${module.id}`,
          source: prereqId.toString(),
          target: module.id.toString(),
          style: {
            strokeWidth: 3,
            stroke: getEdgeColor(module.status),
          },
          markerEnd: 'arrow',
          animated: module.status === 'available',
          labelStyle: { fill: 'oklch(var(--bc))', fontWeight: 'bold' }
        };
        
        moduleEdges.push(edge);
      });
    }
  });

  // 添加节点和边到图
  addNodes(moduleNodes);
  addEdges(moduleEdges);
};

// 处理节点点击事件
const onNodeClick = (event: NodeMouseEvent) => {
  const nodeId = event.node.id;
  if (props.onSelectModule) {
    props.onSelectModule(parseInt(nodeId));
  }
};

// 初始化图表
onMounted(() => {
  initializeGraph();
});

// 当模块数据变化时重新初始化图表
watchEffect(() => {
  if (props.modules && props.modules.length > 0) {
    // 清空已有节点和边
    nodes.value = [];
    edges.value = [];
    // 重新初始化
    initializeGraph();
  }
});
</script>

<template>
  <div class="module-dependency-graph">
    <VueFlow
      :default-viewport="{ x: 0, y: 0, zoom: 1 }"
      :min-zoom="0.2"
      :max-zoom="2"
      fit-view-on-init
      @nodeClick="onNodeClick"
      class="graph-container"
    >
      <template #node-default="{ data }">
        <div class="custom-node">
          <div class="node-header" :style="{ backgroundColor: getDifficultyColor(data.module.difficulty) }">
            {{ data.module.name }}
          </div>
          <div class="node-content">
            <div class="difficulty">
              <span class="difficulty-title">难度:</span> 
              <span class="difficulty-stars">{{ '★'.repeat(data.module.difficulty) }}{{ '☆'.repeat(5 - data.module.difficulty) }}</span>
            </div>
            <div class="status">
              <span v-if="data.module.status === 'completed'" class="status-completed">
                <i class="fas fa-check-circle"></i> 已完成
              </span>
              <span v-else-if="data.module.status === 'available'" class="status-available">
                <i class="fas fa-unlock"></i> 可开始
              </span>
              <span v-else class="status-locked">
                <i class="fas fa-lock"></i> 未解锁
              </span>
            </div>
          </div>
        </div>
      </template>
      
      <Background pattern="dots" :gap="20" :size="1" :patternColor="'oklch(var(--b3))'" />
      <Controls />
    </VueFlow>
  </div>
</template>

<style scoped>
.module-dependency-graph {
  width: 100%;
  height: 500px;
  background-color: hsl(var(--b2));
  border-radius: 12px;
  overflow: hidden;
  border: 2px solid oklch(var(--b3));
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08);
}

.graph-container {
  width: 100%;
  height: 100%;
}

.graph-container :deep(.vue-flow__pane) {
  cursor: grab;
}

.graph-container :deep(.vue-flow__pane.dragging) {
  cursor: grabbing;
}

.graph-container :deep(.vue-flow__controls) {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid oklch(var(--b3));
}

.graph-container :deep(.vue-flow__controls-button) {
  background-color: hsl(var(--b1));
  border-bottom: 1px solid oklch(var(--b3));
  color: hsl(var(--bc));
  width: 28px;
  height: 28px;
  transition: all 0.2s ease;
  font-weight: bold;
}

.graph-container :deep(.vue-flow__controls-button:hover) {
  background-color: oklch(var(--p));
  color: white;
}

.graph-container :deep(.vue-flow__edge-path) {
  stroke-width: 3;
}

.graph-container :deep(.vue-flow__edge.animated path) {
  stroke-dasharray: 5;
  animation: dashdraw 0.5s linear infinite;
}

.graph-container :deep(.vue-flow__edge-text) {
  font-weight: bold;
  fill: oklch(var(--bc));
  text-shadow: 0 0 3px hsl(var(--b1));
}

.graph-container :deep(.vue-flow__edge-textbg) {
  fill: hsl(var(--b1));
}

@keyframes dashdraw {
  from {
    stroke-dashoffset: 10;
  }
}

.custom-node {
  border-radius: 12px;
  overflow: hidden;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.custom-node:hover {
  transform: translateY(-5px) scale(1.02);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
  z-index: 10;
}

.node-header {
  padding: 12px;
  color: white;
  font-weight: bold;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border-top-left-radius: 10px;
  border-top-right-radius: 10px;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
  font-size: 15px;
  letter-spacing: 0.5px;
}

.node-content {
  padding: 15px;
  font-size: 14px;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: hsl(var(--b1));
  color: hsl(var(--bc));
  border-bottom-left-radius: 10px;
  border-bottom-right-radius: 10px;
}

.difficulty {
  margin-bottom: 10px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
}

.difficulty-title {
  color: hsl(var(--bc) / 0.7);
}

.difficulty-stars {
  color: hsl(45, 100%, 51%);
  letter-spacing: 1px;
}

.status {
  font-weight: bold;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 6px;
  background-color: hsla(210, 20%, 98%, 0.8);
}

.status-completed {
  color: hsl(142, 76%, 36%);
}

.status-available {
  color: hsl(217, 91%, 60%);
}

.status-locked {
  color: hsl(215, 16%, 47%);
}
</style> 