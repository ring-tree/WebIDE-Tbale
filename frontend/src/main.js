import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
// import FileTreeNode from './components/FileTreeNode.vue'

// 创建Vue应用实例并挂载到DOM元素上
createApp(App)
  .mount('#app')
  // .component('FileTreeNode', FileTreeNode) // 注册FileTreeNode组件