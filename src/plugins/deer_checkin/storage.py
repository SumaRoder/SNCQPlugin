from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT_DIR / "data"


def get_user_dir(account_id: int | str, group_id: int | str, uin: int | str) -> Path:
    return DATA_DIR / str(group_id) / str(uin)


def load_user_data(user_dir: Path) -> Dict:
    user_dir.mkdir(parents=True, exist_ok=True)
    data_file_path = user_dir / "deer_check_in.json"
    if data_file_path.exists() and data_file_path.stat().st_size > 0:
        try:
            with open(data_file_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            return {}
    return {}


def save_user_data(user_dir: Path, data: Dict) -> None:
    user_dir.mkdir(parents=True, exist_ok=True)
    data_file_path = user_dir / "deer_check_in.json"
    with open(data_file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def list_member_dirs(account_id: int | str, group_id: int | str) -> list[Path]:
    base = DATA_DIR / str(group_id)
    if not base.exists():
        return []
    return [p for p in base.iterdir() if p.is_dir()]
