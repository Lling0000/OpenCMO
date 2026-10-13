<div align="center">
  <img src="assets/logo.png" alt="OpenCMO" width="80" />
  <h1>OpenCMO</h1>
  <p><strong>オープンソースの AI グロースワークスペース。</strong></p>
  <p>プロダクトがどこで見つけられ、何が語られているかを把握し、<br />次に取り組むべき成長施策を見極めます。</p>
  <p>
    <a href="README.md">English</a> · <a href="README_zh.md">中文</a> · <a href="README_ja.md">日本語</a> · <a href="README_ko.md">한국어</a> · <a href="README_es.md">Español</a>
  </p>
  <p>
    <a href="https://github.com/Lling0000/OpenCMO/actions/workflows/ci.yml"><img src="https://github.com/Lling0000/OpenCMO/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&amp;logoColor=white" alt="Python 3.10+" />
    <img src="https://img.shields.io/badge/React-19-149ECA?logo=react&amp;logoColor=white" alt="React 19" />
    <img src="https://img.shields.io/badge/Models-BYOK-7C3AED" alt="自分のモデル API キーを利用" />
  </p>
  <p><a href="#opencmo-でできること">概要</a> · <a href="#クイックスタート">クイックスタート</a> · <a href="docs/rag.md">ナレッジと RAG</a> · <a href="docs/configuration.md">設定</a></p>
</div>

<p align="center">
  <img src="assets/readme-overview.svg" alt="OpenCMO のワークフロー：プロジェクト、モニタリング、共有コンテキスト、AI 分析、人によるレビュー" width="100%" />
</p>

## OpenCMO でできること

OpenCMO は、創業者、オープンソースのメンテナー、小規模なプロダクトチーム向けの、セルフホスト型 AI CMO（最高マーケティング責任者）です。検索での可視性、コミュニティの会話、競合調査、自社の資料を、一つのプロジェクトワークスペースにまとめます。

プロダクトの URL から始められます。OpenCMO はプロジェクトのコンテキストを構築し、シグナルを収集します。専門エージェントがそれらをレポート、コンテンツの下書き、優先順位付きの提案に変換します。定期スキャンで変化を追跡でき、承認キューを通じて公開の判断を自分で行えます。

| 機能 | できること |
| --- | --- |
| **SEO と検索順位** | サイトの技術的な健全性を監査し、AI クローラーのアクセス可否を確認し、キーワード順位の推移を追跡します。 |
| **AI 検索での可視性（GEO）** | 対応する AI プロバイダーを通じてブランドへの言及や引用を調べます。対象範囲は設定済みの連携によって異なります。 |
| **コミュニティと競合** | 関連する会話を見つけ、言及を追跡し、ナレッジグラフで競合、キーワード、会話の関係を調べます。 |
| **ナレッジライブラリ（RAG）** | 資料や過去のレポートを検索し、チャット、レポート、下書きに出典を付けて活用します。 |
| **レポートと AI チャット** | 戦略レポートや週次サマリー、Human Readout と Agent Brief を生成し、プロジェクトを理解したエージェントと結果を議論します。 |
| **コンテンツと承認** | コンテンツやアウトリーチの下書きを作成し、提案されたアクションを確認して、準備が整ったら対応する公開連携を有効にします。 |

**自分のモデルを利用できます。** OpenAI または OpenAI 互換のエンドポイント、ツール呼び出しに対応したモデル、API キーを設定します。検索、コミュニティ、公開の連携は、必要に応じて追加できます。

プラットフォームの認証情報と `OPENCMO_AUTO_PUBLISH=1` を設定すると、Reddit と Twitter/X への直接公開を利用できます。その他のアウトリーチは、レビュー用の下書きとして保存されます。

## 一つの URL から実行計画へ

1. **コンテキストを構築** — プロダクトの URL をクロールし、ブランド、カテゴリ、キーワード、競合を分析します。
2. **シグナルを収集** — 利用可能なプロバイダーを通じて、SEO、AI 検索、キーワード順位、コミュニティのデータを集めます。
3. **結果をまとめて確認** — 結果を正規化し、専門エージェントが各領域を分析して優先順位を整理します。
4. **成果物を作成** — 調査結果を保存し、レポートやブリーフを生成して、レビュー対象のアクションを準備します。
5. **継続的にモニタリング** — 日次、週次、月次のスキャンを設定し、新しい結果を過去の実行結果と比較します。

モニタリングパイプラインは、コンテキスト構築 → シグナル収集 → 正規化 → 領域別レビュー → 戦略の統合 → 永続化の 6 段階です。レポート、チャット、下書きでプロジェクトのコンテキストを再利用するため、毎回プロダクトを説明する必要はありません。

## クイックスタート

### Docker Compose

Docker は Web インターフェースとバックエンドをまとめてビルドします。Compose を含む Docker をインストールし、次を実行します。

