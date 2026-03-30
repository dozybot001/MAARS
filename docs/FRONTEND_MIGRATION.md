# Frontend Migration Plan: Vanilla JS → Vue 3

## 技术选型

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | ^3.5 | UI 框架（Composition API） |
| Pinia | ^2.2 | 状态管理 |
| Vite | ^6.0 | 构建工具 + 开发服务器 |
| @vitejs/plugin-vue | ^5.0 | Vue SFC 编译 |

不引入 Vue Router（单页面）、不引入 UI 库（保留现有样式）。

## 目标文件结构

```
frontend/
├── index.html              # Vite 入口
├── package.json
├── vite.config.js
├── src/
│   ├── main.js             # createApp + Pinia
│   ├── App.vue             # 根组件：ProgressBar + Workspace + CommandPalette + Modal
│   ├── eventBus.js         # 轻量事件总线（chunk 流不走 store）
│   ├── api.js              # fetch 封装（复用原有逻辑）
│   │
│   ├── stores/
│   │   └── pipeline.js     # 中心化 Pinia store
│   │
│   ├── composables/
│   │   ├── useSSE.js       # SSE 连接 → store + eventBus
│   │   └── useAutoScroll.js # 自动滚动
│   │
│   ├── components/
│   │   ├── ProgressBar.vue     # 7 节点进度条 + Docker 状态
│   │   ├── CommandPalette.vue  # Ctrl+K 命令面板
│   │   ├── AppModal.vue        # 文档预览模态框
│   │   ├── LogViewer.vue       # 推理日志（混合模式）
│   │   ├── ProcessViewer.vue   # 过程与输出
│   │   ├── DecompTree.vue      # 分解树（递归组件）
│   │   └── ExecList.vue        # 执行批次列表
│   │
│   └── styles/             # 全局样式（从旧 CSS 迁移）
│       ├── variables.css
│       ├── layout.css
│       ├── workspace.css
│       ├── cards.css
│       └── tree.css
│
└── dist/                   # 构建产物（.gitignore）
```

## 架构设计

### 数据流

```
SSE (EventSource)
  │
  ├─→ Pinia Store ─→ 所有组件（响应式）
  │     结构性数据：阶段状态、节点状态、文档、任务树、分数
  │
  └─→ EventBus ─→ LogViewer（直接 DOM 操作）
        高频数据：chunk 文本流、tool 调用事件
```

**核心原则**：结构性变更走 store（低频、需要多组件共享），流式文本走 eventBus（高频、仅 LogViewer 消费）。

### Pinia Store 设计

```js
// stores/pipeline.js — 单一 store，所有共享状态

{
  // 阶段状态
  stageStates: { refine: 'idle', research: 'idle', write: 'idle' },
  nodeStates: { refine, calibrate, strategy, decompose, execute, evaluate, write },
  activeStage: null,
  currentPhase: null,

  // 计时 & 计数
  timerStart: null,
  totalTokens: 0,
  lastActivityTime: null,

  // 结构化数据
  documents: {},           // name → { label, content, meta }
  taskDescriptions: {},    // taskId → description
  taskStates: {},          // taskId → { status, summary }
  decompTree: null,        // 分解树对象
  execBatches: [],         // 执行批次列表
  scores: [],              // [{ current, previous, improved }]
  errors: [],              // [{ stage, message }]

  // 派生状态
  pipelineState: computed  // 'idle' | 'running' | 'paused' | 'pausing'
}
```

### 事件总线（非响应式）

```js
// eventBus.js — 轻量 pub/sub，避免高频 chunk 进入 Vue 响应式系统

{ on(event, fn), off(event, fn), emit(event, data) }

// 事件类型：
// 'chunk' — { stage, data: { text, call_id, label, level, task_id } }
// 'tokens' — { stage, data: { input, output, total } }
// 'error' — { stage, data: { message } }
// 'phase' — { stage, data: phaseStr }
// 'task_state' — { stage, data: { task_id, status, summary } }
```

### SSE 分发逻辑

