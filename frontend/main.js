import App from './App'

// #ifndef VUE3
import Vue from 'vue'

// 关闭生产提示，避免控制台出现不必要的 Vue 提示信息。
Vue.config.productionTip = false
// 声明当前入口是小程序/uni-app 应用实例。
App.mpType = 'app'

// 创建应用实例，挂载根组件。
const app = new Vue({
  ...App
})

app.$mount()
// #endif
