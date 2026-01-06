export interface Suggestion {
  id: string
  label: string
  type: string
}

export const searchAddress = async (query: string): Promise<Suggestion[]> => {
  if (!query || query.length < 3) return []

  try {
    // Use our local proxy endpoint to avoid CORS issues
    // Using relative path for production compatibility (Vite proxy in dev, Nginx in prod)
    const response = await fetch(`/proxy/locations/${encodeURIComponent(query)}`)
    if (!response.ok) return []

    const data = await response.json()
    
    // The API returns GeoJSON features
    if (!data.features) return []

    return data.features.map((feature: any) => ({
      id: feature.properties.id || feature.properties.descripcion, // Use description as ID if ID is missing
      label: feature.properties.descripcion || feature.properties.name, // "ALEM LEANDRO N 1000" or "name"
      type: feature.properties.subtipo // "DIRECCION_EXACTA"
    })).slice(0, 10) // Limit to 10 suggestions

  } catch (error) {
    console.error('Error fetching suggestions:', error)
    return []
  }
}