```bash
git clone https://github.com/Lling0000/OpenCMO.git
cd OpenCMO
cp .env.example .env
```

`.env` を編集し、`OPENAI_API_KEY` にモデルプロバイダーのキーを設定します。互換プロバイダーを使う場合は、`OPENAI_BASE_URL` と `OPENCMO_MODEL_DEFAULT` も設定してください。[設定ガイド](docs/configuration.md)に例があります。

```bash
docker compose up -d --build
```

**[http://localhost:8080](http://localhost:8080)** を開き、URL からプロジェクトを作成して最初のスキャンを実行します。モデル設定は Web インターフェースからも変更できます。

<details>
<summary><strong>ソースから実行</strong> — Python 3.10+ と Node.js 20+</summary>

```bash
git clone https://github.com/Lling0000/OpenCMO.git
cd OpenCMO
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
crawl4ai-setup
cp .env.example .env
```

`.env` にモデルの API キーを設定し、フロントエンドをビルドしてサーバーを起動します。

```bash
cd frontend
npm ci
npm run build
cd ..
opencmo-web
```

`http://localhost:8080` を開きます。Web インターフェースを使うには、フロントエンドのビルドが必要です。

</details>

### 最初のプロジェクト

- プロダクトまたはリポジトリの URL を追加し、検出されたプロジェクトのコンテキストを確認します。
- スキャンを実行し、検索、コミュニティ、競合の調査結果を確認します。
- AI チャットに結果の説明や戦略レポートの生成を依頼します。
- 自分の資料に基づく回答が必要なら、ソース資料を追加します。
- 下書きと提案をレビューし、次のスキャンを設定します。

## 自分の資料に基づくナレッジ活用

任意で使えるナレッジライブラリは、テキストを含む PDF、DOCX、Markdown、TXT、貼り付けたテキスト、公開 Web ページ、過去のレポートに対応します。**Qdrant による密ベクトル検索、BM25、タイトル・エンティティに基づく候補検索、順位融合、リランキング**を組み合わせ、周辺のコンテキストと出典を生成結果に取り込みます。

```bash
# アプリと任意のベクトルデータベースを有効にします。
docker compose --profile rag up -d --build
```

**ナレッジライブラリ → モデルと検索**で、埋め込みとリランキングのプロバイダーを設定し、接続をテストして検索を有効にします。ソースをアップロードしたら、インデックス作成が完了してから検索してください。

資料は既定でプロジェクト内に限定されます。アカウント間の共有と、公開コンテンツでの利用許可は別々の設定です。セットアップ、権限、API、プロバイダー評価については、[RAG ガイド](docs/rag.md)を参照してください。

## アーキテクチャと開発

| レイヤー | 技術スタック |
| --- | --- |
| Web インターフェース | React 19 · TypeScript · Vite · TanStack Query |
| API とオーケストレーション | FastAPI · OpenAI Agents SDK |
| バックグラウンド処理 | スキャン、レポート、グラフ拡張、ナレッジのインデックス作成ワーカー |
| 保存と検索 | SQLite / FTS5 · 任意の Qdrant |
| データ収集 | Crawl4AI · 検索およびプラットフォーム別のプロバイダー |

```text
frontend/src/              Web インターフェース、プロジェクト画面、設定
src/opencmo/agents/         CMO と専門エージェント
src/opencmo/tools/          クロール、検索、監査、プラットフォーム連携
src/opencmo/services/       プロジェクト分析と承認ワークフロー
src/opencmo/background/     タスク実行と進捗
src/opencmo/rag/            取り込み、ハイブリッド検索、出典
src/opencmo/storage/        SQLite による永続化
src/opencmo/web/            API ルートと認証
```

<details>
<summary><strong>開発用コマンド</strong></summary>

ソースの依存関係をインストールした後に実行します。

```bash
pip install pytest pytest-asyncio ruff
pytest tests/
ruff check src/ tests/

cd frontend
npm ci
npm run dev
```

Vite 開発サーバーは `http://localhost:5173` で動作し、API リクエストをポート `8080` のバックエンドへプロキシします。

</details>

## ドキュメント

- [設定](docs/configuration.md) — モデルプロバイダーと任意の連携。
- [デプロイ](docs/deployment.md) — ホスティング、永続ストレージ、バックアップ。
- [ナレッジと RAG](docs/rag.md) — 資料の取り込み、検索、出典。
- [RAG 検証](docs/rag-validation.md) — テスト範囲、容量測定、評価状況。
- [貢献ガイド](CONTRIBUTING.md) — 開発フローと貢献者のクレジット。

メンテナーは **[Ling (`Lling0000`)](https://github.com/Lling0000)** です。過去の貢献は [CONTRIBUTORS.md](CONTRIBUTORS.md) に記録しています。

## コミュニティ

[LINUX DO](https://linux.do/) — 技術好きが集まるコミュニティ
