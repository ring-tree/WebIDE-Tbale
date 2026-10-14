<script setup>
const props = defineProps({
  node: {
    type: Object,
    required: true
  },
  depth: {
    type: Number,
    default: 0
  },
  expandedFolders: {
    type: Object,
    required: true
  },
  selectedFile: {
    type: String,
    default: null
  }
});

const emit = defineEmits(['toggle', 'select', 'context-menu']);

const getFileIcon = (name) => {
  const ext = name.split('.').pop().toLowerCase();
  const iconMap = {
    'js': '📜',
    'ts': '📘',
    'vue': '💚',
    'py': '🐍',
    'json': '📋',
    'css': '🎨',
    'html': '🌐',
    'md': '📝',
    'txt': '📄',
    'png': '🖼️',
    'jpg': '🖼️',
    'gif': '🖼️',
    'svg': '🖼️'
  };
  return iconMap[ext] || '📄';
};

const handleClick = () => {
  if (props.node.type === 'directory') {
    emit('toggle', props.node.path);
  } else {
    emit('select', props.node);
  }
};

const handleContextMenu = (event) => {
  emit('context-menu', event, props.node);
};
</script>

<template>
  <div class="tree-node">
    <div
      class="node-row"
      :class="[node.type, { selected: node.type === 'file' && selectedFile === node.path }]"
      :style="{ paddingLeft: (8 + depth * 12) + 'px' }"
      @click="handleClick"
      @contextmenu="handleContextMenu"
    >
      <span class="folder-arrow" v-if="node.type === 'directory'">
        {{ expandedFolders.has(node.path) ? 'v' : '>' }}
      </span>
      <span class="folder-icon" v-if="node.type === 'directory'">📁</span>
      <span class="file-icon" v-else>{{ getFileIcon(node.name) }}</span>
      <span class="node-name">{{ node.name }}</span>
    </div>

    <template v-if="node.type === 'directory' && expandedFolders.has(node.path) && node.children">
      <TreeNode
        v-for="child in node.children"
        :key="child.path"
        :node="child"
        :depth="depth + 1"
        :expanded-folders="expandedFolders"
        :selected-file="selectedFile"
        @toggle="emit('toggle', $event)"
        @select="emit('select', $event)"
        @context-menu="(e, n) => emit('context-menu', e, n)"
      />
    </template>
  </div>
</template>

<style scoped>
.tree-node {
  width: 100%;
}

.node-row {
  display: flex;
  align-items: center;
  padding: 3px 8px;
  cursor: pointer;
  white-space: nowrap;
  border-left: 2px solid transparent;
}

.node-row:hover {
  background-color: #2a2d2e;
}

.node-row.selected {
  background-color: #094771;
  border-left-color: #007acc;
}

.node-row.selected .node-name {
  color: #ffffff;
  font-weight: 500;
}

.folder-arrow {
  width: 14px;
  font-size: 10px;
  color: #cccccc;
  flex-shrink: 0;
}

.folder-icon,
.file-icon {
  margin-right: 4px;
  font-size: 14px;
  flex-shrink: 0;
}

.node-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
