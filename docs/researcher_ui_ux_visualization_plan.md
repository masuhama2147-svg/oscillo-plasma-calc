# 油合成研究者向け UI/UX・可視化強化 実装メモ

## 目的

液中プラズマ CO2 還元から液体燃料・油合成へ進む研究では、単に波形を表示するだけでは足りない。研究者が短時間で判断したいのは、放電が成立しているか、装置の 1 kW 予算を超えないか、投入エネルギーが化学生成へ結びついているか、発光分光から得た温度・密度が妥当か、論文や研究ノートに載せられる根拠つき数値になっているかである。

今回の改善では既存の Shiny for Python + Plotly 構成を維持し、画面表示、図表注釈、KPI 表、Markdown/CSV Export を研究者向けに拡張した。計算ロジック本体は既存の `TraceResult` と各 compute 関数を使い、UI で用途別に再構成する方針にしている。

## スクリーンショットから見えた課題

- Upload 画面は読み込み成功後の情報が箇条書き中心で、N、dt、fs、測定窓、Vpp、Ipp、PRF、DC offset、予算余裕度を一目で比較しにくい。
- Waveform / Electrical / FFT は解析には使えるが、ピーク、rise time、ゼロクロス、累積エネルギー、高調波、Nyquist といった論文補助図に必要な注釈が不足している。
- Chemistry は G value と効率だけでは油合成判断に不足するため、SEI、energy cost、CO2 conversion、ASF alpha を同じ表で見る必要がある。
- Plasma / 励起温度 Te は値が nan になった場合の原因候補が画面上で弱く、採用線数、除外線、R2、LTE 判定を研究者がすぐ確認できる必要がある。
- Trace は根拠確認には有効だが、査読・研究ノートで最初に見るべき「重要警告」「油合成 KPI」「装置安全」「論文候補値」が上部にまとまっていなかった。
- Export は元波形 CSV だけでは論文補助表に使いにくいため、計算済み量を `quantity,value,unit,status,source,equation_key` で出す必要がある。

## 実装した改善

### Upload: 実験条件レビュー

読み込み後に、サンプル数、Δt/fs、測定窓、Vpp、Ipp、PRF、DC offset、1 kW 予算余裕度をカードで表示する。次に見るタブは固定文ではなく、rise time や装置予算の警告に応じて Trace / Waveform / Electrical を優先表示する。

### Waveform / Electrical / FFT: 論文補助図モード

全体に `screen` / `paper` の図表モードを追加した。`paper` では白背景、整理した凡例、明確な軸線、単位付き軸ラベルを使う。Waveform には V/I ピーク、10–90% rise time、ゼロクロスを注釈する。Electrical には P(t) と累積 E(t) を同じ図に重ね、Lissajous にはループ面積と PRF を表示する。FFT には支配周波数、2f/3f、高調波、Nyquist 線、信頼範囲外の領域を表示する。

### Chemistry / Plasma: 油合成 KPI 中心

Chemistry では G value、chemical efficiency、SEI、energy cost、CO2 conversion、single-pass energy efficiency、ASF alpha を「油化判断 KPI」として表にまとめた。Plasma では Te、ne、Debye length、plasma frequency、E/N、mean electron energy、T_e/T_gas を「反応場診断 KPI」としてまとめた。

### 励起温度 Te: LTE 妥当性の明示

Boltzmann plot には R2、採用線数、LTE 判定を注釈する。Te が nan/inf の場合は、採用線不足、E_u 差不足、強度 0、自己吸収、感度補正不足、線ラベル違いを画面上に出す。

### Trace: 査読・研究ノート用の根拠確認

Trace 上部に「重要警告・注意」「油合成・装置判断 KPI」「論文・研究ノートに載せる候補値」を追加した。主要 KPI はカードを開かずに、ショートカットから式と数値代入を確認できる。

### Export: 論文補助資料

Markdown レポートの先頭に実験条件レビュー、主要 KPI 表、異常値・注意値、図表の読み方を追加した。CSV は元波形ではなく、計算済み量を `quantity,value,unit,status,source,equation_key` で出力する。

## 図表デザイン規則

- 色は意味に使う。緑は正常、青は注意、黄は警告、赤は異常。
- 軸には必ず単位を入れる。
- 論文補助図モードでは白背景を使い、過剰なグリッドや装飾を避ける。
- 波形図ではピークと立ち上がり、FFT では支配周波数と Nyquist、Boltzmann plot では R2 と採用線数を注釈する。
- 表は「量、値、単位、判定、根拠」の順に揃え、研究ノートへ転記しやすくする。

## 採用 OSS と公開データ候補

- Plotly + Shiny for Python を継続採用した。既存 UI と計算パイプラインがこの構成で動作しており、今回の目的は全面移行ではなく研究者向け画面強化である。
- Dash は 2026年3月時点で v4.1.0 が公開されているが、今回は移行しない。既存資産とテストを活かす方がリスクが低い。
  - https://github.com/plotly/dash
- NIST Atomic Spectra Database は、原子スペクトル線、エネルギー準位、遷移確率の信頼できる参照元として将来連携候補にする。
  - https://www.nist.gov/pml/data/asd.cfm
- LXCat / BOLSIG+ 系は、E/N、電子衝突断面積、EEDF 連携の将来拡張候補にする。
  - https://us.lxcat.net/solvers/BolsigPlus/index.php?step=1

## 受け入れ基準

- Upload 後に実験条件カードが表示される。
- Waveform で V/I ピーク、10–90% rise time、ゼロクロス注釈が見える。
- Electrical で P(t)、累積 E(t)、Lissajous、電力 KPI 表が同一タブ内で確認できる。
- FFT で支配周波数、2f/3f、Nyquist 線が見える。
- Chemistry で油化判断 KPI 表が表示される。
- Plasma で反応場診断 KPI 表が表示される。
- 励起温度 Te で R2、採用線数、除外線、LTE 判定、nan/inf 時の原因候補が表示される。
- Trace で重要警告、油合成 KPI、論文候補値、主要式ショートカットが表示される。
- Export Markdown と CSV が研究ノート・論文補助資料として使える形式になる。
