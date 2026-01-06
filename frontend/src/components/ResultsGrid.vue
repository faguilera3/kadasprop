<script setup lang="ts">
import { ref, computed } from 'vue'
import LotCard from './LotCard.vue'
import InteractiveMap from './InteractiveMap.vue'

interface GlobalInfo {
  streets?: string[]
  block_info?: string
  headers?: string[]
}

interface LotData {
  lot_number?: string
  dimensions?: string[]
  ph_info?: string
  other_text?: string
  image_url?: string
  filename?: string
  loading?: boolean
}

interface ResultsData {
  global_info?: GlobalInfo
  lots_data?: LotData[]
  image_url?: string
  map_screenshot_url?: string
  metadata?: Record<string, string>
}

const props = defineProps<{
  results: ResultsData
}>()

const displayMetadata = computed(() => {
  if (!props.results.metadata) return null
  
  // Filter out internal keys or empty values if needed
  // We want to show everything useful the user saw in the terminal
  const ignored = ['lote'] // 'lote' is normalized duplicate of 'Gráfico' usually
  const entries = Object.entries(props.results.metadata)
    .filter(([key, val]) => val && val.trim() !== '' && !ignored.includes(key))
  
  return entries
})

const getImageUrl = (url?: string) => {
  if (!url) return ''
  // Ensure we don't double prepend or miss the host
  if (url.startsWith('http')) return url
  // If it's a relative path starting with /data, just return it (browser will prepend current host)
  if (url.startsWith('/data')) return url
  // Fallback for any other relative path
  return url.startsWith('/') ? url : `/${url}`
}

// Sort lots by number
const sortedLots = computed(() => {
  if (!props.results.lots_data) return []
  
  return [...props.results.lots_data].sort((a, b) => {
    // Helper to extract first number from string (e.g. "12" from "12¹" or "Lote 12")
    const getNum = (str?: string) => {
      if (!str) return 999999
      const match = str.match(/(\d+)/)
      return match ? parseInt(match[1]) : 999999
    }
    
    const numA = getNum(a.lot_number)
    const numB = getNum(b.lot_number)
    
    // Sort logic: 
    // 1. Known numbers first (ascending)
    // 2. Unknown/Null last
    if (numA === numB) {
        // If numbers are same, try sub-sorting by string (e.g. 1a vs 1b)
        return (a.lot_number || '').localeCompare(b.lot_number || '')
    }
    return numA - numB
  })
})

// Modal state
const isModalOpen = ref(false)
const selectedImage = ref<string | null>(null)

const openModal = (url?: string) => {
  if (!url) return
  selectedImage.value = getImageUrl(url)
  isModalOpen.value = true
}

const closeModal = () => {
  isModalOpen.value = false
  selectedImage.value = null
}

const mapCoords = computed(() => {
  if (props.results.metadata && props.results.metadata['Latitud'] && props.results.metadata['Longitud']) {
    const lat = parseFloat(props.results.metadata['Latitud'])
    const lng = parseFloat(props.results.metadata['Longitud'])
    if (!isNaN(lat) && !isNaN(lng)) {
      return { lat, lng }
    }
  }
  return null
})
</script>

