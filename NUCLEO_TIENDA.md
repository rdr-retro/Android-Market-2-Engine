# Nucleo Interno de Android Market 2

## 1. Resumen tecnico
Android Market 2 es una tienda Android legacy-oriented (minSdk 16 / Android 4.1) basada en una arquitectura Activity-centric, sin capas formales de repositorio ni ViewModel. El flujo principal es:

1. `MainActivity` descarga y parsea un `apps.txt` remoto.
2. Convierte cada entrada a modelos de UI (`RecommendedApp` y `FeedItem`).
3. Renderiza un feed heterogeneo con `RecyclerView` + `FeedAdapter`.
4. Navega a `DetailsActivity` con un payload serializado en `Intent`.
5. `DetailsActivity` resuelve instalacion (Play Store o descarga de APK directa con mirrors).

## 2. Stack y restricciones base

- Lenguaje: Kotlin.
- UI toolkit: Android Views clasicas (sin Compose).
- `RecyclerView` para feed.
- Networking: `HttpURLConnection` con wrapper propio (`NetClient`).
- Cache de imagen:
- L1: RAM (`ConcurrentHashMap<String, Bitmap>`).
- L2: disco (`ImageDiskCache` en `cacheDir/market_image_cache`).
- Minimo SDK: 16.
- Sin librerias externas de networking o imagen (no Retrofit, no Glide, no Coil).

## 3. Estructura de componentes

### 3.1 Entry point
- `MainActivity`: carga feed, parsea remoto, controla overlay de carga y navega a categorias/detalle.

### 3.2 Presentacion de feed
- `FeedAdapter`: adapter multivista con 3 view types:
- Hero banner.
- Bloque de categorias + recomendadas.
- Lista normal de apps.

### 3.3 Detalle e instalacion
- `DetailsActivity`: muestra metadata, screenshots, compatibilidad Android, estado de instalado y flujo de instalacion.

### 3.4 Utilidades de infraestructura
- `NetClient`: GET HTTP/HTTPS con configuracion TLS retrocompatible.
- `ImageDiskCache`: cache persistente de bitmaps por hash MD5 de URL.
- `ZoomableImageView`: visor full-screen con matrix transform (pinch zoom, drag, double-tap).

### 3.5 Pantallas secundarias
- `AppsCategoryActivity`, `GamesCategoryActivity`, `BooksCategoryActivity`, `MoviesCategoryActivity`: Activities de categoria con comportamiento minimalista (solo `finish()` desde back).

## 4. Pipeline de datos del catalogo

## 4.1 Origen remoto
`MainActivity` consulta varias URLs espejo de `apps.txt` en este orden:

1. `raw.githubusercontent.com`
2. `github.com/raw/...`
3. `blob?...raw=1`
4. jsDelivr
5. raw.githack
6. Fallback API GitHub Contents + Base64 decode

La primera respuesta no vacia se usa como fuente canonical de sesion.

## 4.2 Parseo tolerante (`parseAppsTxt`)
El parser soporta dos formatos:

1. Bloques `key=value` o `key:value` separados por linea en blanco.
2. CSV de una linea (`name,developer,stars,icon,package` + extras opcionales).

Normalizaciones importantes:

- `stars` y typo `starts`.
- alias de descripcion: `description`, `desc`, `descripcion`, `descripccion`.
- alias de screenshots: `screenshotX`, `screenX`, `captureX`.
- alias de categoria y version minima.
- `type` normalizado a `recommended`/`normal` con sinonimos (`featured`, `recomendado`, etc.).

## 4.3 Regla de particion recomendadas vs normales

- Si no existe `type` explicito: primeras 4 apps => recomendadas, resto => normales.
- Si existe `type`: se respeta, pero si hay menos de 4 recomendadas, se promueven normales hasta completar 4.

## 5. Resolucion de iconos y assets

## 5.1 `resolveIconSpec` en `MainActivity`
Cada entrada genera:

- `iconUrl`: URL remota final (o `null`).
- `fallbackRes`: recurso local drawable a usar como fallback.

Regla clave:

- Si el icono referenciado coincide con un drawable local (ej. `ic_menu_bag_*.png`) y no es URL remota, se prioriza recurso local (`iconUrl = null`).
- Si es remoto, se normaliza GitHub `blob`/`raw` a `raw.githubusercontent.com`.

Esto evita fallos por intentar descargar iconos que realmente son assets empaquetados.

## 5.2 Cache buster
Para assets GitHub se agrega `?v=<hashDelAppsTxt>` para invalidar cache cuando cambia el catalogo.

## 6. Render del feed y paginacion

## 6.1 Feed heterogeneo
`FeedAdapter` siempre reserva 2 filas iniciales:

- Posicion 0: hero.
- Posicion 1: bloque de categorias + recomendadas.

El resto son apps normales.

## 6.2 Paginacion incremental
`MainActivity` implementa infinite scroll:

- Al acercarse al final (`lastVisible >= itemCount - 4`), agrega lote de 12.
- Fuente de datos circular: usa modulo sobre `remoteApps` para no agotar lista.

## 6.3 Overlay de carga reutilizado
`loading_overlay` sirve para:

- carga inicial de feed.
- transicion al detalle al pulsar app.

Se controla con flags:

- `initialLoadingVisible`
- `openingDetailsVisible`

## 7. Subsistema de imagen (core)

Hay dos implementaciones paralelas (feed y details) con la misma estrategia:

