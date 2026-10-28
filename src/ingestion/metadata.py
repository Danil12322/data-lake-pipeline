from pathlib import Path

import pandas as pd

from src.config import METADATA_PATH, PROJECT_ROOT, SOURCE_DIR

METADATA_COLUMNS = [
    "file_name",
    "hash",
    "version",
    "ingested_at",
    "file_size",
    "raw_path",
    "processed_at",
]


def load_metadata() -> pd.DataFrame:
    if not METADATA_PATH.exists():
        return pd.DataFrame(columns=METADATA_COLUMNS)
    df = pd.read_csv(METADATA_PATH)
    if "processed_at" not in df.columns:
        df["processed_at"] = None
    df["processed_at"] = df["processed_at"].astype("object")
    return df


def save_metadata(df: pd.DataFrame) -> None:
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(METADATA_PATH, index=False)


def latest_versions() -> dict[str, Path]:
    """Последняя версия каждого файла (независимо от processed_at)."""
    meta = load_metadata()
    if meta.empty:
        return {}

    latest = meta.sort_values("version").groupby("file_name").tail(1)

    result: dict[str, Path] = {}
    for _, row in latest.iterrows():
        file_stem = Path(row["file_name"]).stem
        result[file_stem] = PROJECT_ROOT / row["raw_path"]
    return result


def unprocessed_versions() -> list[dict]:
    """
    Версии, которые ещё не попали в Bronze (processed_at IS NULL).

    Возвращает список dict с полями:
    - file_stem: имя файла без расширения (M000001_1005-02)
    - raw_path: Path к файлу .000
    - row_index: индекс строки в metadata (для последующего UPDATE)
    """
    meta = load_metadata()
    if meta.empty:
        return []

    pending = meta[meta["processed_at"].isna()].copy()
    if pending.empty:
        return []

    result = []
    for idx, row in pending.iterrows():
        result.append(
            {
                "file_stem": Path(row["file_name"]).stem,
                "raw_path": PROJECT_ROOT / row["raw_path"],
                "row_index": idx,
            }
        )
    return result


def mark_processed(row_indices: list[int]) -> None:
    """Помечает версии как обработанные (processed_at = now)."""
    if not row_indices:
        return

    meta = load_metadata()

    # Принудительно приводим колонку к object, чтобы можно было писать строки
    meta["processed_at"] = meta["processed_at"].astype("object")

    now = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    meta.loc[row_indices, "processed_at"] = now

    save_metadata(meta)


def source_files_count() -> int:
    """Считает все файлы с цифровым расширением (.000, .051, .055 и т.д.)."""
    return sum(
        1 for p in SOURCE_DIR.rglob("*")
        if p.is_file() and p.suffix.startswith(".") and p.suffix[1:].isdigit()
    )