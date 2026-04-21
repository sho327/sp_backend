### 1. 前提条件
---
- `mise`がインストール済みであること  
https://mise.jdx.dev/


### 2. 起動方法
---
#### `A. 初回の実行時`
#### 2-A-1. miseインストールの実行
mise設定に沿って開発環境の構築を行います。  
※mise設定に沿って指定バージョンの`uv`・`node.js`がインストールされます
```terminal:terminal
mise install
```

#### 2-A-2. マイグレーションの実行
一括マイグレーションだと参照関係でエラーが出るので、エンティティ毎にマイグレーションファイル生成コマンドを実行します。
```terminal:terminal
python manage.py makemigrations artist
python manage.py makemigrations playlist
python manage.py makemigrations account
python manage.py makemigrations common
```

次に「manage.py」が存在する、「src」フォルダ配下で以下を実行します  
(または手動で該当パスのファイルを削除してください)
```terminal:terminal
rm apps/account/migrations/0001_initial.py
rm apps/common/migrations/0001_initial.py
```

参照関係解決の為に再度以下マイグレーションファイル生成コマンドを通します。
```terminal:terminal
python manage.py makemigrations account
python manage.py makemigrations common
```

こちらでマイグレーション定義が整うので以下コマンドにてマイグレーションを実行します。
```terminal:terminal
python manage.py migrate
```

これでいけるかも↓↓
python manage.py makemigrations
python manage.py migrate

#### `B. 初回/初回以降の実行時`
#### 2-B-1. フロントエンド起動
miseにてインストール済みのNode.jsを使用してフロントエンドサーバを起動します。
```terminal:terminal
npm run dev
```

#### 2-B-2. バックエンド起動
miseにてインストール済みのuvを使用してバックエンドサーバを起動します。
```terminal:terminal
uv run ./src/manage.py runserver 0.0.0.0:8787
```
