"""
Copia o modelo Live2D de Downloads para assets/live2d/kuri_model
com nomes ASCII e mapeamento de emoções da Kuri.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path(r"C:\Users\zigifrid\Downloads\简__1_")
TARGET_ROOT = PROJECT_ROOT / "assets" / "live2d" / "kuri_model"

RENAME_MAP = {
    "简.moc3": "kuri.moc3",
    "简.physics3.json": "kuri.physics3.json",
    "简.cdi3.json": "kuri.cdi3.json",
    "简.png": "kuri.png",
    "简.vtube.json": "kuri.vtube.json",
    "简.8192": "textures",
    "脸红.exp3.json": "expr_blushing.exp3.json",
    "生气.exp3.json": "expr_angry.exp3.json",
    "星星眼.exp3.json": "expr_surprised.exp3.json",
    "脸黑.exp3.json": "expr_cool.exp3.json",
    "爱心眼.exp3.json": "expr_love.exp3.json",
    "白眼.exp3.json": "expr_eyeroll.exp3.json",
    "泪.exp3.json": "expr_tears.exp3.json",
    "血.exp3.json": "expr_blood.exp3.json",
    "右手.exp3.json": "expr_hand_right.exp3.json",
    "左手.exp3.json": "expr_hand_left.exp3.json",
    "Scene1.motion3.json": "idle.motion3.json",
}

EXPRESSIONS = [
    {"Name": "blushing", "File": "expr_blushing.exp3.json"},
    {"Name": "angry", "File": "expr_angry.exp3.json"},
    {"Name": "surprised", "File": "expr_surprised.exp3.json"},
    {"Name": "cool", "File": "expr_cool.exp3.json"},
    {"Name": "love", "File": "expr_love.exp3.json"},
    {"Name": "eyeroll", "File": "expr_eyeroll.exp3.json"},
    {"Name": "tears", "File": "expr_tears.exp3.json"},
]

EMOTION_MAP = {
    "neutral": None,
    "cool": "cool",
    "surprised": "surprised",
    "blushing": "blushing",
    "angry": "angry",
}

MOTIONS = [
    {"File": "idle.motion3.json", "FadeInTime": 0.5, "FadeOutTime": 0.5},
]


def find_source_dir() -> Path:
    if not SOURCE_ROOT.exists():
        raise FileNotFoundError(f"Modelo não encontrado: {SOURCE_ROOT}")
    for child in SOURCE_ROOT.iterdir():
        if child.is_dir() and (child / "简.model3.json").exists():
            return child
    raise FileNotFoundError("Pasta do modelo (简) não encontrada em Downloads")


def copy_model() -> None:
    source_dir = find_source_dir()
    if TARGET_ROOT.exists():
        shutil.rmtree(TARGET_ROOT)
    TARGET_ROOT.mkdir(parents=True, exist_ok=True)

    for src_name, dst_name in RENAME_MAP.items():
        src = source_dir / src_name
        dst = TARGET_ROOT / dst_name
        if not src.exists():
            print(f"[skip] {src_name}")
            continue
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        print(f"[copy] {src_name} -> {dst_name}")

    model3 = {
        "Version": 3,
        "FileReferences": {
            "Moc": "kuri.moc3",
            "Textures": ["textures/texture_00.png"],
            "Physics": "kuri.physics3.json",
            "DisplayInfo": "kuri.cdi3.json",
            "Expressions": EXPRESSIONS,
            "Motions": {"Idle": MOTIONS},
        },
        "Groups": [
            {"Target": "Parameter", "Name": "LipSync", "Ids": ["ParamMouthOpenY"]},
            {"Target": "Parameter", "Name": "EyeBlink", "Ids": ["ParamEyeLOpen", "ParamEyeROpen"]},
        ],
    }

    model_path = TARGET_ROOT / "kuri.model3.json"
    model_path.write_text(json.dumps(model3, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[write] {model_path.name}")

    emotion_path = TARGET_ROOT / "emotion_map.json"
    emotion_path.write_text(
        json.dumps(EMOTION_MAP, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"[write] {emotion_path.name}")

    viewport_path = PROJECT_ROOT / "assets" / "live2d" / "kuri_model" / "viewport_config.json"
    if not viewport_path.exists():
        viewport_path.write_text(
            json.dumps(
                {
                    "framing": {
                        "min_height": 72,
                        "max_height": 520,
                        "scale": {"min": 3.0, "max": 1.9},
                        "offset_x": {"min": 0.0, "max": 0.0},
                        "offset_y": {"min": -2.5, "max": -1.2},
                        "curve_power": 3.0,
                    }
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    readme = TARGET_ROOT / "README.txt"
    readme.write_text(
        "Modelo Live2D preparado para o projeto Kuri.\n"
        "Arquivo principal: kuri.model3.json\n"
        "Mapeamento de emoções: emotion_map.json\n"
        "Enquadramento do avatar: viewport_config.json\n",
        encoding="utf-8",
    )
    print(f"[done] Modelo pronto em {TARGET_ROOT}")


if __name__ == "__main__":
    copy_model()