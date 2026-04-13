import os
import random
import string
from typing import Any, Dict, List, Optional, Union

# 汎用的なヘルパー関数やデータクレンジング処理を定義する。
# 利用例: フォーム入力値のNull/空白チェック


def set_str_or_blank_format(pStr: Optional[str]) -> str:
    """
    文字列型に対するフォーマット。対象値がNoneまたはNoneでない場合に空文字列を設定する。
    """
    if isinstance(pStr, str):
        return pStr
    else:
        # pStrがNoneの場合に空文字列を返す。
        return "" if pStr is None else str(pStr)


def set_str_or_none_format(pStr: Optional[str]) -> Optional[str]:
    """
    文字列型に対するフォーマット。対象値がNoneの場合にそのままNone設定。
    """
    if isinstance(pStr, str):
        return pStr
    else:
        # Noneでない場合は文字列化を試みる
        return None if pStr is None else str(pStr)


def set_int_format(pInt: Optional[Union[int, str]]) -> Optional[int]:
    """
    数値型に対するフォーマット。対象値がNoneの場合にそのままNone設定。
    文字列を数値に変換する処理も行う。
    """
    if pInt is None:
        return None

    try:
        return int(pInt)
    except (ValueError, TypeError):
        # 変換できない場合はNoneを返す
        return None


def clean_input_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    辞書内の文字列データから前後の空白文字を削除し、データの前処理を行う。
    """
    cleaned_data = {}
    for key, value in data.items():
        if isinstance(value, str):
            cleaned_data[key] = value.strip()
        else:
            cleaned_data[key] = value
    return cleaned_data


def dedupe_keep_order(values: List[str]) -> List[str]:
    """
    入力:
    - values: 重複を含む可能性のある文字列配列
    出力:
    - 重複を除去しつつ、元順序を維持した配列
    副作用:
    - なし(純粋関数)
    """
    return list(dict.fromkeys([v for v in values if v]))


def take(values: List[str], n: int) -> List[str]:
    """
    入力:
    - values: 取得元配列 または イテレータ
    - n: 取得件数(0未満は0扱い)
    出力:
    - 先頭から最大n件の配列
    副作用:
    - なし(純粋関数)
    """
    return list(islice(values, max(0, n)))