1. Placeholder inmediato (`fallbackRes`).
2. Lookup RAM cache.
3. Lookup disk cache.
4. Descarga por candidatos URL.
5. Retry burst + retry periodico.

## 7.1 Candidatos URL para robustez
De una URL base se generan mirrors equivalentes:

- `raw.githubusercontent.com`
- `cdn.jsdelivr.net/gh/...`
- `raw.githack.com/...`
- `github.com/.../raw/refs/heads/...`

Esto reduce errores por CDN o endpoint puntual caido.

## 7.2 Politica de retries

- Reintentos inmediatos internos por ciclo.
- Backoff escalonado (700ms, 1300ms, 2200ms, 3500ms, 5000ms).
- Luego retry periodico continuo (cada ~6s) mientras el `ImageView.tag` siga apuntando a esa URL.

## 7.3 Control de coherencia por `tag`
Cada `ImageView` guarda `tag = requestedUrl`.
Antes de aplicar bitmap descargado se valida que el `tag` siga siendo el mismo. Eso evita race conditions por reciclado de celdas o cambios de pantalla.

## 7.4 `ImageDiskCache`

- Key: `md5(url)`.
- TTL: 7 dias.
- Cap: 24 archivos mas recientes.
- Lectura valida actualiza `lastModified` para LRU simple.

## 8. Flujo de detalle e instalacion

## 8.1 Entrada de datos
`DetailsActivity.newIntent()` recibe `AppDetailsPayload` (title, developer, stars, package/target, icon, screenshots, minAndroid, descripcion).

## 8.2 Compatibilidad Android
Se traduce `minandroid` textual a API level via tabla hardcoded (`androidVersionToApi`) y se compara con `Build.VERSION.SDK_INT`.

Estados de boton:

- App instalada: `Abrir`.
- Compatible y no instalada: precio/base text.
- Incompatible: `Version no compatible`.

## 8.3 Deteccion de app instalada
2 rutas:

1. Si `installTarget` parece package name, consulta directa `packageManager.getPackageInfo`.
2. Si no, fallback por matching de label normalizada contra titulo app.

## 8.4 Instalacion por target

- Si target es package: abre Play Store (`market://`) con fallback web.
- Si target es URL APK: descarga directa a `getExternalFilesDir(DIRECTORY_DOWNLOADS)` con archivo temporal `.part`, barra de progreso legacy y apertura via `FileProvider`.

## 8.5 Descarga APK robusta

- Mirror list igual que imagen (raw + cdn + githack + github raw heads).
- Progress UI actualizada cada ~120ms.
- Renombrado atomico `.part -> .apk` con fallback copy.

## 9. Visor full-screen de capturas

- Thumbnails en detalle usan `fitCenter` (no recorte por `centerCrop`).
- Tap en screenshot abre dialog full-screen negro.
- Render con `ZoomableImageView`:
- ScaleType MATRIX.
- Pinch zoom (hasta 5x).
- Pan condicionado a escala > 1x.
- Double tap alterna 1x / 2.5x.
- Single tap cierra.

## 10. Networking y compat TLS

`NetClient.openGet` centraliza:

- timeouts base.
- redirects.
- headers (`User-Agent`, `Accept`, `Connection`).
- soporte HTTPS con `TlsCompatSocketFactory` que habilita protocolos disponibles priorizando `TLSv1.3 -> 1.2 -> 1.1 -> 1.0`.

Objetivo: mejorar operatividad en dispositivos/API antiguos sin romper endpoints modernos.

## 11. Permisos y manifest

- `INTERNET`: obligatorio para catalogo, iconos y APK remoto.
- `REQUEST_INSTALL_PACKAGES`: para flujo de instalacion APK sideload.
- `WRITE_EXTERNAL_STORAGE` limitado a `maxSdkVersion=28` para compat legacy.
- `FileProvider` configurado para compartir APK descargado con instalador del sistema.

## 12. Estado actual del diseno (tradeoffs)

Ventajas:

- Muy portable para Android viejos.
- Dependencias minimas.
- Robustez alta en red irregular por mirrors + retries + caches.

Limitaciones:

- Sin arquitectura por capas (no repository/use-cases).
- Sin lifecycle-aware async (no coroutines + scope cancelation).
- Sin diff util ni paging formal.
- Sin telemetria para medir tasas de fallo por endpoint.

## 13. Mapa de ejecucion end-to-end

1. Usuario abre app.
2. `MainActivity` muestra overlay y descarga `apps.txt`.
3. Parser normaliza y separa recomendadas/normal.
4. Feed se renderiza con iconos locales/remotos.
5. Pulsar app activa overlay corto y abre detalle.
6. `DetailsActivity` aplica compatibilidad, carga imagenes robustamente y habilita instalacion.
7. Si APK remoto, descarga con progreso y abre instalador.
8. Al volver, estado de instalacion e imagenes se refresca.

## 14. Archivos nucleares

- `app/src/main/java/com/rdr/androidmarket2/MainActivity.kt`
- `app/src/main/java/com/rdr/androidmarket2/FeedAdapter.kt`
- `app/src/main/java/com/rdr/androidmarket2/DetailsActivity.kt`
- `app/src/main/java/com/rdr/androidmarket2/NetClient.kt`
- `app/src/main/java/com/rdr/androidmarket2/ImageDiskCache.kt`
- `app/src/main/java/com/rdr/androidmarket2/ZoomableImageView.kt`
- `app/src/main/AndroidManifest.xml`
- `app/apps.txt`
