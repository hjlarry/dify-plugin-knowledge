# knowledge

**作者:** hjlarry  
**バージョン:** 0.0.2  
**タイプ:** ツール  
**リポジトリ:** [https://github.com/hjlarry/dify-plugin-knowledge](https://github.com/hjlarry/dify-plugin-knowledge)

## はじめに

### 1. 認証設定

`API_URL` と `API_KEY` は以下の場所から取得します。  
![1](../_assets/1.png)

### 2. 設定

![2](../_assets/2.png)

利用するデータセットIDはここで確認できます。  
![3](../_assets/3.png)

`PROCESS RULE` は既定値として `{"mode": "automatic"}` を利用できます。カスタム設定を行う場合は、チャンク方式に応じて次のように設定してください。

`CHUNK METHOD` が `General` または `Q&A` の場合:

```json
{
  "mode": "custom",
  "rules": {
    "pre_processing_rules": [
      {"id": "remove_extra_spaces", "enabled": true},
      {"id": "remove_urls_emails", "enabled": true}
    ],
    "segmentation": {
      "separator": "\n\n",
      "max_tokens": 1024,
      "chunk_overlap": 50
    }
  }
}
```

`CHUNK METHOD` が `Parent-child` の場合:

```json
{
  "mode": "hierarchical",
  "rules": {
    "pre_processing_rules": [
      {"id": "remove_extra_spaces", "enabled": true},
      {"id": "remove_urls_emails", "enabled": true}
    ],
    "segmentation": {
      "separator": "\n\n",
      "max_tokens": 1024,
      "chunk_overlap": 50
    }
  },
  "parent_mode": "full-doc",
  "subchunk_segmentation": {
    "separator": "\n\n",
    "max_tokens": 1024,
    "chunk_overlap": 50
  }
}
```

### 3. 実行

PDF解析プラグイン（例: `MinerU`）と同様の手順でプラグインを起動できます。  
![4](../_assets/4.png)
