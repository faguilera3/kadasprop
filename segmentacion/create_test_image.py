import cv2
import numpy as np
import os

def create_test_image(filename="test_map.png"):
    # Crear una imagen blanca de 1000x1000
    h, w = 1000, 1000
    img = np.ones((h, w, 3), dtype=np.uint8) * 255
    
    # Dibujar líneas negras (simulando calles/división de lotes)
    color = (0, 0, 0)
    thickness = 2
    
    # Dibujar una cuadrícula básica
    # Verticales
    cv2.line(img, (200, 100), (200, 900), color, thickness)
    cv2.line(img, (400, 100), (400, 900), color, thickness)
    cv2.line(img, (600, 100), (600, 900), color, thickness)
    cv2.line(img, (800, 100), (800, 900), color, thickness)
    
    # Horizontales
    cv2.line(img, (100, 200), (900, 200), color, thickness)
    cv2.line(img, (100, 400), (900, 400), color, thickness)
    cv2.line(img, (100, 600), (900, 600), color, thickness)
    cv2.line(img, (100, 800), (900, 800), color, thickness)
    
    # Dibujar un lote irregular (polígono)
    pts = np.array([[250, 250], [350, 220], [380, 300], [280, 350]], np.int32)
    pts = pts.reshape((-1, 1, 2))
    cv2.polylines(img, [pts], True, color, thickness)
    
    # Dibujar texto dentro de un lote (simular números de parcela)
    cv2.putText(img, "123", (250, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    
    # Guardar
    cv2.imwrite(filename, img)
    print(f"Imagen de prueba creada: {filename}")

if __name__ == "__main__":
    create_test_image()
