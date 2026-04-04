<template>
  <div class="tree-node">
    <div 
      class="node-item" 
      :class="{ folder: node.isFolder, file: !node.isFolder }"
      @click="onItemClick"
    >
      <span class="node-icon">
        {{ node.isFolder ? (node.expanded ? '📂' : '📁') : '📄' }}
      </span>
      <span class="node-name">{{ node.name }}</span>
    </div>
    
    <div v-if="node.isFolder && node.expanded && node.children" class="children">
      <FileTreeNode 
        v-for="child in node.children" 
        :key="child.name" 
        :node="child" 
        @node-click="$emit('node-click', $event)"
      />
    </div>
  </div>
</template>

<script>
export default {
  name: 'FileTreeNode',
  props: {
    node: {
      type: Object,
      required: true
    }
  },
  emits: ['node-click'],
  methods: {
    onItemClick() {
      this.$emit('node-click', this.node)
    }
  }
}
</script>

<style scoped>
.tree-node {
  user-select: none;
}

.node-item {
  display: flex;
  align-items: center;
  padding: 0.2rem 0.5rem;
  cursor: pointer;
  border-radius: 3px;
}

.node-item:hover {
  background-color: #2a2d2e;
}

.node-icon {
  margin-right: 0.5rem;
  width: 16px;
}

.node-name {
  font-size: 0.9rem;
}

.children {
  padding-left: 1rem;
}
</style>