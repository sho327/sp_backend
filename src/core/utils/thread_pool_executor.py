import atexit
from concurrent.futures import ThreadPoolExecutor

# アプリ全体で使い回すスレッドプール
# この変数をインポートして使用して使用する仕組みとすることでプロセス起動時に最初に1つだけ生成され、同じワーカー内の全Viewで使いまわせる
executor = ThreadPoolExecutor(max_workers=3)


def shutdown_executor():
    executor.shutdown(wait=True)
    print("[Global] ThreadPoolExecutor has been shut down.")


# atexitもモジュールインポート(このexecutor.pyが最初にimportされたとき)に1回だけ登録される
# ※但し、atexitが呼ばれるのはPythonプロセスが正常終了するときだけ(落ちた場合には呼ばれない)
# 同期処理での時も同じだが、ファイルのロック等を行っていた場合、ロックが残ってしまうのでそこだけ考慮が必要
# (DB読込等はDB側でロールバックしてくれる、WebPushもロック等はなく不具合時の分だけ送れなくなるのみの影響を想定)
atexit.register(shutdown_executor)
