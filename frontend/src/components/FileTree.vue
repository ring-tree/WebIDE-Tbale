<script setup>
import { ref, reactive, watch } from 'vue';

const props = defineProps({
  projectPath: {
    type: String,
    default: 'project'
  }
});

const emit = defineEmits(['file-selected', 'refresh']);

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
  targetType: null
});

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
};

const hideContextMenu = () => {
  contextMenu.show = false;
};

const showCreateDialog = (type) => {
  hideContextMenu();
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
    if (!response.ok) throw new Error(`创建${type === 'directory' ? '文件夹' : '文件'}失败`);
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
    if (!response.ok) throw new Error('删除失败');
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
    if (!response.ok) throw new Error('重命名失败');
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

const renderTreeNode = (node, depth = 0) => {
  const isFolder = node.type === 'directory';
  const isExpanded = expandedFolders.has(node.path);
  const paddingLeft = 8 + depth * 12;

  return { isFolder, isExpanded, paddingLeft };
};

defineExpose({
  fetchFileTree
});
</script>

<template>
  <div class="file-tree">
    <div class="file-tree-header">
      <span class="file-tree-title">Explorer</span>
      <div class="header-actions">
        <button class="action-btn" @click="showCreateDialog('file')" title="新建文件">+</button>
        <button class="action-btn" @click="showCreateDialog('directory')" title="新建文件夹">+📁</button>
        <button class="action-btn danger" @click="deleteNode" v-if="contextMenu.target" title="删除">-</button>
        <button class="refresh-btn" @click="fetchFileTree" title="刷新">↻</button>
      </div>
    </div>
    <div class="file-tree-content">
      <template v-for="child in fileTree.children" :key="child.path">
        <div
          v-if="child.type === 'directory'"
          class="node-row directory"
          :style="{ paddingLeft: '8px' }"
          @click="toggleFolder(child.path)"
          @contextmenu="showContextMenu($event, child)"
        >
          <span class="folder-arrow">{{ expandedFolders.has(child.path) ? 'v' : '>' }}</span>
          <span class="folder-icon">📁</span>
          <span class="node-name">{{ child.name }}</span>
        </div>
        <template v-if="child.type === 'directory' && expandedFolders.has(child.path)">
          <template v-for="grandchild in child.children" :key="grandchild.path">
            <div
              v-if="grandchild.type === 'directory'"
              class="node-row directory"
              :style="{ paddingLeft: '20px' }"
              @click="toggleFolder(grandchild.path)"
              @contextmenu="showContextMenu($event, grandchild)"
            >
              <span class="folder-arrow">{{ expandedFolders.has(grandchild.path) ? 'v' : '>' }}</span>
              <span class="folder-icon">📁</span>
              <span class="node-name">{{ grandchild.name }}</span>
            </div>
            <template v-if="grandchild.type === 'directory' && expandedFolders.has(grandchild.path)">
              <div
                v-for="g2 in grandchild.children"
                :key="g2.path"
                class="node-row"
                :class="g2.type"
                :style="{ paddingLeft: '32px' }"
                @click="g2.type === 'directory' ? toggleFolder(g2.path) : selectFile(g2)"
                @contextmenu="showContextMenu($event, g2)"
              >
                <span class="folder-arrow" v-if="g2.type === 'directory'">{{ expandedFolders.has(g2.path) ? 'v' : '>' }}</span>
                <span class="file-icon" v-else>{{ getFileIcon(g2.name) }}</span>
                <span class="node-name">{{ g2.name }}</span>
              </div>
            </template>
            <div
              v-else-if="grandchild.type === 'file'"
              class="node-row file"
              :style="{ paddingLeft: '20px' }"
              :class="{ selected: selectedFile === grandchild.path }"
              @click="selectFile(grandchild)"
              @contextmenu="showContextMenu($event, grandchild)"
            >
              <span class="file-icon">{{ getFileIcon(grandchild.name) }}</span>
              <span class="node-name">{{ grandchild.name }}</span>
            </div>
          </template>
        </template>
        <div
          v-else-if="child.type === 'file'"
          class="node-row file"
          :style="{ paddingLeft: '8px' }"
          :class="{ selected: selectedFile === child.path }"
          @click="selectFile(child)"
          @contextmenu="showContextMenu($event, child)"
        >
          <span class="file-icon">{{ getFileIcon(child.name) }}</span>
          <span class="node-name">{{ child.name }}</span>
        </div>
      </template>
    </div>

    <div
      v-show="contextMenu.show"
      class="context-menu"
      :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
    >
      <div class="menu-item" @click="showCreateDialog('file')">新建文件</div>
      <div class="menu-item" @click="showCreateDialog('directory')">新建文件夹</div>
      <div class="menu-divider"></div>
      <div class="menu-item" @click="renameNode">重命名</div>
      <div class="menu-item danger" @click="deleteNode">删除</div>
    </div>
  </div>
</template>

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
  z-index: 1000;
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

.menu-divider {
  height: 1px;
  background-color: #4c4c4c;
  margin: 4px 0;
}
</style>
