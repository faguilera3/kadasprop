<script setup lang="ts">
import { ref, watch } from 'vue'
import { searchAddress, type Suggestion } from '../services/location'

// Update location service to use relative path if it's using absolute
// Wait, location service is imported. Let's check location.ts content.

const emit = defineEmits(['search'])
const address = ref('')
const loading = ref(false)
const suggestions = ref<Suggestion[]>([])
const showSuggestions = ref(false)
const selectedIndex = ref(-1)

const isSelecting = ref(false)

// Debounce search
let timeout: number | null = null

watch(address, (newValue) => {
  if (timeout) clearTimeout(timeout)

  // If we are selecting a suggestion, ignore this change
  if (isSelecting.value) {
    isSelecting.value = false
    return
  }
  
  if (newValue.length < 3) {
    suggestions.value = []
    showSuggestions.value = false
    return
  }

  timeout = window.setTimeout(async () => {
    loading.value = true
    const results = await searchAddress(newValue)
    
    // Only update if the address hasn't changed significantly in the meantime
    // and if the input is still focused (optional check)
    if (address.value === newValue) {
      suggestions.value = results
      showSuggestions.value = results.length > 0
      selectedIndex.value = -1
    }
    loading.value = false
  }, 300)
})

const handleSearch = () => {
  if (!address.value.trim()) return
  
  // Clear suggestions immediately to avoid flicker or stale data
  showSuggestions.value = false
  suggestions.value = []
  
  emit('search', address.value)
}

const selectSuggestion = (suggestion: Suggestion) => {
  // Clear any pending timeout
  if (timeout) clearTimeout(timeout)

  // Flag to prevent watcher from triggering a new search
  isSelecting.value = true
  
  address.value = suggestion.label
  
  // Clear suggestions IMMEDIATELY
  suggestions.value = []
  showSuggestions.value = false
  
  handleSearch()
}

const handleKeydown = (e: KeyboardEvent) => {
  if (!showSuggestions.value) return

  if (e.key === 'ArrowDown') {
    e.preventDefault()
    selectedIndex.value = (selectedIndex.value + 1) % suggestions.value.length
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    selectedIndex.value = selectedIndex.value - 1 < 0 ? suggestions.value.length - 1 : selectedIndex.value - 1
  } else if (e.key === 'Enter') {
    if (selectedIndex.value >= 0) {
      selectSuggestion(suggestions.value[selectedIndex.value])
    } else {
      handleSearch()
    }
  } else if (e.key === 'Escape') {
    showSuggestions.value = false
  }
}
</script>

<template>
  <div class="w-full max-w-2xl mx-auto p-2 relative">
    <div class="relative flex items-center group">
      <div class="absolute inset-0 bg-[#e8e2fb] rounded-full blur opacity-20 group-hover:opacity-40 transition-opacity duration-300"></div>
      <input
        v-model="address"
        @keydown="handleKeydown"
        type="text"
        placeholder="Ingresá una dirección (ej: Cordoba 1000)"
        class="relative w-full px-8 py-5 text-lg border-0 bg-white rounded-full shadow-[0_4px_20px_-2px_rgba(0,0,0,0.1)] focus:shadow-[0_8px_30px_-4px_rgba(117,61,219,0.2)] placeholder-gray-400 text-gray-700 outline-none ring-1 ring-gray-100 focus:ring-2 focus:ring-[#753ddb] transition-all duration-300 pr-20"
        @focus="showSuggestions = suggestions.length > 0"
      />
      
      <!-- Loading Indicator -->
      <div v-if="loading" class="absolute right-20 animate-spin rounded-full h-5 w-5 border-b-2 border-[#753ddb]"></div>

      <button
        @click="handleSearch"
        class="absolute right-3 p-3.5 bg-gradient-to-r from-[#753ddb] to-[#561eb0] text-white rounded-full shadow-md hover:shadow-lg hover:scale-105 active:scale-95 transition-all duration-300 flex items-center justify-center z-10"
        :disabled="loading"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </button>
    </div>

    <!-- Suggestions Dropdown -->
    <div 
      v-if="showSuggestions"
      class="absolute top-full left-0 right-0 mt-2 bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden z-50 animate-fade-in mx-2"
    >
      <ul class="py-2">
        <li 
          v-for="(suggestion, index) in suggestions" 
          :key="suggestion.id"
          @click="selectSuggestion(suggestion)"
          @mouseenter="selectedIndex = index"
          class="px-6 py-3 cursor-pointer transition-colors flex items-center gap-3"
          :class="{ 'bg-gray-50 text-[#753ddb]': index === selectedIndex, 'text-gray-700 hover:bg-gray-50': index !== selectedIndex }"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-400" :class="{ 'text-[#753ddb]': index === selectedIndex }" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <div class="flex flex-col items-start">
            <span class="font-medium text-sm">{{ suggestion.label }}</span>
            <span class="text-[10px] text-gray-400 uppercase tracking-wide font-bold">{{ suggestion.type.replace('_', ' ') }}</span>
          </div>
        </li>
      </ul>
      <div class="bg-gray-50 px-4 py-2 text-[10px] text-gray-400 text-center border-t border-gray-100 uppercase tracking-wider font-semibold">
        Fuente: Municipalidad de Rosario
      </div>
    </div>
    
    <!-- Backdrop to close suggestions -->
    <div 
      v-if="showSuggestions" 
      class="fixed inset-0 z-40" 
      @click="showSuggestions = false"
    ></div>

  </div>
</template>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
