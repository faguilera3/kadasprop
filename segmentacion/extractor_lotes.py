import cv2
import numpy as np
import os
import argparse


def process_cadastral_map(image_path, output_dir, min_area=1000, max_area_percent=0.5, dilation_iter=6, epsilon_factor=0.001, min_line_area=100, closing_kernel_size=40, reconnect_lines_iter=2, reconnect_kernel_size=1):
    """
    Procesa un plano catastral para extraer lotes individuales.
    
    Args:
        image_path (str): Ruta a la imagen del plano.
        output_dir (str): Directorio donde guardar los recortes.
        min_area (int): Área mínima en píxeles para considerar un contorno como lote.
        max_area_percent (float): Porcentaje máximo del área total de la imagen para un lote.
        dilation_iter (int): Cantidad de dilatación de la máscara para incluir bordes/números.
        epsilon_factor (float): Factor de aproximación poligonal (menor = más fiel al contorno original).
        min_line_area (int): Área mínima para considerar un objeto blanco (línea) como pared. 
        closing_kernel_size (int): Tamaño del kernel para la operación de cierre morfológico (rellenar huecos de texto).
        reconnect_lines_iter (int): Iteraciones para reconectar líneas rotas al inicio.
        reconnect_kernel_size (int): Tamaño del kernel para reconectar líneas.
    """
    
    # 1. Cargar imagen
    if not os.path.exists(image_path):
        print(f"Error: No se encontró la imagen en {image_path}")
        return

    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: No se pudo leer la imagen. Verifique el formato.")
        return

    original = img.copy()
    h, w = img.shape[:2]
    total_area = h * w
    max_area = total_area * max_area_percent

    # 2. Preprocesamiento
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Binarización invertida (líneas blancas sobre fondo negro para encontrar contornos externos)
    # Usamos threshold adaptativo para manejar iluminación variable o manchas
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 11, 2)

    # Operaciones morfológicas para cerrar huecos en líneas y eliminar ruido
    # Kernel horizontal y vertical para reconstruir lineas?
    # Mejor un kernel rectangular genérico
    if reconnect_kernel_size > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (reconnect_kernel_size, reconnect_kernel_size))
        # Dilatar/Cerrar para conectar líneas rotas
        # Morph Close: Dilatación seguida de Erosión. Cierra huecos pequeños dentro de las zonas blancas (líneas)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=reconnect_lines_iter)
    
    # LIMPIEZA DE RUIDO Y TEXTO EN LAS LÍNEAS:
    # thresh tiene Líneas Blancas sobre Fondo Negro.
    # El texto también aparece como blobs blancos pequeños.
    # Si eliminamos los blobs pequeños, el texto desaparece de la "pared", 
    # por lo que el "Lote" (espacio vacío) podrá ocupar ese espacio.
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(thresh, connectivity=8)
    
    # stats: [x, y, width, height, area]
    thresh_clean = np.zeros_like(thresh)
    
    # Filtrar componentes
    for i in range(1, num_labels): # Empezamos en 1 para saltar el fondo (0)
        area = stats[i, cv2.CC_STAT_AREA]
        if area >= min_line_area:
            # Mantener componente (es una línea o estructura grande)
            thresh_clean[labels == i] = 255
            
    # ESTRATEGIA ACTUALIZADA:
    # Trabajamos con los "Lotes" como objetos blancos.
    # Invertimos la imagen de líneas LIMPIA para obtener lotes blancos sobre fondo negro.
    # Ahora el texto (que fue borrado de las líneas) es parte del fondo negro en thresh_clean...
    # Espera, thresh_clean: Lineas=Blanco, Fondo=Negro.
    # Invertir: Lineas=Negro, Fondo=Blanco.
    # Si borré el texto (era blanco, ahora es negro en thresh_clean), al invertir será BLANCO.
    # Por tanto, el espacio donde estaba el texto será parte del "Lote" (Blanco). ¡CORRECTO!
    lots_binary = cv2.bitwise_not(thresh_clean)
    
    # 3. Encontrar contornos en los lotes blancos
    # RETR_TREE recupera todos los contornos y reconstruye la jerarquía completa de contornos anidados.
    contours, hierarchy = cv2.findContours(lots_binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        print("No se encontraron contornos.")
        return

    print(f"Se encontraron {len(contours)} contornos iniciales.")

    # Crear directorio de salida
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Filtrar y ordenar contornos
    valid_lots = []
    h_img, w_img = img.shape[:2]
    
    # Helper para calcular profundidad
    def get_depth(idx, hier):
        depth = 0
        current = idx
        while hier[0][current][3] != -1:
            current = hier[0][current][3]
            depth += 1
        return depth

    for i, cnt in enumerate(contours):
        # Calcular profundidad
        # Si la profundidad es impar (1, 3...), es un contorno interior (agujero), que encierra negro.
        # Si la profundidad es par (0, 2...), es un contorno exterior, que encierra blanco (Lote).
        depth = get_depth(i, hierarchy)
        if depth % 2 != 0:
            continue

        # Calcular área
        area = cv2.contourArea(cnt)
        
        # Filtrar por área
        if area < min_area or area > max_area:
            continue
        
        # Filtrar contornos que tocan el borde de la imagen (generalmente es el marco o márgenes)
        bx, by, bw, bh = cv2.boundingRect(cnt)
        if bx <= 5 or by <= 5 or (bx + bw) >= (w_img - 5) or (by + bh) >= (h_img - 5):
            continue
            
        # Con la estrategia de "Lotes Blancos", los contornos externos de los lotes son lo que queremos.
        # No necesitamos filtrar por padre estrictamente, porque incluso si hay un lote dentro de otro (raro),
        # o un edificio dentro de un lote, queremos el contorno externo.
        # Sin embargo, el "marco" de la página podría ser detectado como un lote gigante si es blanco.
        # El filtro max_area ayuda aquí.
        
        # Adicionalmente, podemos verificar la solidez o la relación de aspecto si es necesario.
        
        valid_lots.append(cnt)
    
    print(f"Se detectaron {len(valid_lots)} lotes válidos después de filtrar.")
    
    # Ordenar lotes (opcional, por posición Y luego X para tener orden lógico)
    # bounding box: x, y, w, h
    valid_lots.sort(key=lambda c: (cv2.boundingRect(c)[1] // 100, cv2.boundingRect(c)[0])) 

    count = 0
    debug_img = original.copy()

    for cnt in valid_lots:
        # Aproximar el polígono
        # Reducimos epsilon para que el contorno sea más fiel a la forma real y no corte esquinas
        # Usamos el parámetro epsilon_factor
        epsilon = epsilon_factor * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        
        # 4. Extracción precisa
        # Crear una máscara para este lote específico
        x, y, w_rect, h_rect = cv2.boundingRect(approx)
        
        # Margen de seguridad para el recorte rectangular (ROI)
        # Aumentamos el margen en base a la dilatación para no cortar lo que expandimos
        margin = 10 + (dilation_iter * 2)
        x_start = max(0, x - margin)
        y_start = max(0, y - margin)
        x_end = min(w_img, x + w_rect + margin)
        y_end = min(h_img, y + h_rect + margin)

        # Recorte del área de interés
        roi = original[y_start:y_end, x_start:x_end]
        
        # Crear máscara ajustada al ROI
        mask = np.zeros((y_end - y_start, x_end - x_start), dtype=np.uint8)
        
        # Ajustar coordenadas del contorno al ROI
        cnt_roi = cnt - [x_start, y_start]
        
        # Dibujar el contorno relleno en la máscara
        cv2.drawContours(mask, [cnt_roi], -1, (255), thickness=cv2.FILLED)
        
        # CIERRE MORFOLÓGICO (IMPORTANTE):
        # Si el texto estaba pegado a la pared, creó una "bahía" o hueco en la máscara blanca.
        # Aplicamos Morphological Closing para cerrar esos huecos y recuperar el área del texto.
        if closing_kernel_size > 0:
            k_size = closing_kernel_size
            kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (k_size, k_size))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close)
            
        # DILATACIÓN DE SEGURIDAD:
        # Dilatamos ligeramente la máscara blanca para asegurar que incluimos los bordes internos
        # y cualquier texto que pudiera estar tocando el borde.
        if dilation_iter > 0:
            kernel_dilate = np.ones((3,3), np.uint8)
            mask = cv2.dilate(mask, kernel_dilate, iterations=dilation_iter)
        
        # Crear imagen final con fondo blanco
        result = np.ones_like(roi) * 255
        
        # Copiar solo el contenido dentro de la máscara
        result[mask == 255] = roi[mask == 255]
        
        # Guardar
        lot_filename = os.path.join(output_dir, f"lote_{count+1:03d}.png")
        cv2.imwrite(lot_filename, result)
        
        # Dibujar en imagen de debug
        cv2.drawContours(debug_img, [cnt], -1, (0, 255, 0), 2)
        # Centro para poner texto
        M = cv2.moments(cnt)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            cv2.putText(debug_img, str(count+1), (cX, cY), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        count += 1

    # Guardar imagen de debug
    cv2.imwrite(os.path.join(output_dir, "debug_detected_lots.jpg"), debug_img)
    print(f"Procesamiento completado. Se extrajeron {count} lotes en '{output_dir}'.")
    print(f"Revise 'debug_detected_lots.jpg' para ver qué se detectó.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extractor de lotes catastrales")
    parser.add_argument("imagen", help="Ruta a la imagen del plano")
    parser.add_argument("--out", default="lotes_extraidos", help="Directorio de salida")
    parser.add_argument("--min_area", type=int, default=5000, help="Área mínima del lote")
    parser.add_argument("--dilation", type=int, default=5, help="Iteraciones de dilatación de la máscara (aumentar si se cortan números)")
    parser.add_argument("--epsilon", type=float, default=0.001, help="Factor de simplificación de contornos (menor = más detalle)")
    parser.add_argument("--min_line_area", type=int, default=100, help="Área mínima de una línea para ser considerada pared (filtra texto)")
    parser.add_argument("--closing_kernel", type=int, default=25, help="Tamaño del kernel para cerrar huecos (texto pegado a paredes)")
    parser.add_argument("--reconnect_iter", type=int, default=2, help="Iteraciones para reconectar líneas rotas")
    parser.add_argument("--reconnect_kernel", type=int, default=3, help="Tamaño kernel para reconectar líneas rotas")
    
    args = parser.parse_args()
    
    process_cadastral_map(args.imagen, args.out, min_area=args.min_area, dilation_iter=args.dilation, epsilon_factor=args.epsilon, min_line_area=args.min_line_area, closing_kernel_size=args.closing_kernel, reconnect_lines_iter=args.reconnect_iter, reconnect_kernel_size=args.reconnect_kernel)
