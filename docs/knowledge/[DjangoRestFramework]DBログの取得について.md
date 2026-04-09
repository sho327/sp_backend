Django/DRFのSQLログをまとめて取得する方法

---

結論

DjangoのSQLを確実に取得したいのであれば、connection.execute_wrapper()を利用するのが良い。
ViewSetのcreate/update/listなどで動いたSQLをすべてキャプチャできる。

---

1. QueryLogger — SQL を貯めるロガーの設定

```python
from django.db import connection

class QueryLogger:
def **init**(self):
self.queries = []

    def __call__(self, execute, sql, params, many, context):
        self.queries.append({"sql": sql, "params": params})
        return execute(sql, params, many, context)
```

---

2. record_sql — 任意の関数を丸ごとSQLロギングするデコレータ

```python
def record_sql(func):
from django.db import connection

    class QueryLogger:
        def __init__(self):
            self.queries = []

        def __call__(self, execute, sql, params, many, context):
            self.queries.append((sql, params))
            return execute(sql, params, many, context)

    def wrapper(*args, **kwargs):
        logger = QueryLogger()
        with connection.execute_wrapper(logger):
            result = func(*args, **kwargs)

        print("=== Executed SQL ===")
        for sql, params in logger.queries:
            print(sql, params)

        return result

    return wrapper
```

使い方：

```python
@record_sql
def some_process():
User.objects.get(id=1)
Project.objects.filter(status=1).first()
```

→ @record_sqlで指定された関数中のSQLがすべて出力される。

---

3. ViewSetのcreate()を囲んでSQLを取る方法

```python
class UserViewSet(ModelViewSet):

    def create(self, request, *args, **kwargs):
        logger = QueryLogger()
        with connection.execute_wrapper(logger):
            response = super().create(request, *args, **kwargs)

        print("========== SQL LOG ==========")
        for q in logger.queries:
            print(q["sql"], q["params"])

        return response
```

✔ この設定で捕捉できるもの
• serializer.is_valid()内のSELECT
• serializer.save()のINSERT/UPDATE
• 外部キーチェックのSELECT
• signalsのSQL
• create内のORMすべて

---

4. すべてのViewSetにSQLログを自動適用するMixin

```python
class SQLLogMixin:
def \_log_sql(self, func, *args, \*\*kwargs):
logger = QueryLogger()
with connection.execute_wrapper(logger):
response = func(*args, \*\*kwargs)

        print(f"========== SQL LOG for {func.__name__} ==========")
        for q in logger.queries:
            print(q["sql"], q["params"])

        return response

    def create(self, request, *args, **kwargs):
        return self._log_sql(super().create, request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return self._log_sql(super().update, request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        return self._log_sql(super().list, request, *args, **kwargs)
```

利用例：

```python
class UserViewSet(SQLLogMixin, ModelViewSet):
queryset = User.objects.all()
serializer_class = UserSerializer
```

---

5. 「first()の時のSQL」について

✔ SQL 文を見たい(実行前)

```python
qs = instance.m_user_status_set.order_by("id")[:1]
print(qs.query)
```

→ 0件でも安全にSQL表示。

✔ 実行されたSQLを見たい

```python
with connection.execute_wrapper(logger):
result = qs.first()
```

→ 0件でもNoneになるだけでSQLは確実にキャプチャ。

---

6. 捕捉できない部分(注意点)

場所 結果(補足可能か)
ViewSet内(create/update/list)   => ✔その中でwrapperが生きている
serializer/signals              => ✔create()内で動く
認証処理(Authentication classes) => ✗ ViewSet より前で実行される
Middleware                      => ✗ ViewSetの外側

→ 認証やmiddlewareのSQLを取りたい時は、
そちら側でもexecute_wrapperを使う必要がある。

---

まとめ

目的 ベストな方法
関数単位でSQLをまとめて取りたい       => record_sqlデコレータ
ViewSetのSQLを全部捕捉したい         => execute_wrapper()でcreate/update/listを囲む
全ViewSetに適用したい                => SQLLogMixin
実行されたSQLを確実にキャプチャしたい  => execute_wrapper
実行前のSQL文を見たい                 => qs.query

---
