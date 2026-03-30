import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

import './styles/variables.css'
import './styles/layout.css'
import './styles/workspace.css'
import './styles/cards.css'
import './styles/tree.css'

const app = createApp(App)
app.use(createPinia())
app.mount('#app')
