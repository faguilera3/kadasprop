<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import proj4 from 'proj4'
import 'proj4leaflet'

// Fix for default marker icon
import icon from 'leaflet/dist/images/marker-icon.png'
import iconShadow from 'leaflet/dist/images/marker-shadow.png'

const DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
})
L.Marker.prototype.options.icon = DefaultIcon

const props = defineProps<{
  lat: number
  lng: number
  zoom?: number
}>()

const mapContainer = ref<HTMLElement | null>(null)
let map: L.Map | null = null
let marker: L.Marker | null = null

// Sources
const WMS_PLANOBASE = 'https://infomapa.rosario.gov.ar/wms/planobase?'
const WMS_CODIGO = 'https://infomapa.rosario.gov.ar/wms/codigourbano?'
const WMS_INFRA = 'https://infomapa.rosario.gov.ar/wms/infraestructura?'

// Define Groups and Layers
type LayerDef = {
  id: string
  name: string
  wmsUrl?: string // Optional specific URL override
  default?: boolean
}

type LayerGroup = {
  name: string
  isOpen: boolean
  layers: LayerDef[]
}

const layerGroups = ref<LayerGroup[]>([
  {
    name: "Normas Urbanísticas",
    isOpen: true,
    layers: [
      { id: 'Zonas Urbanisticas', name: 'Áreas Urbanísticas', wmsUrl: WMS_CODIGO, default: true },
      { id: 'Distritos Urbanos', name: 'Distritos Urbanos', wmsUrl: WMS_CODIGO },
      { id: 'Grados de Proteccion', name: 'Catálogo e Inventario', wmsUrl: WMS_CODIGO },
      { id: 'Red Jerarquica', name: 'Red Jerárquica', wmsUrl: WMS_CODIGO },
      { id: 'Zonas_Areas_Inundables_Saladillo_Luduena', name: 'Zonas Inundables', wmsUrl: WMS_CODIGO },
      { id: 'Urbanizacion_Subdivision_tierra', name: 'Urbanización', wmsUrl: WMS_CODIGO },
      { id: 'clubes_ordenanza_ord_9201_2014', name: 'Clubes y Asociaciones', wmsUrl: WMS_CODIGO },
      { id: 'Centro de Manzanas', name: 'Centro de Manzana', wmsUrl: WMS_CODIGO },
      { id: 'Recovas', name: 'Recovas', wmsUrl: WMS_CODIGO },
      { id: 'helipuerto', name: 'Helipuertos', wmsUrl: WMS_CODIGO }
    ]
  },
  {
    name: "Infraestructura",
    isOpen: true,
    layers: [
      { id: 'cruces_con_semaforos', name: 'Semáforos', wmsUrl: WMS_INFRA },
      { id: 'Antenas', name: 'Antenas', wmsUrl: WMS_INFRA },
      { id: 'Alumbrado Publico', name: 'Alumbrado Público', wmsUrl: WMS_INFRA },
      { id: 'Columnas', name: 'Alumbrado: Columnas', wmsUrl: WMS_INFRA },
      { id: 'Tableros', name: 'Alumbrado: Tableros', wmsUrl: WMS_INFRA },
      { id: 'Infraestructura_Cloacal', name: 'Red Cloacal', wmsUrl: WMS_INFRA },
      { id: 'Conductos_Plan_Integral', name: 'Desagües Pluviales', wmsUrl: WMS_INFRA },
      { id: 'Sumideros', name: 'Sumideros', wmsUrl: WMS_INFRA }
    ]
  },
  {
    name: "Mapas Base",
    isOpen: false,
    layers: [
      { id: 'planobase:plano_base', name: 'Plano Base', default: true },
      { id: 'Fotos2013', name: 'Fotos Aéreas 2013' },
      { id: 'ImagenesSatelitales2011', name: 'Satelital 2011' }
    ]
  },
  {
    name: "Catastro y Subdivisiones",
    isOpen: false,
    layers: [
      { id: 'manzanas', name: 'Manzanas', default: true },
      { id: 'parcelas', name: 'Parcelas', default: true },
      { id: 'numeros_de_manzana', name: 'Nros. de Manzana' },
      { id: 'distritos_descentralizados', name: 'Distritos Admin.' },
      { id: 'manzanas_no_regularizada', name: 'Manzanas No Reg.' }
    ]
  },
  {
    name: "Transporte y Otros",
    isOpen: false,
    layers: [
      { id: 'nombres_de_calles', name: 'Nombres de Calles', default: true },
      { id: 'sentidos_de_calle', name: 'Sentido de Calles' },
      { id: 'autopistas', name: 'Autopistas' },
      { id: 'av_circunvalacion', name: 'Circunvalación' },
      { id: 'via_ferroviaria', name: 'Vías Férreas' },
      { id: 'hidrografia', name: 'Hidrografía' },
      { id: 'espacios_verdes', name: 'Espacios Verdes' }
    ]
  }
])

