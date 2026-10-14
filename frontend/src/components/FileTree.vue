<template>
  <div class="file-tree">
    <div class="file-tree-header">
      <span class="file-tree-title">{{ projectPath }}</span>
      <div class="header-actions">
        <button class="action-btn" @click="showCreateDialog('file')" title="新建文件">📄</button>
        <button class="action-btn" @click="showCreateDialog('directory')" title="新建文件夹">📁</button>
        <button class="action-btn" @click="collapseAll" title="折叠全部">⬇</button>
        <button class="refresh-btn" @click="fetchFileTree" title="刷新">↻</button>
      </div>
    </div>
    <div class="file-tree-content">
      <template v-for="child in fileTree.children" :key="child.path">
        <TreeNode
          :node="child"
          :depth="0"
          :expanded-folders="expandedFolders"
          :selected-file="selectedFile"
          @toggle="toggleFolder"
          @select="selectFile"
          @context-menu="showContextMenu"
        />
      </template>
    </div>

    <Teleport to="body">
      <div
        v-show="contextMenu.show"
        class="context-menu"
        :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
      >
        <template v-if="!contextMenu.isReadonly">
          <div class="menu-item" @click="showCreateDialog('file')">新建文件</div>
          <div class="menu-item" @click="showCreateDialog('directory')">新建文件夹</div>
          <div class="menu-divider"></div>
          <div class="menu-item" @click="renameNode">重命名</div>
          <div class="menu-item danger" @click="deleteNode">删除</div>
        </template>
        <template v-else>
          <div class="menu-item readonly">只读目录</div>
        </template>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue';
import TreeNode from './TreeNode.vue';

const props = defineProps({
  projectPath: {
    type: String,
    default: 'project'
  }
});

const emit = defineEmits(['file-selected', 'refresh']);

const READONLY_PREFIXES = ['project/toolBox'];

const fileTree = reactive({
  name: 'project',
  type: 'directory',
  path: 'project',
  children: []
});

const expandedFolders = reactive(new Set());
const selectedFile = ref(null);
const contextMenu = reactive({
  show: false,
  x: 0,
  y: 0,
  target: null,
  targetType: null,
  isReadonly: false
});

const isReadonlyPath = (path) => {
  const normalizedPath = path.replace(/\\/g, '/');
  return READONLY_PREFIXES.some(prefix =>
    normalizedPath === prefix || normalizedPath.startsWith(prefix + '/')
  );
};

const fetchFileTree = async () => {
  try {
    const response = await fetch(`/api/files?path=${props.projectPath}`);
    if (!response.ok) throw new Error('获取文件树失败');
    const data = await response.json();
    Object.assign(fileTree, data);
  } catch (error) {
    console.error('获取文件树失败:', error);
  }
};

const toggleFolder = (path) => {
  if (expandedFolders.has(path)) {
    expandedFolders.delete(path);
  } else {
    expandedFolders.add(path);
  }
};

const collapseAll = () => {
  expandedFolders.clear();
};

const selectFile = (file) => {
  selectedFile.value = file.path;
  emit('file-selected', file);
};

const showContextMenu = (event, node) => {
  event.preventDefault();
  event.stopPropagation();
  contextMenu.show = true;
  contextMenu.x = event.clientX;
  contextMenu.y = event.clientY;
  contextMenu.target = node;
  contextMenu.targetType = node.type;
  contextMenu.isReadonly = isReadonlyPath(node.path);
};

const hideContextMenu = () => {
  contextMenu.show = false;
};

const showCreateDialog = (type) => {
  hideContextMenu();
  if (contextMenu.isReadonly) {
    alert('此目录是只读目录，无法执行操作');
    return;
  }
  const name = prompt(`请输入${type === 'file' ? '文件名' : '文件夹名'}:`);
  if (!name) return;

  const targetPath = contextMenu.target && contextMenu.target.type === 'directory'
    ? `${contextMenu.target.path}/${name}`
    : `${props.projectPath}/${name}`;

  createNode(targetPath, type);
};

