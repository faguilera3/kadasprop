<script setup lang="ts">
interface LotData {
  lot_number?: string
  dimensions?: string[]
  ph_info?: string
  other_text?: string
  image_url?: string
  filename?: string
  loading?: boolean
}

defineProps<{
  lot: LotData
}>()

defineEmits(['click-image'])

// Helper to format image URL
const getImageUrl = (url?: string) => {
  if (!url) return ''
  // Ensure we don't double prepend or miss the host
  if (url.startsWith('http')) return url
  // If it's a relative path starting with /data, just return it (browser will prepend current host)
  if (url.startsWith('/data')) return url
  // Fallback for any other relative path
  return url.startsWith('/') ? url : `/${url}`
}
</script>

<template>
  <div class="bg-white rounded-xl shadow-[0_2px_10px_-2px_rgba(0,0,0,0.05)] hover:shadow-[0_8px_25px_-5px_rgba(0,0,0,0.1)] transition-all duration-300 border border-gray-100 flex flex-col h-full transform hover:-translate-y-1">
    <div class="h-48 bg-gray-50 overflow-hidden relative group rounded-t-xl">
      <div class="absolute inset-0 bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] [background-size:16px_16px] opacity-50"></div>
      <img 
        v-if="lot.image_url"
        :src="getImageUrl(lot.image_url)" 
        alt="Lote" 
        class="relative w-full h-full object-contain p-4 transition-transform duration-500 group-hover:scale-110 cursor-pointer z-10"
        @click="$emit('click-image', lot.image_url)"
      />
      <div v-else class="relative w-full h-full flex items-center justify-center text-gray-400 z-10">
        <div class="flex flex-col items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <span class="text-xs">Sin imagen</span>
        </div>
      </div>
      
      <div class="absolute top-2 right-2 bg-white/90 backdrop-blur-sm text-[#6428ca] text-xs font-bold px-2.5 py-1 rounded-full shadow-sm pointer-events-none z-20 border border-[#e8e2fb]">
        {{ lot.lot_number || 'S/N' }}
      </div>
      
      <!-- Zoom Icon Overlay -->
      <div 
        v-if="lot.image_url"
        class="absolute inset-0 bg-[#3c1678]/0 group-hover:bg-[#3c1678]/5 transition-colors duration-300 flex items-center justify-center pointer-events-none z-20"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 text-[#6428ca] opacity-0 group-hover:opacity-100 transition-all duration-300 transform scale-75 group-hover:scale-100 drop-shadow-md bg-white rounded-full p-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>
    </div>
    
    <div class="p-5 flex-1 flex flex-col">
      <!-- Loading Skeleton -->
      <div v-if="lot.loading" class="animate-pulse space-y-3">
        <div class="h-6 bg-gray-200 rounded w-1/3"></div>
        <div class="space-y-2 pt-2">
          <div class="h-4 bg-gray-100 rounded w-full"></div>
          <div class="h-4 bg-gray-100 rounded w-2/3"></div>
        </div>
      </div>
      
      <div v-else>
        <div class="flex items-start justify-between mb-3">
          <h3 class="text-lg font-bold text-gray-800">Lote {{ lot.lot_number || '?' }}</h3>
          <div v-if="lot.ph_info" class="text-xs font-medium bg-green-50 text-green-700 px-2 py-0.5 rounded-full border border-green-100">
            {{ lot.ph_info }}
          </div>
        </div>
        
        <div class="space-y-3 text-sm text-gray-600 flex-1">
          <div v-if="lot.dimensions && lot.dimensions.length > 0">
            <span class="text-xs uppercase tracking-wide text-gray-400 font-semibold block mb-1.5">Medidas</span>
            <div class="flex flex-wrap gap-1.5">
              <span 
                v-for="(dim, idx) in lot.dimensions" 
                :key="idx"
                class="bg-gray-50 px-2.5 py-1 rounded-md text-xs font-medium text-gray-600 border border-gray-100"
              >
                {{ dim }}
              </span>
            </div>
          </div>
          
          <div v-if="lot.other_text" class="text-xs text-gray-400 mt-3 pt-3 border-t border-gray-50 line-clamp-2 italic">
            {{ lot.other_text }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
