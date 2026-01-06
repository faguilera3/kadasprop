# 📍 INFOMAPA ROSARIO - Guía Técnica Completa & Integración Dunod

**Última actualización**: Enero 2026  
**Versión**: 1.0  
**Autor**: Documentación Técnica - Municipalidad de Rosario

---

## 📋 Tabla de Contenidos

1. [🎯 Resumen Ejecutivo](#resumen-ejecutivo)
2. [🏗️ Arquitectura General](#arquitectura-general)
3. [🔵 WMS Rosario](#wms-rosario)
4. [🟩 APIs REST de Ubicaciones](#apis-rest-de-ubicaciones)
5. [🟨 GeorRef - Georreferencia Nacional](#georef---georreferencia-nacional)
6. [📊 Comparativa de Fuentes](#comparativa-de-fuentes)
7. [💻 Opciones de Implementación](#opciones-de-implementación)
8. [🔗 Integración con Dunod](#integración-con-dunod)
9. [⚙️ Ejemplos de Código](#ejemplos-de-código)
10. [📈 Límites y Escalabilidad](#límites-y-escalabilidad)

---

## 🎯 Resumen Ejecutivo

**InfoMapa** es la plataforma geoespacial oficial de la Municipalidad de Rosario que integra:

- ✅ **150+ capas** de información cartográfica, catastral y de servicios
- ✅ **WMS Estándar OGC** para visualización de mapas complejos
- ✅ **APIs REST** para búsquedas y datos estructurados
- ✅ **Integración GeorRef** para contexto geográfico nacional
- ✅ **Datos públicos** en formato abierto (GeoJSON, CSV, JSON)

### Ubicación Oficial
- **Web**: https://infomapa.rosario.gov.ar/emapa/mapa.htm
- **Datos Abiertos**: https://datosabiertos.rosario.gob.ar
- **Stack**: OpenLayers 2.11 + jQuery + WMS + REST APIs

---

## 🏗️ Arquitectura General

┌────────────────────────────────────────────────────────────────┐
│ INFOMAPA.ROSARIO.GOV.AR (Frontend) │
│ OpenLayers 2.11 + jQuery + HTML5 Geolocation + Canvas/SVG │
└──────────────────────────┬─────────────────────────────────────┘
│
┌─────────────────┼─────────────────┐
│ │ │
▼ ▼ ▼

text
🔷 WMS ROSARIO       🔶 APIS REST         🔸 GEOREF
Web Map Service     Ubicaciones          Georreferencia

├─ Plano base       ├─ Direcciones       ├─ Provincias
├─ Catastrales      ├─ Lugares           ├─ Municipios
├─ Manzanas         ├─ Servicios         ├─ Localidades
├─ Parcelas         ├─ Normas urbanas    ├─ Calles
├─ Divisiones       ├─ Infraestructura   ├─ Cuadras
└─ Topografía       └─ Datos públicos    └─ Asentamientos

https://www.rosario  https://ws.rosario  https://apis.datos
.gob.ar/wms/        .gob.ar/ubicaciones/ .gob.ar/georef/
planobase?          public/geojson/      api/v2.0/
text

### Flujo de Datos

Usuario busca: "Mitre 250"
│
▼
┌─────────────────────────────────────┐
│ API REST: GET /direccion/mitre/250 │
│ Respuesta: {lat, lng, info, lote} │
└─────────────────────────────────────┘
│
▼
┌─────────────────────────────────────┐
│ WMS: GetFeatureInfo (lote) │
│ Respuesta: Imagen + atributos │
└─────────────────────────────────────┘
│
▼
┌─────────────────────────────────────┐
│ API REST: GET /normas/{lote} │
│ Respuesta: Regulaciones + datos │
└─────────────────────────────────────┘
│
▼
Mostrar resultado en mapa

text

---

## 🔵 WMS Rosario

### Descripción

**WMS (Web Map Service)** es un estándar OGC para proporcionar imágenes de mapas sobre demanda. Permite superponer múltiples capas complejas sin necesidad de procesar datos en el cliente.

### Características

- ✅ Renderización server-side (no consume recursos del navegador)
- ✅ Soporta 50,000+ polígonos sin problemas
- ✅ Consultas espaciales (punto en polígono)
- ✅ Capas superpuestas automáticas
- ✅ Actualización periódica (semanal)
- ❌ Devuelve imagen (no datos estructurados)
- ❌ No permite filtros de atributos

### URL Base

https://www.rosario.gob.ar/wms/planobase?

text

### Operaciones Disponibles

#### 1. GetCapabilities
Obtiene lista completa de capas, proyecciones y escalas soportadas.

```bash
curl "https://www.rosario.gob.ar/wms/planobase?SERVICE=WMS&VERSION=1.1.0&REQUEST=GetCapabilities"
Respuesta: XML con metadatos del servicio

xml
<?xml version="1.0" encoding="UTF-8"?>
<WMT_MS_Capabilities version="1.1.0">
  <Service>
    <Name>WMS</Name>
    <Title>Servicio WMS Rosario</Title>
    <OnlineResource xlink:href="https://www.rosario.gob.ar/wms/planobase?"/>
  </Service>
  <Capability>
    <Request>
      <GetCapabilities>
        <Format>application/vnd.ogc.wms_xml</Format>
      </GetCapabilities>
      <GetMap>
        <Format>image/png</Format>
        <Format>image/jpeg</Format>
      </GetMap>
      <GetFeatureInfo>
        <Format>text/plain</Format>
        <Format>text/html</Format>
      </GetFeatureInfo>
    </Request>
    <Layer queryable="1">
      <Name>planobase:eje_calles</Name>
      <Title>Eje de Calles</Title>
      <SRS>EPSG:32723</SRS>
      <BoundingBox SRS="EPSG:32723" minx="5400000" miny="6300000" maxx="5500000" maxy="6400000"/>
    </Layer>
    <Layer queryable="1">
      <Name>planobase:parcelas</Name>
      <Title>Parcelas Catastrales</Title>
      <SRS>EPSG:32723</SRS>
    </Layer>
  </Capability>
</WMT_MS_Capabilities>
Capas Disponibles:

Nombre	Descripción	Tipo	Queryable
planobase:eje_calles	Red viaria	LineString	Sí
planobase:parcelas	Divisiones catastrales	Polygon	Sí
planobase:manzanas	Agrupaciones de parcelas	Polygon	Sí
planobase:plano_base	Imagen topográfica	Raster	No
planobase:divisiones_admin	Distritos y zonas	Polygon	Sí
2. GetMap
Descarga una imagen de mapa para un área específica.

bash
curl "https://www.rosario.gob.ar/wms/planobase?SERVICE=WMS&VERSION=1.1.0&REQUEST=GetMap&LAYERS=planobase:parcelas,planobase:eje_calles&BBOX=5430000,6330000,5450000,6350000&WIDTH=800&HEIGHT=600&SRS=EPSG:32723&FORMAT=image/png&TRANSPARENT=true"
Parámetros:

SERVICE=WMS - Tipo de servicio

VERSION=1.1.0 - Versión del protocolo

REQUEST=GetMap - Operación

LAYERS - Capas a mostrar (separadas por coma)

BBOX - Cuadro delimitador [minx,miny,maxx,maxy]

WIDTH/HEIGHT - Dimensiones en píxeles

SRS=EPSG:32723 - Sistema de coordenadas (UTM Zone 23S)

FORMAT=image/png - Formato de salida

TRANSPARENT=true - Fondo transparente

Respuesta: Imagen PNG con las capas solicitadas

3. GetFeatureInfo
Obtiene información al hacer click en el mapa.

bash
curl "https://www.rosario.gob.ar/wms/planobase?SERVICE=WMS&VERSION=1.1.0&REQUEST=GetFeatureInfo&LAYERS=planobase:parcelas&QUERY_LAYERS=planobase:parcelas&X=400&Y=300&INFO_FORMAT=text/html&BBOX=5430000,6330000,5450000,6350000&WIDTH=800&HEIGHT=600&SRS=EPSG:32723"
Parámetros adicionales:

X,Y - Píxeles en la imagen donde se hace click

INFO_FORMAT - Formato de respuesta (text/plain, text/html, application/json)

FEATURE_COUNT - Número máximo de features a retornar

Respuesta: Información de las features en el punto clickeado

xml
Results for point (400,300):
Layer 'planobase:parcelas'
  Feature 0:
    ID: 12345
    NOMENCLATURA: 8-V-8-a
    AREA: 250.5
    FOS: 0.6
    FOT: 1.8
    ALTURA_MAX: 15
    USO: Comercial
🟩 APIs REST de Ubicaciones
Descripción
APIs JSON/GeoJSON que devuelven datos geoestructurados. Perfectas para búsquedas, filtros y procesamiento de datos en aplicaciones.

Características
✅ Datos estructurados (JSON/GeoJSON)

✅ Búsquedas textuales

✅ Múltiples filtros

✅ Información actualizada (online)

✅ Fácil de procesar en código

⚠️ Limitadas a ~50K features

⚠️ Performance decrece con muchos datos

URL Base
text
https://ws.rosario.gob.ar/ubicaciones/public/geojson/
Endpoints Principales
1. Ubicaciones Generales
text
GET /ubicaciones/all/true/0/all
Descripción: Obtiene todas las ubicaciones (direcciones + lugares de interés)

Parámetros:

all - Búsqueda de texto (o "all" para todas)

true - Información completa (false para reducida)

0 - Scope: 0=todos, 1=nacional, 2=provincial, 3=municipal, 4=privado, 5=mixto, 6=ONG

all - Etiqueta/categoría

Ejemplo:

bash
curl "https://ws.rosario.gob.ar/ubicaciones/public/geojson/ubicaciones/all/true/0/all"
Respuesta (GeoJSON):

json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": "loc_001",
      "geometry": {
        "type": "Point",
        "coordinates": [-60.661721, -32.945542]
      },
      "properties": {
        "name": "Terminal de Omnibus",
        "calle": "Santa Fe",
        "altura": 1950,
        "bis": false,
        "letra": "",
        "tipo": "transporte",
        "subtipo": "lugar",
        "description": "Terminal de ómnibus interprovincial",
        "coordenada_ref": "UTM:5438500,6348000",
        "estado": "publicado",
        "etiquetas": ["transporte", "servicios"],
        "codigo_calle": 1234,
        "divs_admin": [
          {"codigo": "01", "nombreAbrev": "DNO", "tipo": "distrito", "valor": "Distrito Norte"}
        ],
        "piso": "",
        "departamento": "",
        "lineas_tup": ["1", "2", "3"],
        "contactos": {"telefono": "0341-XXXX", "email": "info@terminal.gov.ar"},
        "atencion": "Lun-Dom: 6:00-23:00",
        "multimedia": ["foto_1.jpg"],
        "titular": "Municipalidad de Rosario",
        "ultima_actualizacion": "2025-12-15"
      }
    },
    {
      "type": "Feature",
      "id": "loc_002",
      "geometry": {
        "type": "Point",
        "coordinates": [-60.668500, -32.948000]
      },
      "properties": {
        "name": "Hospital Provincial",
        "calle": "9 de Julio",
        "altura": 2000,
        "bis": false,
        "letra": "",
        "tipo": "salud",
        "subtipo": "lugar",
        "description": "Hospital público provincial",
        "etiquetas": ["salud", "servicios"]
      }
    }
  ]
}
2. Búsqueda por Texto
text
GET /ubicaciones/{busqueda}/true/{scope}/{etiqueta}
Ejemplo - Lugares de salud en Rosario:

bash
curl "https://ws.rosario.gob.ar/ubicaciones/public/geojson/ubicaciones/salud/true/3/all"
Ejemplo - Educación en municipio (scope=3):

bash
curl "https://ws.rosario.gob.ar/ubicaciones/public/geojson/ubicaciones/educacion/true/3/all"
Ejemplo - Cultura en toda la provincia:

bash
curl "https://ws.rosario.gob.ar/ubicaciones/public/geojson/ubicaciones/cultura/true/2/all"