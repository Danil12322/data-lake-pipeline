from pathlib import Path
import duckdb
import matplotlib
import os
import pandas as pd
import numpy as np

if os.environ.get("CI"):
    matplotlib.use('Agg')

import matplotlib.pyplot as plt
import matplotlib.patches as patches

from src.logger import logger

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SILVER_PATH = PROJECT_ROOT / "data" / "silver" / "defects_clean.parquet"

def extract_sample_test_plan(lines, start_idx=0):
    """Извлекает список кадров, которые сканер посетил."""
    for i in range(start_idx, len(lines)):
        if lines[i].startswith("SampleTestPlan"):
            # Количество кадров (не используем, но полезно)
            count = int(lines[i].split()[1])
            plan = []
            j = i + 1
            while j < len(lines) and not lines[j].startswith("AreaPerTest"):
                parts = lines[j].strip().split()
                if len(parts) >= 2:
                    try:
                        x = int(parts[0])
                        y = int(parts[1])
                        plan.append((x, y))
                    except ValueError:
                        break
                j += 1
            return plan
    return []



def draw_klarity_style_map(inspection_run_id: str):
    if not SILVER_PATH.exists():
        logger.error("Silver layer not found.")
        return

    con = duckdb.connect()
    df = con.execute(f"""
        SELECT x_rel, y_rel, x_index, y_index, die_pitch_x, die_pitch_y, sample_center_x, sample_center_y
        FROM '{SILVER_PATH}'
        WHERE inspection_run_id = '{inspection_run_id}'
    """).df()

    if df.empty:
        logger.warning(f"No defects found for run: {inspection_run_id}")
        return

    logger.info(f"Drawing map for {inspection_run_id} ({len(df)} defects)...")

    # 1. Параметры
    pitch_x = df["die_pitch_x"].iloc[0] or 10000.0
    pitch_y = df["die_pitch_y"].iloc[0] or 10000.0
    cx = df["sample_center_x"].iloc[0]
    cy = df["sample_center_y"].iloc[0]

    if cx is None or np.isnan(cx):
        cx = (df["x_index"].median() * pitch_x)
    if cy is None or np.isnan(cy):
        cy = (df["y_index"].median() * pitch_y)

    # 2. Абсолютные координаты дефектов
    df["x_abs"] = (df["x_index"] * pitch_x) + df["x_rel"]
    df["y_abs"] = (df["y_index"] * pitch_y) + df["y_rel"]

    # 3. Сдвиг к центру пластины
    df["x_wafer"] = df["x_abs"] - cx
    df["y_wafer"] = df["y_abs"] - cy

    # 4. Радиус
    radius = 100000.0

    fig, ax = plt.subplots(figsize=(10, 10))

    # 5. Серый круг
    wafer_bg = patches.Circle((0, 0), radius, color='#888888', zorder=0)
    ax.add_patch(wafer_bg)

    # 6. Получаем УНИКАЛЬНЫЕ индексы кадров, где есть дефекты
    plan_path = PROJECT_ROOT / "data" / "bronze" / "test_plan.parquet"
    scanned_dies = set()

    lot_id, wafer_id = inspection_run_id.rsplit("-", 1)

    if plan_path.exists():
        plan_df = pd.read_parquet(plan_path)
        wafer_id_clean = wafer_id.replace("@", "")
        plan_df["wafer_id_clean"] = plan_df["wafer_id"].astype(str).str.replace("@", "")

        plan_filtered = plan_df[
            (plan_df["lot_id"] == lot_id) & (plan_df["wafer_id_clean"] == wafer_id_clean)
            ]

        # Проверяем, является ли план "полным сканированием" (один кадр 0,0)
        is_full_wafer_scan = (
                len(plan_filtered) == 1
                and plan_filtered.iloc[0]["x_index"] == 0
                and plan_filtered.iloc[0]["y_index"] == 0
        )

        if not is_full_wafer_scan and not plan_filtered.empty:
            # Рисуем все кадры из плана
            scanned_dies = set(zip(plan_filtered["x_index"], plan_filtered["y_index"]))
        elif is_full_wafer_scan:
            # Не рисуем кадры (полное сканирование)
            scanned_dies = set()
        else:
            # Fallback: кадры с дефектами
            scanned_dies = set(zip(df["x_index"], df["y_index"]))

    # 7. Рисуем белые квадраты ТОЛЬКО для этих кадров
    for xi, yi in scanned_dies:
        x_pos = (xi * pitch_x) - cx
        y_pos = (yi * pitch_y) - cy

        # Центр кадра
        center_x = x_pos + pitch_x / 2
        center_y = y_pos + pitch_y / 2

        # Проверяем, что кадр внутри пластины (с отступом 6 мм)
        if np.sqrt(center_x ** 2 + center_y ** 2) <= (radius - 6000):
            rect = patches.Rectangle(
                (x_pos, y_pos), pitch_x, pitch_y,
                linewidth=0.5, edgecolor='lightgray', facecolor='white', zorder=2
            )
            rect.set_clip_path(wafer_bg)
            ax.add_patch(rect)

    # 8. Вырез (Notch)
    notch_width = radius * 0.05
    notch = patches.Polygon([
        [-notch_width, -radius],
        [notch_width, -radius],
        [0, -radius + notch_width]
    ], closed=True, color='#888888', zorder=4)
    ax.add_patch(notch)

    # 9. Дефекты
    ax.scatter(
        df["x_wafer"],
        df["y_wafer"],
        s=10,
        c='black',
        alpha=0.9,
        zorder=5
    )

    # 10. Настройки
    ax.set_xlim([-radius, radius])
    ax.set_ylim([-radius, radius])
    ax.set_aspect('equal')
    ax.set_facecolor('white')
    ax.set_title(f'Wafer Defect Map: {inspection_run_id}', fontsize=14)
    ax.grid(False)

    plt.tight_layout()

    output_path = PROJECT_ROOT / "data" / "gold" / f"wafer_map_{inspection_run_id.replace('@', '').replace('-', '_')}.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300)
    logger.info(f"Map saved to: {output_path}")

    if not os.environ.get("CI"):
        plt.show()

    plt.close(fig)


if __name__ == "__main__":
    draw_klarity_style_map("M000001_1015-03")