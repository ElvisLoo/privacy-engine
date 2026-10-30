# -*- coding: utf-8 -*-
"""
轻量设置持久化。

防窥工具的典型用法是「打开、拨到合适强度、开始工作」。每次启动都要
重新拨一遍强度、重新选模式，用两天就会烦。

设计取舍：
  - 配置文件放用户目录，不放程序目录（程序可能装在 Program Files，
    没有写权限，静默失败会让用户以为"存了但其实没存"）；
  - 任何异常都不抛：配置坏了就用默认值，工具必须能起来 ——
    防窥工具起不来的代价比忘记强度大得多；
  - 数值一律夹到合法区间：手改出来的 intensity 999 会让遮罩完全变黑。
"""

import json
import os

DEFAULTS = {
    "intensity": 50,       # 0-100，遮罩强度百分比
    "mode": "none",        # none / circle / three_zone
    "window_x": None,      # 主窗口位置，None 表示居中
    "window_y": None,
}

_LIMITS = {
    "intensity": (0, 100),
}


def config_path():
    """配置路径：用户目录下的 .privacy_engine/config.json"""
    base = os.path.expanduser("~")
    return os.path.join(base, ".privacy_engine", "config.json")


def _clamp_int(value, lo, hi, default):
    """只接受整数（或可转成整数的字符串），越界夹紧，非法回默认。"""
    if isinstance(value, bool):
        # bool 是 int 的子类，True 会变成 1，这不是用户想要的意思
        return default
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def sanitize(raw):
    """把任意输入洗成合法配置。未知字段全部丢弃。"""
    out = dict(DEFAULTS)
    if not isinstance(raw, dict):
        return out

    for key, (lo, hi) in _LIMITS.items():
        out[key] = _clamp_int(raw.get(key, DEFAULTS[key]), lo, hi, DEFAULTS[key])

    mode = raw.get("mode")
    if mode in ("none", "circle", "three_zone"):
        out["mode"] = mode

    for key in ("window_x", "window_y"):
        v = raw.get(key)
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)) and -100000 < v < 100000:
            out[key] = int(v)
    return out


def load():
    """读取配置。文件不存在或损坏都返回默认值。"""
    path = config_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return sanitize(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return dict(DEFAULTS)


def save(data):
    """
    保存配置。返回 (ok, error)。
    写临时文件再替换，避免写一半断电留下坏 JSON —— 坏 JSON 会让下次启动
    静默回到默认值，用户完全不知道自己的设置丢了。
    """
    path = config_path()
    tmp = path + ".tmp"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = sanitize(data)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True, None
    except OSError as e:
        return False, str(e)