<template>
  <div class="w-full max-w-7xl mx-auto px-4 pb-20 animate-fade-in">
    
    <!-- Header / Global Info -->
    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-8">
      <div class="flex flex-col gap-8">
        
        <!-- Info (Top) -->
        <div class="flex-1 space-y-4">
          <div>
            <h2 class="text-2xl font-bold text-gray-900 mb-2">Información de Manzana</h2>
            
            <!-- Official Metadata Grid -->
            <div v-if="displayMetadata" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 my-4 animate-fade-in">
              <div v-for="[key, value] in displayMetadata" :key="key" class="bg-gray-50 p-3 rounded-lg border border-gray-100 hover:border-[#e8e2fb] transition-colors group">
                <span class="block text-[10px] text-gray-400 uppercase tracking-wider font-bold mb-1 group-hover:text-[#753ddb] transition-colors">{{ key }}</span>
                <span class="block text-sm font-semibold text-gray-800 font-mono break-words leading-tight">{{ value }}</span>
              </div>
            </div>

            <div v-if="!results.global_info && !results.image_url && !results.metadata" class="animate-pulse h-6 bg-gray-100 rounded w-1/3 mt-1"></div>
            
            <!-- Block Info removed as per request (redundant) -->
          </div>
          
          <div v-if="results.global_info?.streets?.length" class="space-y-2">
            <h3 class="text-sm font-semibold text-gray-400 uppercase tracking-wider">Calles Circundantes</h3>
            <div class="flex flex-wrap gap-2">
              <span 
                v-for="street in results.global_info.streets" 
                :key="street"
                class="px-3 py-1 bg-[#f2f0fd] text-[#561eb0] rounded-full text-sm font-medium border border-[#e8e2fb]"
              >
                {{ street }}
              </span>
            </div>
          </div>
          
          <div v-if="results.global_info?.headers?.length" class="space-y-2 mt-4">
             <h3 class="text-sm font-semibold text-gray-400 uppercase tracking-wider">Detalles de Ubicación</h3>
             <div class="flex flex-wrap gap-2">
               <span 
                 v-for="(header, index) in results.global_info.headers.filter(h => !h.includes('Sección') && !h.includes('Manzana'))" 
                 :key="index"
                 class="px-3 py-1.5 bg-white border border-gray-200 text-gray-700 rounded-lg text-xs font-medium shadow-sm hover:border-[#e8e2fb] transition-colors"
               >
                 {{ header }}
               </span>
             </div>
          </div>
        </div>

        <!-- Main Content Grid (Full Width Map with Floating PDF Button) -->
        <div class="relative w-full mt-8">
          
          <!-- Interactive Map -->
          <div class="flex flex-col h-full">
             <div class="flex items-center justify-between mb-4">
               <h3 class="text-xl font-bold text-gray-900 flex items-center gap-2">
                 <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                   <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                 </svg>
                 Mapa Interactivo
               </h3>
               <span class="text-xs text-gray-400 bg-gray-50 px-2 py-1 rounded border border-gray-100">WMS Oficial</span>
             </div>
             
             <div v-if="mapCoords" class="w-full h-[600px] animate-fade-in relative z-0">
                <InteractiveMap :lat="mapCoords.lat" :lng="mapCoords.lng" class="h-full w-full rounded-xl shadow-sm border border-gray-200" />
                
                <!-- Floating PDF Button (Inside Map Container) -->
                <div v-if="results.image_url" class="absolute bottom-6 right-6 z-[1002]">
                  <button 
                    @click="openModal(results.image_url)"
                    class="group flex items-center gap-3 bg-white p-2 rounded-xl shadow-lg border border-gray-200 hover:shadow-xl hover:border-[#753ddb] transition-all duration-300"
                  >
                    <div class="w-16 h-16 rounded-lg overflow-hidden border border-gray-100 relative bg-gray-50">
                      <img 
                        :src="getImageUrl(results.image_url)" 
                        alt="Miniatura Plano" 
                        class="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity"
                      />
                    </div>
                    <div class="pr-3 text-left">
                      <span class="block text-xs font-bold text-gray-500 uppercase tracking-wider group-hover:text-[#753ddb]">Plano Oficial</span>
                      <span class="text-sm font-semibold text-gray-800">Ver PDF Digitalizado</span>
                    </div>
                  </button>
                </div>
             </div>
             
             <div v-else class="w-full h-[400px] bg-gray-50 rounded-xl border border-gray-200 flex items-center justify-center text-gray-400">
                <span>Cargando mapa interactivo...</span>
             </div>
          </div>

        </div>
      </div>
    </div>

    <!-- Lots Grid -->
    <div class="mb-6 flex items-center justify-between">
      <h3 class="text-xl font-bold text-gray-800">Lotes Detectados ({{ sortedLots.length || 0 }})</h3>
    </div>

    <div v-if="sortedLots && sortedLots.length > 0" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
      <LotCard 
        v-for="(lot, index) in sortedLots" 
        :key="lot.filename || index" 
        :lot="lot"
        class="animate-slide-up"
        :style="{ animationDelay: `${index * 50}ms` }"
        @click-image="openModal"
      />
    </div>
    <div v-else class="text-center py-20 text-gray-400">
      <div v-if="results.map_screenshot_url && !results.image_url" class="flex flex-col items-center gap-3">
         <div class="animate-spin h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full"></div>
         <span>Procesando lotes...</span>
      </div>
      <span v-else>No se encontraron lotes individuales.</span>
    </div>

    <!-- Image Modal -->
    <Teleport to="body">
      <div 
        v-if="isModalOpen" 
        class="fixed inset-0 z-[9999] flex items-center justify-center bg-black/90 backdrop-blur-md p-4 animate-fade-in"
        @click="closeModal"
      >
        <!-- Close Button (Fixed to viewport) -->
        <button 
          @click="closeModal"
          class="absolute top-4 right-4 text-white/70 hover:text-white transition-colors z-[10000] p-2 bg-black/20 rounded-full hover:bg-black/40"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <!-- Image Container -->
        <img 
          v-if="selectedImage"
          :src="selectedImage" 
          alt="Plano Oficial" 
          class="block object-contain rounded-lg shadow-2xl bg-white max-w-[90vw] max-h-[90vh]"
          @click.stop
        />
      </div>
    </Teleport>

  </div>
</template>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}

.animate-slide-up {
  animation: slideUp 0.5s ease-out forwards;
  opacity: 0;
  transform: translateY(20px);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