// Flatten for easy access
const allLayers = layerGroups.value.flatMap(g => g.layers)
const activeLayers = ref<string[]>(allLayers.filter(l => l.default).map(l => l.id))
const layerInstances: Record<string, L.TileLayer.WMS> = {}

onMounted(() => {
  if (!mapContainer.value) return

  map = L.map(mapContainer.value, {
    zoomControl: false // We'll add it manually if needed or stick to default position
  }).setView([props.lat, props.lng], props.zoom || 17)

  // Zoom control top-right to avoid sidebar
  L.control.zoom({ position: 'topright' }).addTo(map)

  // Standard OSM Layer
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
  }).addTo(map)

  // Add marker
  marker = L.marker([props.lat, props.lng]).addTo(map!)

  // Initialize all WMS layers
  allLayers.forEach(layer => {
    // Default to planobase if not specified
    const url = layer.wmsUrl || WMS_PLANOBASE
    
    const wmsLayer = L.tileLayer.wms(url, {
      layers: layer.id,
      format: 'image/png',
      transparent: true,
      version: '1.1.1', // Updated to match user snippet
      attribution: 'Municipalidad de Rosario',
      crs: L.CRS.EPSG4326
    })
    
    layerInstances[layer.id] = wmsLayer
    
    if (activeLayers.value.includes(layer.id)) {
      wmsLayer.addTo(map!)
    }
  })
})

const toggleLayer = (layerId: string) => {
  if (!map) return
  
  if (activeLayers.value.includes(layerId)) {
    activeLayers.value = activeLayers.value.filter(id => id !== layerId)
    map.removeLayer(layerInstances[layerId])
  } else {
    activeLayers.value.push(layerId)
    layerInstances[layerId].addTo(map)
    layerInstances[layerId].bringToFront() // Ensure new layer is on top
  }
}

const toggleGroup = (groupName: string) => {
  const group = layerGroups.value.find(g => g.name === groupName)
  if (group) {
    group.isOpen = !group.isOpen
  }
}

watch(() => [props.lat, props.lng], ([newLat, newLng]) => {
  if (map) {
    map.setView([newLat, newLng], map.getZoom())
    if (marker) {
      marker.setLatLng([newLat, newLng])
    }
  }
})
</script>

<template>
  <div class="flex h-full bg-white rounded-xl overflow-hidden border border-gray-200 shadow-sm relative">
    
    <!-- Sidebar -->
    <div class="w-64 bg-white border-r border-gray-200 flex flex-col overflow-y-auto h-full z-[1001] shadow-lg">
      <div class="p-4 bg-primary-500 text-white font-bold text-sm uppercase tracking-wide flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
        </svg>
        Capas InfoMapa
      </div>

      <div class="flex-1">
        <div v-for="group in layerGroups" :key="group.name" class="border-b border-gray-100">
          <!-- Accordion Header -->
          <button 
            @click="toggleGroup(group.name)"
            class="w-full flex items-center justify-between p-3 text-left hover:bg-gray-50 transition-colors"
          >
            <span class="font-semibold text-gray-700 text-sm">{{ group.name }}</span>
            <svg 
              xmlns="http://www.w3.org/2000/svg" 
              class="h-4 w-4 text-gray-400 transition-transform duration-200"
              :class="{ 'rotate-180': group.isOpen }"
              fill="none" viewBox="0 0 24 24" stroke="currentColor"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          <!-- Accordion Content -->
          <div v-show="group.isOpen" class="bg-gray-50/50 px-3 pb-3 pt-1 space-y-1">
            <label 
              v-for="layer in group.layers" 
              :key="layer.id"
              class="flex items-center gap-2 p-1.5 rounded hover:bg-white cursor-pointer group/item"
            >
              <div class="relative flex items-center">
                <input 
                  type="checkbox" 
                  :checked="activeLayers.includes(layer.id)"
                  @change="toggleLayer(layer.id)"
                  class="peer h-4 w-4 rounded border-gray-300 text-primary-500 focus:ring-primary-500 cursor-pointer"
                />
              </div>
              <span class="text-sm text-gray-600 group-hover/item:text-gray-900">{{ layer.name }}</span>
            </label>
          </div>
        </div>
      </div>
      
      <div class="p-3 text-xs text-gray-400 bg-gray-50 border-t border-gray-200">
        Fuente: Municipalidad de Rosario
      </div>
    </div>
    
    <!-- Map Container -->
    <div ref="mapContainer" class="flex-1 h-full z-0 bg-gray-100"></div>
  </div>
</template>

<style scoped>
/* Custom scrollbar for sidebar */
.overflow-y-auto::-webkit-scrollbar {
  width: 4px;
}
.overflow-y-auto::-webkit-scrollbar-track {
  background: transparent;
}
.overflow-y-auto::-webkit-scrollbar-thumb {
  background-color: #e5e7eb;
  border-radius: 20px;
}
</style>