```js
// composables/useSSE.js

SSE event    →  Store action           →  EventBus emit
─────────────────────────────────────────────────────────
state        →  store.handleStageState →  (不需要)
phase        →  store.handlePhase      →  eventBus.emit('phase')
chunk        →  store.markActivity()   →  eventBus.emit('chunk')
task_state   →  store.updateTaskState  →  eventBus.emit('task_state')
exec_tree    →  store.setExecBatches   →  (不需要)
tree         →  store.decompTree =     →  (不需要)
tokens       →  store.addTokens       →  eventBus.emit('tokens')
document     →  store.addDocument      →  (不需要)
score        →  store.addScore         →  (不需要)
error        →  store.addError         →  eventBus.emit('error')
```

## 组件映射（旧 → 新）

| 旧文件 | 新组件 | 迁移策略 |
|--------|--------|----------|
| `pipeline-ui.js` (进度条部分) | `ProgressBar.vue` | 纯声明式。`v-for` 渲染节点，`:data-state` 绑定 store |
| `pipeline-ui.js` (命令面板部分) | `CommandPalette.vue` | 纯声明式。`v-model` 绑定输入，按钮状态从 store 派生 |
| `modal.js` | `AppModal.vue` | 纯声明式。`v-if` 控制显示，props 传入标题/内容 |
| `process-viewer.js` | `ProcessViewer.vue` | 纯声明式。watch store 数据渲染文档卡片、树、批次列表、分数 |
| `process-viewer.js` (树渲染) | `DecompTree.vue` | 递归组件。`:node` prop，`v-for` 渲染子节点 |
| `process-viewer.js` (批次列表) | `ExecList.vue` | 声明式。从 store 读取 batches + taskStates |
| `log-viewer.js` | `LogViewer.vue` | **混合模式**。Vue 管理 header badges；内容区保留 DOM 操作 |
| `autoscroll.js` | `useAutoScroll.js` | composable，接受 ref(element)，返回 { scroll, reset, isLocked } |
| `events.js` | `eventBus.js` | 简化为纯 JS pub/sub（不用 DOM CustomEvent） |
| `api.js` | `api.js` | 几乎不变，去掉对旧 events.js 的依赖 |
| `shared.js` | 删除 | `STAGE_LABELS` 移到 store 常量；`createFold` 移到 LogViewer 内部；`safeParse` 移到 useSSE |

## LogViewer 详细设计（最复杂组件）

### 为什么用混合模式

LogViewer 接收高频 chunk 流（每秒数十次），每次追加文本到特定 fold 节点。如果用纯 Vue 响应式：
- 每个 chunk 触发 reactive 更新 → diff → patch → 性能瓶颈
- fold 树结构是动态的（由 chunk 事件的 `call_id` + `level` 决定），难以预先声明模板

**方案**：Vue 管理组件生命周期和 header 状态，fold/chunk 内容用原生 DOM 操作。

### 结构

```vue
<template>
  <div class="panel">
    <div class="panel-header">
      <h3>Reasoning Log</h3>
      <span class="activity-badge" v-if="activityText" :data-state="activityState">
        {{ activityText }}
      </span>
      <span class="token-badge">{{ tokenDisplay }}</span>
      <button @click="copyLog">Copy</button>
    </div>
    <div ref="logOutput" class="panel-body" id="log-output"></div>
  </div>
</template>

<script setup>
// Header: 响应式 computed 从 store 读取
// 内容: onMounted 中设置 eventBus 监听，port 原有 DOM 逻辑
// onUnmounted 清理监听器
</script>
```

### 内部状态（非响应式，仅 DOM 引用）

```js
// 这些是 LogViewer 内部的 JS 变量，不进 Vue 响应式系统
let currentSection = null                    // 当前 stage section DOM 元素
let phaseGroups = {}                         // callId → { label, body } DOM 引用
let taskGroups = {}                          // taskId → { label, body } DOM 引用
let callBlocks = {}                          // callId → text block DOM 元素
let callScrollers = {}                       // callId → autoScroller 实例
```

### 事件处理

