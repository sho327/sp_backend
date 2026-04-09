from enum import Enum
from typing import Type, List, Any, Union

def enum_contains(enum_class: Type[Enum], item: Union[str, int, Any]) -> bool:
    """
    Enum にキーまたは値が含まれているかを判定する共通関数
    - enum_class: Enum クラス
    - item: キー名(str) または 値(int/str/その他)
    """
    # キー判定（名前一致）
    if isinstance(item, str) and item in enum_class.__members__:
        return True

    # 値判定
    if item in [e.value for e in enum_class]:
        return True

    return False

def enum_keys(enum_class: Type[Enum]) -> List[str]:
    """
    Enum のキー一覧を返す
    """
    return list(enum_class.__members__.keys())


def enum_values(enum_class: Type[Enum]) -> List[Any]:
    """
    Enum の値一覧を返す
    """
    return [e.value for e in enum_class]

# ==== 使用例(※IntEnumでも使用可能※) ====
# class PushType(Enum):
#     MESSAGE = '1'
#     REQUEST = '2'
#     SURVEY  = '3'

# print(enum_contains(PushType, "MESSAGE"))  # True（キー判定）
# print(enum_contains(PushType, "2"))        # True（値判定）
# print(enum_keys(PushType))   # ['MESSAGE', 'REQUEST', 'SURVEY']
# print(enum_values(PushType)) # ['1', '2', '3']