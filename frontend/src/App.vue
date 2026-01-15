<script setup lang="ts">
import { ref } from 'vue'
import SearchBox from './components/SearchBox.vue'
import ResultsGrid from './components/ResultsGrid.vue'

const results = ref<any>(null)
const loading = ref(false)
const loadingMessage = ref('Iniciando...')
const progress = ref(0) // 0-100
const error = ref<string | null>(null)
const hasSearched = ref(false)

// History Logic
const isHistoryOpen = ref(false)
const historyItems = ref<any[]>([])

const fetchHistory = async () => {
  try {
    const res = await fetch('/history')
    if (res.ok) {
      historyItems.value = await res.json()
    }
  } catch (e) {
    console.error("Failed to fetch history", e)
  }
}

const toggleHistory = () => {
  isHistoryOpen.value = !isHistoryOpen.value
  if (isHistoryOpen.value) {
    fetchHistory()
  }
}

const loadHistoryItem = async (filename: string) => {
  loading.value = true
  loadingMessage.value = 'Cargando búsqueda guardada...'
  isHistoryOpen.value = false
  hasSearched.value = true
  error.value = null
  results.value = null

  try {
    const res = await fetch(`/history/${filename}`)
    if (res.ok) {
      const data = await res.json()
      results.value = {
        global_info: data.global_info,
        lots_data: data.lots_data,
        image_url: data.image_url,
        map_screenshot_url: data.map_screenshot_url,
        metadata: data.metadata
      }
    } else {
      error.value = "No se pudo cargar la búsqueda."
    }
  } catch (e) {
    error.value = "Error al cargar la búsqueda."
    console.error(e)
  } finally {
    loading.value = false
  }
}

const deleteHistoryItem = async (filename: string) => {
  if (!confirm('¿Estás seguro de eliminar esta búsqueda?')) return
  
  try {
    const res = await fetch(`/history/${filename}`, { method: 'DELETE' })
    if (res.ok) {
      await fetchHistory()
    }
  } catch (e) {
    console.error("Failed to delete item", e)
  }
}

