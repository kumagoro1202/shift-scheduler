# Scripts ディレクトリ

このディレクトリには、データベースのセットアップやビルド関連のスクリプトが含まれています。

## スクリプト一覧

### init_test_data.py

実際のシフトCSVファイルからテストデータを生成し、データベースに投入します。

```powershell
# 使用方法
python scripts/init_test_data.py --force

# CSVファイルを指定する場合
python scripts/init_test_data.py --csv report/other_shift.csv --force
```

**重要**: 
- `report/*.csv`は個人情報を含むため、Git管理対象外です（.gitignoreで除外）
- このスクリプトはビルド時にも自動実行されます（build.spec参照）
- 配布パッケージには実データベースが含まれます

### setup_database.py

データベーススキーマの初期化と、マスタデータ（就業パターン、診療時間スロット）のセットアップを行います。

```powershell
# 使用方法
python scripts/setup_database.py --force
```

### build.spec

PyInstallerのビルド設定ファイルです。ビルド時に`init_test_data.py`を自動実行し、
最新のテストデータをパッケージに含めます。

```powershell
# ビルド実行
pyinstaller scripts/build.spec
```

### launcher.py

PyInstallerでビルドされた実行ファイル用のランチャーです。
Streamlitアプリケーションを起動します。

## セキュリティ注意事項

- `report/`ディレクトリに配置するCSVファイルは個人情報を含む可能性があります
- これらのファイルは`.gitignore`で除外されており、Gitリポジトリにコミットされません
- ただし、ビルドされた配布パッケージにはデータベース経由でテストデータが含まれます
- 配布時は個人情報の取り扱いに十分注意してください