```
store.activeStage 变化 → 创建新 stage section，折叠旧 section
eventBus 'phase'       → 创建新 phase fold
eventBus 'chunk'       → label 创建 fold / 非 label 追加文本到 callBlocks
eventBus 'task_state'  → 折叠已完成/失败的 task fold
eventBus 'tokens'      → (header 自动更新，从 store 读)
eventBus 'error'       → 追加错误文本到当前 target
store reset            → 清空 DOM + 重置内部变量
```

## 执行步骤

### Step 1: 项目搭建

1. 创建 `frontend/package.json`、`vite.config.js`
2. 创建 `frontend/index.html`（Vite 入口，挂载 `#app`）
3. 创建 `frontend/src/main.js`（createApp + Pinia）
4. 迁移 CSS 到 `frontend/src/styles/`（内容不变）
5. 在 `main.js` 中 import 全局样式
6. 删除旧 `frontend/js/`、`frontend/css/`

### Step 2: 核心系统

1. `src/eventBus.js` — 3 个函数的轻量 pub/sub
2. `src/api.js` — 从旧 api.js 复制 fetch 逻辑，去掉 emit 调用
3. `src/stores/pipeline.js` — 完整 store（状态 + actions）
4. `src/composables/useSSE.js` — SSE → store + eventBus 分发
5. `src/composables/useAutoScroll.js` — 从旧 autoscroll.js 适配为 composable

### Step 3: 简单组件

1. `ProgressBar.vue` — 进度条 + Docker 状态指示器
2. `CommandPalette.vue` — Ctrl+K 面板 + 按钮状态机
3. `AppModal.vue` — 文档预览模态框

### Step 4: ProcessViewer + 子组件

1. `DecompTree.vue` — 递归渲染分解树
2. `ExecList.vue` — 批次列表 + 任务状态着色
3. `ProcessViewer.vue` — 组合阶段 section、文档卡片、树、批次列表、分数

### Step 5: LogViewer

1. Vue wrapper（header badges 响应式）
2. `onMounted` 中设置 eventBus 监听
3. Port fold/chunk DOM 操作逻辑（代码几乎原样搬迁）
4. `watch(store.activeStage)` 管理 section 创建
5. 清理函数放在 `onUnmounted`

### Step 6: 集成与部署

1. `App.vue` 组合所有组件
2. 更新 `backend/main.py`：静态文件目录改为 `frontend/dist/`
3. 更新 `start.sh`：添加 `npm install && npm run build` 步骤
4. `.gitignore` 添加 `frontend/dist/` 和 `frontend/node_modules/`
5. `npm run build` 验证产物
6. 端到端测试：启动后端 + 打开浏览器验证 UI

### Step 7: 清理

1. 确认所有功能正常后删除旧文件（git history 可追溯）
2. 更新 README 的 Frontend 部分

## 开发工作流（迁移后）

```bash
# 开发模式（两个终端）
uvicorn backend.main:app --port 8000          # 后端
cd frontend && npm run dev                     # 前端 (Vite dev server, 代理 /api → :8000)

# 生产模式（一键启动）
bash start.sh                                  # 自动 build + 启动
```

## Vite 配置要点

```js
// vite.config.js
export default {
  server: {
    proxy: { '/api': 'http://localhost:8000' }  // 开发时代理 API
  },
  build: {
    outDir: 'dist',       // 构建产物目录
    emptyOutDir: true,
  }
}
```

## 风险与注意事项

1. **LogViewer chunk 性能** — 混合模式已规避。如果仍有问题，可用 `requestAnimationFrame` 批量更新
2. **SSE 重连** — EventSource 自带重连，与现有行为一致
3. **Docker 状态轮询** — 移到 `App.vue` 的 `onMounted` + `setInterval`，与现有行为一致
4. **Ctrl+K 全局快捷键** — 在 `App.vue` 注册 `keydown` 事件，通过 ref 控制 CommandPalette 显隐
5. **样式不变** — 所有 CSS 原样迁移，仅调整 import 路径。视觉效果应完全一致
