import io
import base64
import numpy as np
import matplotlib

matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from typing import Dict, Any, Optional


def generate_preview_image(
        results: Dict[str, Any],
        molecule: str,
        width: int = 300,
        height: int = 200,
        dpi: int = 100
) -> Optional[str]:
    """
    Генерирует превью графика в формате base64 PNG

    Returns:
        Base64-encoded PNG string или None при ошибке
    """
    try:
        # Извлечь данные
        distances = []
        vqe_energies = []

        for dist_str, result in results.items():
            if isinstance(result, dict) and "error" not in result:
                distances.append(float(dist_str))
                vqe_energies.append(result["vqe"])

        if len(distances) < 2:
            return None

        # Сортировка
        sorted_indices = np.argsort(distances)
        distances = np.array(distances)[sorted_indices]
        vqe_energies = np.array(vqe_energies)[sorted_indices]

        # Создать график
        fig, ax = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)
        ax.plot(distances, vqe_energies, 'b-', linewidth=1.5)
        ax.set_xlabel('Distance (Å)', fontsize=8)
        ax.set_ylabel('Energy (Ha)', fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.3)

        # Убрать лишние отступы
        plt.tight_layout(pad=0.5)

        # Сохранить в буфер
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)

        # Конвертировать в base64
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        return f"data:image/png;base64,{image_base64}"

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to generate preview: {e}")
        return None