const createNode = async (filePath, type) => {
  try {
    const response = await fetch('/api/files/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        path: filePath,
        type: type
      })
    });
    const data = await response.json();
    if (!response.ok || data.status === 'error') {
      throw new Error(data.message || `创建${type === 'directory' ? '文件夹' : '文件'}失败`);
    }
    await fetchFileTree();
    emit('refresh');
  } catch (error) {
    console.error('创建失败:', error);
    alert('创建失败: ' + error.message);
  }
};

const deleteNode = async () => {
  hideContextMenu();
  if (!contextMenu.target) return;
  if (contextMenu.isReadonly) {
    alert('此目录是只读目录，无法执行操作');
    return;
  }

  const confirmed = confirm(`确定要删除 ${contextMenu.target.name} 吗?${contextMenu.targetType === 'directory' ? '（文件夹内的所有内容也将被删除）' : ''}`);
  if (!confirmed) return;

  try {
    const response = await fetch('/api/files/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        path: contextMenu.target.path
      })
    });
    const data = await response.json();
    if (!response.ok || data.status === 'error') {
      throw new Error(data.message || '删除失败');
    }
    await fetchFileTree();
    emit('refresh');
  } catch (error) {
    console.error('删除失败:', error);
    alert('删除失败: ' + error.message);
  }
};

const renameNode = async () => {
  hideContextMenu();
  if (!contextMenu.target) return;
  if (contextMenu.isReadonly) {
    alert('此目录是只读目录，无法执行操作');
    return;
  }

  const newName = prompt('请输入新名称:', contextMenu.target.name);
  if (!newName || newName === contextMenu.target.name) return;

  try {
    const response = await fetch('/api/files/rename', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        path: contextMenu.target.path,
        newName: newName
      })
    });
    const data = await response.json();
    if (!response.ok || data.status === 'error') {
      throw new Error(data.message || '重命名失败');
    }
    await fetchFileTree();
    emit('refresh');
  } catch (error) {
    console.error('重命名失败:', error);
    alert('重命名失败: ' + error.message);
  }
};

watch(() => props.projectPath, () => {
  fetchFileTree();
}, { immediate: true });

document.addEventListener('click', hideContextMenu);

defineExpose({
  fetchFileTree
});
</script>

<style scoped>
.file-tree {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #1e1e1e;
  color: #cccccc;
  font-size: 13px;
  overflow: hidden;
}

.file-tree-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  background-color: #252526;
  border-bottom: 1px solid #3c3c3c;
}

.file-tree-title {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #ababab;
}

.header-actions {
  display: flex;
  gap: 4px;
}

.action-btn,
.refresh-btn {
  background: none;
  border: none;
  color: #cccccc;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
}

.action-btn:hover,
.refresh-btn:hover {
  background-color: #3c3c3c;
}

.action-btn.danger:hover {
  background-color: #f48771;
  color: #1e1e1e;
}

.file-tree-content {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.file-tree-content::-webkit-scrollbar {
  width: 8px;
}

.file-tree-content::-webkit-scrollbar-track {
  background: #1e1e1e;
}

.file-tree-content::-webkit-scrollbar-thumb {
  background: #424242;
  border-radius: 4px;
}

.file-tree-content::-webkit-scrollbar-thumb:hover {
  background: #4f4f4f;
}

.node-row {
  display: flex;
  align-items: center;
  padding: 3px 8px;
  cursor: pointer;
  white-space: nowrap;
}

.node-row:hover {
  background-color: #2a2d2e;
}

.node-row.selected {
  background-color: #094771;
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

.context-menu {
  position: fixed;
  background-color: #3c3c3c;
  border: 1px solid #4c4c4c;
  border-radius: 4px;
  padding: 4px 0;
  min-width: 160px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  z-index: 99999;
}

.menu-item {
  padding: 6px 20px;
  cursor: pointer;
  font-size: 13px;
}

.menu-item:hover {
  background-color: #094771;
}

.menu-item.danger {
  color: #f48771;
}

.menu-item.danger:hover {
  background-color: #f48771;
  color: #1e1e1e;
}

.menu-item.readonly {
  color: #888;
  cursor: default;
}

.menu-item.readonly:hover {
  background-color: transparent;
}

.menu-divider {
  height: 1px;
  background-color: #4c4c4c;
  margin: 4px 0;
}
</style>