const handleSearch = (payload: any) => {
  isHistoryOpen.value = false
  loading.value = true
  loadingMessage.value = 'Conectando con el servidor...'
  progress.value = 0
  error.value = null
  results.value = {
    global_info: null,
    lots_data: [],
    image_url: null,
    map_screenshot_url: null,
    metadata: null
  }
  hasSearched.value = true
  
  // payload can be string or object
  const address = typeof payload === 'string' ? payload : payload.address
  const coordinates = (typeof payload === 'object' && payload.coordinates) ? payload.coordinates : null

  // Determine WebSocket protocol (ws or wss)
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host // Includes port if present
  
  const wsUrl = `${protocol}//${host}/ws/scrape`
  const ws = new WebSocket(wsUrl)
  
  let totalLots = 0
  let processedLots = 0

  ws.onopen = () => {
    // Send object with address and optional coordinates
    ws.send(JSON.stringify({ address, coordinates }))
    progress.value = 5 // Connection established
  }
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    
    if (data.status === 'started') {
        progress.value = 10
        loadingMessage.value = data.message
    }
    else if (data.status === 'progress') {
      loadingMessage.value = data.message
    }
    else if (data.status === 'map_ready') {
      progress.value = 30
      results.value.map_screenshot_url = data.screenshot_url
      results.value.metadata = data.metadata
      // We can start showing results container now if we want, or wait for lots
    }
    else if (data.status === 'full_map_ready') {
      results.value.image_url = data.image_url
      progress.value = Math.max(progress.value, 40)
    }
    else if (data.status === 'lots_found') {
      // Initialize lots with images but no text
      totalLots = data.lots.length
      processedLots = 0
      
      results.value.lots_data = data.lots.map((l: any) => ({
        filename: l.filename,
        image_url: l.image_url,
        loading: true // Add loading state per lot
      }))
      // Hide main loading spinner, show grid
      loading.value = false
      progress.value = Math.max(progress.value, 45)
    }
    else if (data.status === 'lot_update') {
      processedLots++
      // Calculate progress from 45% to 95% based on lots
      if (totalLots > 0) {
          const lotProgress = (processedLots / totalLots) * 50
          progress.value = Math.min(45 + lotProgress, 95)
      }
      
      // Find the lot and update it
      const lotIndex = results.value.lots_data.findIndex((l: any) => l.filename === data.data.filename)
      if (lotIndex !== -1) {
        results.value.lots_data[lotIndex] = {
          ...results.value.lots_data[lotIndex],
          ...data.data,
          loading: false
        }
      }
    }
    else if (data.status === 'global_info') {
      results.value.global_info = data.data
      progress.value = 98
    }
    else if (data.status === 'complete') {
      progress.value = 100
      setTimeout(() => {
          ws.close()
      }, 500)
    }
    else if (data.status === 'error') {
      error.value = data.message
      loading.value = false
      ws.close()
    }
  }
  
  ws.onerror = (e) => {
    console.error(e)
    error.value = "Error de conexión WebSocket"
    loading.value = false
  }
  
  ws.onclose = () => {
    if (loading.value) {
      // If closed while loading without error
      // loading.value = false
    }
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 text-gray-800 font-sans selection:bg-primary-100 selection:text-primary-900 flex flex-col relative overflow-x-hidden">
    
    <!-- History Toggle Button -->
    <button 
      @click="toggleHistory"
      class="fixed top-4 right-4 z-40 p-3 bg-white text-primary-500 rounded-full shadow-lg hover:shadow-xl hover:scale-105 transition-all duration-300 border border-gray-100"
      title="Historial de Búsquedas"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    </button>

    <!-- History Sidebar -->
    <div 
      class="fixed inset-y-0 right-0 w-80 bg-white shadow-2xl z-50 transform transition-transform duration-300 ease-in-out flex flex-col"
      :class="isHistoryOpen ? 'translate-x-0' : 'translate-x-full'"
    >
      <div class="p-4 border-b border-gray-100 flex items-center justify-between bg-[#f9fafb]">
        <h2 class="font-bold text-gray-800 flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-primary-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Historial
        </h2>
        <button @click="isHistoryOpen = false" class="text-gray-400 hover:text-gray-600">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      
      <div class="flex-1 overflow-y-auto p-4 space-y-3">
        <div v-if="historyItems.length === 0" class="text-center py-10 text-gray-400 text-sm">
          No hay búsquedas guardadas.
        </div>
        
        <div 
          v-for="item in historyItems" 
          :key="item.filename"
          class="bg-white border border-gray-100 rounded-xl p-3 shadow-sm hover:shadow-md hover:border-primary-100 transition-all group"
        >
          <div class="flex justify-between items-start mb-2">
            <button 
              @click="loadHistoryItem(item.filename)"
              class="text-left flex-1"
            >
              <h3 class="font-semibold text-gray-800 text-sm group-hover:text-primary-500 transition-colors leading-tight mb-1">
                {{ item.address }}
              </h3>
              <span class="text-xs text-gray-400 block">{{ item.date }}</span>
            </button>
            <button 
              @click="deleteHistoryItem(item.filename)"
              class="text-gray-300 hover:text-red-500 p-1 rounded-full hover:bg-red-50 transition-colors"
              title="Eliminar"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Backdrop -->
    <div 
      v-if="isHistoryOpen" 
      class="fixed inset-0 bg-black/20 backdrop-blur-sm z-40"
      @click="isHistoryOpen = false"
    ></div>

    <!-- Hero Section / Search Container -->
    <div 
      class="flex-1 flex flex-col items-center transition-all duration-1000 ease-[cubic-bezier(0.4,0,0.2,1)] pb-32"
      :class="(hasSearched && !loading) ? 'justify-start pt-12 flex-none h-auto pb-8' : 'justify-center h-screen'"
    >
      <!-- Progress Bar (Only when active searching) -->
      <div 
        v-if="hasSearched && progress < 100 && !error && progress > 0" 
        class="fixed top-0 left-0 w-full h-2 bg-gray-200 z-[9999]"
      >
        <div 
          class="h-full bg-gradient-to-r from-primary-500 via-primary-400 to-primary-200 transition-all duration-300 ease-out shadow-[0_0_15px_rgba(34,197,94,0.6)]"
          :style="{ width: `${progress}%` }"
        ></div>
      </div>

      <div class="w-full max-w-7xl px-4 text-center">
        <div 
          class="flex justify-center transition-all duration-700 ease-in-out" 
          :class="(hasSearched && !loading) ? 'mb-4 scale-75' : 'mb-8 scale-100'"
        >
          <img src="/logo.png" alt="Logo" class="h-16 md:h-40 object-contain" />
        </div>
        
        <SearchBox @search="handleSearch" :isGlobalLoading="loading" />
        
        <!-- Discreet Status Text -->
        <div v-if="loading" class="mt-3 text-center animate-fade-in">
          <p class="text-sm font-medium text-primary-500 animate-pulse">{{ loadingMessage }}</p>
        </div>
      </div>
    </div>

    <!-- Content (Only visible after search) -->
    <main 
      v-if="hasSearched && !loading" 
      class="flex-1 py-12 animate-fade-in bg-gray-100 w-full rounded-t-[2.5rem] shadow-[inset_0_2px_15px_rgba(0,0,0,0.05)] border-t border-gray-200 mt-4"
    >
      
      <!-- Error State -->
      <div v-if="error" class="max-w-2xl mx-auto px-4 py-8">
        <div class="bg-red-50 border-l-4 border-red-500 p-4 rounded-r-lg flex items-start space-x-3">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-red-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <h3 class="text-red-800 font-bold">Error</h3>
            <p class="text-red-700 mt-1">{{ error }}</p>
          </div>
        </div>
      </div>

      <!-- Results -->
      <ResultsGrid v-if="(results && (results.lots_data.length > 0 || results.map_screenshot_url))" :results="results" />

    </main>
    
    <!-- Footer (Only visible after search) -->
    <footer v-if="hasSearched && !loading" class="bg-white border-t border-gray-200 py-8 mt-auto animate-fade-in">
      <div class="max-w-7xl mx-auto px-4 text-center text-gray-400 text-sm">
        &copy; {{ new Date().getFullYear() }} 
      </div>
    </footer>

  </div>
</template>

<style>
.animate-fade-in {
  animation: fadeIn 0.5s ease-out forwards;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
