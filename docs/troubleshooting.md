# ❌ よくあるエラーと対処（トラブルシューティング FAQ）

「コマンドラインを使ったことがない」レベルから読めるように書いてあります。エラーが出たらまずこのページを検索してください（Ctrl+F）。

---

## 🪟 Windows 関連

### Q1. `'python' は、内部コマンドまたは外部コマンド…として認識されていません。`

**原因**: Python が PATH に追加されていません。

**対処**:
1. Python のインストーラを **再実行**（[python.org/downloads](https://www.python.org/downloads/) から再ダウンロード）
2. インストール最初の画面で **☑ Add Python to PATH** に必ずチェック
3. 「Install Now」をクリック
4. **コマンドプロンプト / PowerShell を一度閉じて、開き直す**（PATH の変更を反映させるため）
5. `python --version` で `Python 3.x.x` が出れば成功

---

### Q2. PowerShell で `.ps1 cannot be loaded because running scripts is disabled on this system`

**原因**: Windows のデフォルト設定で PowerShell スクリプト実行が制限されています。

**対処** (**初回 1 回だけ** 実行):
1. **PowerShell を「管理者として実行」** で開く（スタートメニューで PowerShell を右クリック → 管理者として実行）
2. 以下をコピペして Enter:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
3. 「[Y] はい」と聞かれたら `Y` Enter
4. 普通の PowerShell に戻って再実行

---

### Q3. `launch_ui.bat` をダブルクリックしたら Defender が「Windows によって PC が保護されました」を出す

**原因**: 未署名の `.bat` を Microsoft Defender SmartScreen が警告しているだけ。**実害なし**。

**対処**:
1. 警告ダイアログの **「詳細情報」** をクリック（小さく書かれている）
2. 出てきた **「実行」** ボタンをクリック
3. 一度許可すれば、次回以降はこの警告は出ません

---

### Q4. `git: コマンドが見つかりません` / `'git' は認識されません`

**原因**: Git for Windows が未インストール、または PATH に通っていません。

**対処（コマンド派）**:
1. [git-scm.com/download/win](https://git-scm.com/download/win) からダウンロード
2. インストーラはすべて **デフォルト設定** で OK（「Next」を連打）
3. ターミナルを開き直して `git --version` で確認

**対処（GUI 派）**:
- [GitHub Desktop](https://desktop.github.com/) を使えば git コマンド一切不要
- 詳しくは README の「🖱️ Git コマンドが嫌な場合」を参照

---

### Q5. `python -m venv .venv` でエラー

**原因 A**: Python 3.12 未満（venv モジュールがない or 古い）
**対処**: Python 3.12 以上を再インストール

**原因 B**: フォルダ名に半角スペースや日本語が含まれる
**対処**: フォルダを `C:\Users\<あなた>\Documents\oscillo-plasma-calc\` のような **半角英数のみのパス** に置く

---

### Q6. 仮想環境を有効化できない (`activate` してもプロンプトが変わらない)

**コマンドプロンプト (cmd) の場合**:
```cmd
.venv\Scripts\activate.bat
```

**PowerShell の場合**:
```powershell
.\.venv\Scripts\Activate.ps1
```

**Git Bash の場合**:
```bash
source .venv/Scripts/activate
```

成功するとプロンプトの先頭に `(.venv)` が付きます。

---

## 🍎 macOS 関連

### Q7. `xcrun: error: invalid active developer path` （初回 git 実行時）

**対処**:
```bash
xcode-select --install
```
ダイアログが出たら「インストール」をクリック → 数分で完了

---

### Q8. `python3: command not found`

**対処** (Homebrew が入っている前提):
```bash
brew install python@3.13
```

Homebrew が入っていない場合:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

---

### Q9. `error: externally-managed-environment` （pip install 時）

**原因**: macOS の system Python を直接いじろうとしている。

**対処**: 仮想環境を **必ず activate** してから pip install:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 🌐 ブラウザ関連

### Q10. ブラウザが自動で開かない

**対処**: ターミナルに `Uvicorn running on http://127.0.0.1:8000` と表示されたら、手動でブラウザを開いて `http://127.0.0.1:8000` を入力。

ポートが既に使用されている場合は別のポート番号を指定:
```bash
# 例えば 8001 番に変える
.venv/bin/shiny run --port 8001 src/oscillo_plasma_calc/ui/app.py
```

---

### Q11. ブラウザで `このサイトにアクセスできません` / `127.0.0.1 で接続が拒否されました`

**対処**:
1. ターミナルに `Application startup complete` が出てから 2-3 秒待つ
2. それでもダメなら別のブラウザ（Chrome / Edge / Safari）で試す
3. プロキシ設定や VPN を一時的に切る

---

## 📊 アプリ内エラー

### Q12. CSV を読み込ませたら「列が不足: voltage_V」

**原因**: CSV の列名が仕様と違う。

**対処**: CSV を Excel で開いて、1 行目の列名を以下に揃える:
```
time_s, voltage_V, current_A
```

スペースなし、英字小文字、3 列必須。詳しくは Upload タブの STEP 1 の例を参照。

---

### Q13. Te が `(参考値)` と表示されて、論文に使ってよいか分からない

**原因**: Boltzmann plot の R² が 0.85 未満で、LTE（局所熱平衡）が成立していない可能性が高い。

**対処**:
1. 採用線数を 3 本以上にする
2. タングステン電極の 4 本線（下準位 6s 共通）を使う（R² が上がりやすい）
3. 強度の感度補正（プローブ波長依存性）を見直す
4. それでも R² ≥ 0.85 にならないなら、その実験条件では LTE が成立していない → 論文には書かない、または「非平衡」を明示する

---

### Q14. 装置予算 1 kW を超過しています、と赤バナーが出る

**原因**: P_eff = Ppeak × Duty が 1 kW を超えた。

**対処**:
- 想定外の P_eff なら、Sidebar の PRF (Pulse Repetition Frequency) を実際の値に合わせる
- 実際に超えているなら、電源出力を下げる or PRF を下げる
- 装置予算は「研究室の運用ルール」なので、超過時は野村先生・中島先生に相談

---

## 🆘 上記で解決しないとき

GitHub の Issue にスクリーンショットと一緒に投稿してください:
https://github.com/masuhama2147-svg/oscillo-plasma-calc/issues
