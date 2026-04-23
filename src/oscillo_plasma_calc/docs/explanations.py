"""Three-level explanations for every physical quantity computed in the app.

- 🔰 beginner (学部 4 年生 / 新配属): what it measures in everyday words
- 🔬 researcher (M1〜PD): typical values, how to use, relationship to other quantities
- 🎓 phd (PI / reviewer): assumptions, error analysis, paper references

These strings are displayed in the Trace card as three cascading toggles.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExplanationSet:
    key: str
    display_name: str
    beginner: str
    researcher: str
    phd: str
    references: tuple[str, ...] = ()


_ALL: dict[str, ExplanationSet] = {}


def _reg(es: ExplanationSet) -> ExplanationSet:
    _ALL[es.key] = es
    return es


# ---- Tier 1: Electrical -----------------------------------------------

_reg(ExplanationSet(
    key="vpp", display_name="ピーク間電圧 Vpp",
    beginner=(
        "電圧の「振れ幅」です。高いほど強いパルスが電極にかかっています。"
        "プラズマを生み出す元気さの一番基本の指標。"),
    researcher=(
        "液中ストリーマ放電の典型値は 3〜15 kV。Paschen 電圧を超えているか・超えて"
        "いないかで「実際に放電が開始したか」を判断できる。Ipp とセットで評価し、"
        "Vpp × Ipp でピーク電力のオーダーを見積もれる。"),
    phd=(
        "DC オフセット補正後に算出する前提。プローブ帯域 BW ≫ 1/t_r である必要。"
        "逆パルス成分があれば整流系由来か回路リンギングかを FFT タブで峻別する。"),
    references=("2013_CAP-13-1050",),
))

_reg(ExplanationSet(
    key="ipp", display_name="ピーク間電流 Ipp",
    beginner="電流の「振れ幅」。電子と正イオンが放電チャネルをどれだけ激しく流れたかの指標。",
    researcher=(
        "液中ストリーマで 10〜100 A が典型。Vpp に対する比 Ipp/Vpp が 0.001〜0.01 A/V の"
        "範囲にあれば妥当なインピーダンス帯。"),
    phd=(
        "Rogowski コイル校正が必要。高周波成分でインダクタンス結合があると実効減衰が"
        "入る点に注意。放電電流 vs 変位電流の切り分けは q(t)=∫I dt の構造から評価。"),
    references=("2011_PSST-20-034016",),
))

_reg(ExplanationSet(
    key="rise_time", display_name="立ち上がり時間 t_r",
    beginner="電圧（電流）が 10 % から 90 % まで立ち上がるのにかかった時間。短いほど高速パルス。",
    researcher=(
        "ナノ秒パルス電源では 1〜500 ns が典型。μs オーダーならプローブ帯域不足、"
        "または整形回路の劣化を疑う。EEDF 裾が高エネルギー側に伸びるかは t_r に直結。"),
    phd=(
        "Δt 精度で下限が決まる（Δt=2 ns サンプリングなら t_r の実質下限 ~4 ns）。"
        "検出窓を最初のピーク周辺 ±50 ns に絞る高精度モードは今後追加予定。"),
    references=("2013_CAP-13-1050",),
))

_reg(ExplanationSet(
    key="slew_rate_v", display_name="電圧スルーレート dV/dt",
    beginner="電圧がどれだけ素早く立ち上がるか。大きいほど瞬間的に大きな電界が印加されます。",
    researcher=(
        "10⁹〜10¹² V/s が典型。電子の加速時間スケール 1/f_p と比較し、"
        "EEDF の裾伸びを評価。CO₂ の電離閾値（~13.8 eV）に届くかの目安。"),
    phd=(
        "中央差分（O(Δt²)）で数値ノイズに敏感。必要なら Savitzky-Golay 前処理を"
        "推奨。最大値位置と V ピーク位置の時間差から streamer 前面速度が推定可能。"),
    references=("2013_CAP-13-1050",),
))

_reg(ExplanationSet(
    key="slew_rate_i", display_name="電流スルーレート dI/dt",
    beginner="電流がどれだけ素早く立ち上がるか。プラズマ形成の急峻さの指標。",
    researcher=(
        "10⁸〜10¹⁰ A/s が典型。dV/dt と dI/dt の比から放電チャネルの有効インダクタンス "
        "L_eff ≈ V̇ / İ を推定できる。"),
    phd=(
        "放電電流と変位電流（dQ/dt = C dV/dt）の分離は浮遊容量 C の推定が必要。"
        "Rogowski の高周波応答の周波数依存にも注意。"),
    references=("2013_CAP-13-1050",),
))

_reg(ExplanationSet(
    key="instant_power", display_name="瞬時電力 P(t)",
    beginner="各瞬間にプラズマへ流れ込んでいるエネルギーの速度。正なら入力、負なら回路からの戻り。",
    researcher=(
        "ピーク電力 |P|_max は数 kW〜数百 kW が典型。V と I のピーク位置が揃う ⇔ "
        "抵抗性負荷優位。時間ズレがあれば誘導性／容量性成分が支配。"),
    phd=(
        "プラズマチャネル外の浮遊容量 C_stray で dV/dt 由来の変位電流が乗り、"
        "P(t) の負値成分になる。実効プラズマ投入電力を取り出すには C_stray の寄与を"
        "差し引く必要（Peeters & van der Laan, 2015 PSST が系統的手法）。"),
    references=("2006_JJAP-45-8864", "2011_PSST-20-034016"),
))

_reg(ExplanationSet(
    key="energy", display_name="吸収エネルギー E",
    beginner="観測窓のあいだにプラズマへ入った合計エネルギー。値が大きいほど反応器に投入されたエネルギー量が多い。",
    researcher=(
        "観測窓 20 μs で数 mJ オーダーが液中パルス放電の典型。PRF と掛け合わせて"
        "平均電力に換算し、反応器の冷却要否を判断。"),
    phd=(
        "合成台形則 O(Δt²) の打ち切り誤差で +/- 0.1 % オーダー。窓が 1 周期を跨ぐ場合"
        "最初・最後のパルスの半分を含むかで結果が ±10 % 振れることがあるので、"
        "窓境界を zero-crossing で合わせる前処理を推奨。"),
    references=("2008_APEX-1-046002",),
))

_reg(ExplanationSet(
    key="mean_power", display_name="時間平均電力 P̄",
    beginner="単位時間あたり平均してどれだけのパワーが入ったか。反応器の冷却設計の参考値。",
    researcher=(
        "観測窓を 1 周期と仮定した参考値。実 PRF を入れて Lissajous 法で別推定し、"
        "両者が一致すれば「観測窓 ≈ 周期」の仮定が成り立っていた証拠。"),
    phd=(
        "PRF × (1 パルス吸収 E) とセルフコンシステントか要確認。"
        "観測窓にゴースト放電が入ると P̄ が過大評価される。"),
    references=("2008_APEX-1-046002", "2011_PSST-20-034016"),
))

_reg(ExplanationSet(
    key="v_rms", display_name="電圧 RMS Vrms",
    beginner="電圧の「実効値」。同じ電力を出す直流電圧に相当する値。",
    researcher=(
        "正弦波なら Vrms = Vpp/(2√2) ≈ 0.354·Vpp。現測定は Vrms/Vpp ≈ 0.1 で"
        "デューティ比 ~1 % のパルス列と整合。"),
    phd=(
        "Vrms² × Irms × cosφ の形で無効電力成分の除去に使える。"
        "窓外乱成分が支配的な場合は帯域制限 Vrms を検討（bandpass + RMS）。"),
    references=("classical AC circuit theory",),
))

_reg(ExplanationSet(
    key="i_rms", display_name="電流 RMS Irms",
    beginner="電流の「実効値」。等価 DC 電流として反応器負荷を評価する指標。",
    researcher="Vrms と同じ性質。Vrms/Irms で実効インピーダンス評価。",
    phd="",
    references=("classical AC circuit theory",),
))

_reg(ExplanationSet(
    key="lissajous", display_name="Lissajous (V-q) 平均電力",
    beginner="V-q 平面上の閉ループの面積から 1 周期エネルギーを求め、周波数倍で平均電力に。DBD 研究の標準法。",
    researcher=(
        "平均電力の独立推定。E/T と Lissajous 値が大きく外れる ⇔ 窓 ≠ 周期 か、"
        "変位電流支配で Manley 法の前提が崩れている。"),
    phd=(
        "本実装は q = ∫I dt（モニタ Cm 無し）で DBD の厳密 Manley 法から外れる。"
        "厳密には Qa = Q_plasma + Q_stray を分離する必要（Peeters 2015）。"
        "液中 ns-pulse では抵抗性が支配的なため、直接積分 E = ∫VI dt の方が物理的に"
        "解釈しやすい点に留意。"),
    references=("Manley 1943", "2013_CAP-13-1050", "Peeters & van der Laan 2015 PSST"),
))

_reg(ExplanationSet(
    key="impedance", display_name="瞬時インピーダンス Z(t)",
    beginner="時間ごとの電気抵抗。放電前は高抵抗、放電後は低抵抗に変化します。",
    researcher="ブレークダウン前後で 2〜3 桁ダイナミクス。ブレークダウン時刻の判定に使える。",
    phd="|I|<閾値 は NaN。ガード閾値選択は Ipp × 0.01〜0.001 程度が経験的。",
    references=(),
))

_reg(ExplanationSet(
    key="peak_power", display_name="瞬時電力ピーク |P|_max",
    beginner="瞬間的な最大の入力電力。値が大きいほど強いパルス。",
    researcher="Vpp × Ipp / 4 の理論上限に近ければ V と I が同位相（抵抗性負荷）。",
    phd="窓処理やダウンサンプルでピーク値が減衰する点に注意。",
    references=("2006_JJAP-45-8864",),
))


# ---- Tier 2: Plasma ---------------------------------------------------

_reg(ExplanationSet(
    key="boltzmann_two_line", display_name="Boltzmann 2 本線法による Te",
    beginner="2 本のスペクトル線の強度比から電子温度を推定。液中プラズマの「熱さ」の目安。",
    researcher=(
        "典型 0.5〜5 eV（5,800〜58,000 K）。CO₂ 電離閾値 13.8 eV まで電子の裾が"
        "届くかは Te に強く依存。"),
    phd=(
        "LTE 仮定・光学的に薄い前提。自己吸収があると I_ij が過小評価され Te 過大。"
        "n 本線の Boltzmann plot 法（spectroscopy/boltzmann_plot.py）の方が頑健。"),
    references=("2006_JJAP-45-8864", "2009_JAP-106-113302"),
))

_reg(ExplanationSet(
    key="stark", display_name="Stark 広がりによる ne",
    beginner="水素 Hα 線の線幅から電子密度を推定。線幅が広いほど電子が密。",
    researcher=(
        "液中プラズマで 10²¹〜10²⁴ m⁻³ が典型。Stark 係数 α(Te) は Te に弱く依存するので、"
        "Te を別途 Boltzmann 法で決めて対応 α を文献表から引くのが厳密。"),
    phd=(
        "Voigt fit で FWHM を分離（Doppler + Stark）。本実装は Lorentz 成分全体を"
        "Stark と仮定するため 0〜30 % 程度の系統誤差あり。"
        "Gigosos & Cardeñoso (1996 JPB) の数値表が現行標準。"),
    references=("2009_POP-16-033503", "Gigosos & Cardeñoso 1996 JPB 29:4795"),
))

_reg(ExplanationSet(
    key="debye", display_name="Debye 長 λ_D",
    beginner="プラズマが電荷を打ち消し合える最小の距離。これより小さい領域は「純プラズマ」と呼べません。",
    researcher=(
        "Te=1 eV, ne=10²² m⁻³ で λ_D ≈ 74 nm。電極ギャップ mm オーダー ≫ λ_D なので"
        "準中性バルクが成立していると判断できる。"),
    phd="古典公式。ne > 10²⁴ になると電子縮退で古典近似が破れる（本プロジェクトの範囲外）。",
    references=(),
))

_reg(ExplanationSet(
    key="plasma_freq", display_name="プラズマ周波数 f_p",
    beginner="プラズマが自然に振動する周波数。外部 RF/MW との大小で吸収か透過が決まる。",
    researcher=(
        "ne=10²² → f_p ≈ 900 GHz。MW 2.45 GHz ≪ f_p なのでプラズマ表面近傍で反射／吸収、"
        "深部までは届かない（skin depth）。"),
    phd="縮退・相対論補正は本範囲では無視可。",
    references=("2008_APEX-1-046002",),
))

_reg(ExplanationSet(
    key="ohmic", display_name="Ohmic 加熱密度",
    beginner="導電性液体内で電流によって発生する単位体積あたりの熱。",
    researcher=(
        "σ=0.01 S/m, E=10⁶ V/m で p_ohm = 10¹⁰ W/m³ = 10 kW/cm³。"
        "気泡形成と streamer 伝搬の駆動力として妥当なオーダー。"),
    phd=(
        "σ は温度依存 σ(T) = σ₀ exp(-E_a/(RT))。局所加熱で σ が上昇し逃走（thermal"
        "runaway）を起こすと streamer 形成の引き金に。Bruggeman et al. (2016 PSST) 参照。"),
    references=("2011_PSST-20-034016", "Bruggeman et al. 2016 PSST 25:053002"),
))

_reg(ExplanationSet(
    key="paschen", display_name="Paschen 破壊電圧",
    beginner="気体空間で放電が起こり始める最小電圧。圧力 p とギャップ d の積で決まります。",
    researcher=(
        "1 atm × 1 mm で V_b ≈ 3 kV。実測 Vpp=11.8 kV は大幅に超えており、"
        "ブレークダウン確定と判断できる。"),
    phd=(
        "液中では厳密には適用不可（Paschen は気相前提）。液中 streamer は Maxwell "
        "stress と局所気泡形成が支配する別機構（Seepersad et al. 2013 JPD レビュー）。"
        "本実装は「気相参照値」として提示。"),
    references=("2013_CAP-13-1050",
                "Seepersad et al. 2013 JPD 46:355201 (liquid streamer review)"),
))


# ---- Tier 3: Chemistry ------------------------------------------------

_reg(ExplanationSet(
    key="g_value", display_name="G 値",
    beginner="100 eV のエネルギーで何分子できたかの効率指標。大きいほど効率的。",
    researcher=(
        "液中プラズマ H₂ 生成で 1〜10 が典型。触媒協調で 20 超もあり得る。"
        "ε_chem (eV/molecule) = 100 / G に換算可能。"),
    phd=(
        "E_abs はプラズマに実際に入ったエネルギー。浮遊容量由来の戻りエネルギーを"
        "差し引いた純投入を使うべき。G 値はラジオリシス由来の universal 指標だが、"
        "プラズマの場合は EEDF 依存で温度換算が単純でない点に注意。"),
    references=("2012_IJHE-37-16000", "2020_JJIE_99-104"),
))

_reg(ExplanationSet(
    key="efficiency", display_name="化学エネルギー変換効率 η",
    beginner="投入したエネルギーのうち、目的の化学反応にどれだけ変わったかの割合。",
    researcher=(
        "液中 CO₂ → メタノール合成で 5〜15% が典型。20% 超は触媒併用・超音波支援の"
        "「+α 効果」が効いているサイン。"),
    phd=(
        "ΔH は反応エンタルピー（形成熱差）。反応選択性と組合せて評価。"
        "副生成物 H₂、O₂ の混入でみかけ η が上振れすることがある。"),
    references=("2017_JEPE-10-335",),
))

_reg(ExplanationSet(
    key="selectivity", display_name="生成物選択性 X",
    beginner="生成物のうち、目的の物質がどれだけの割合を占めるかの指標。",
    researcher=(
        "CH₃OH 選択性 > 50 % が油合成プロセスの実用目標。H₂ 共生成が多ければ"
        "Fischer-Tropsch 段への供給原料として再利用するルートあり。"),
    phd="GC 定量誤差（FID/TCD）が数 % あるので、有効数字 2 桁程度での比較が妥当。",
    references=("2019_IJHE_44-23912",),
))


# ---- Tier 4: Boltzmann plot (multi-line LSM) --------------------------

_reg(ExplanationSet(
    key="excitation_temp", display_name="励起温度 Te（Boltzmann plot）",
    beginner=(
        "複数のスペクトル線の強度から電子温度を推定します。"
        "2 本より 3 本以上の方が精度が高いです。"),
    researcher=(
        "n 本線を用い、y = ln[I/(g·A·ν)] vs x = E_u-E_l でプロットし、"
        "傾き m から Te = -1/(kB m) を得る。典型値は 5,000〜30,000 K。"),
    phd=(
        "線選択の上準位エネルギー差が大きい組合せを使うこと。小さいと slope 推定"
        "誤差が発散（今回の Cu① が典型例で Te=662 K という非物理値を出している）。"
        "下準位が異なる場合、厳密には x=E_u のみを取るべき（xlsx の x=E_u-E_l は"
        "下準位共通時のみ等価）。将来の追加オプション候補。"),
    references=("2006_JJAP-45-8864", "2009_JAP-106-113302",
                "励起温度計算シート ver.2.xlsx (Nomura lab 社内)"),
))


# ---- Advanced electrical ----------------------------------------------

_reg(ExplanationSet(
    key="pulse_energy", display_name="パルスエネルギー E_pulse",
    beginner="1 発のパルスがプラズマへ入れたエネルギー。窓全体ではなく 1 パルス単位。",
    researcher=(
        "観測窓エネルギー E を検出パルス数 N で割って求める。"
        "液中 ns パルスで数 μJ〜数百 μJ が典型。"
        "PRF を掛ければ平均電力と照合可能。"),
    phd=(
        "find_peaks prominence=0.4·Vpp で同定。partial discharge が混在すると"
        "N が過大評価される恐れ。FWHM から τ_pulse を別途取り、1 パルス内での"
        "インパルス積分 (Peeters 2015) へ拡張する余地あり。"),
    references=("2008_APEX-1-046002", "2013_CAP-13-1050"),
))

_reg(ExplanationSet(
    key="duty_cycle", display_name="デューティ比 D",
    beginner="1 周期のうちパルスがオンになっている時間の割合。",
    researcher=(
        "D ≈ N·FWHM / T_window。液中 ns パルス列で D ≈ 1% が典型。"
        "Vrms²/Vpp² との一貫性チェック指標。"),
    phd="繰返し電力の重要パラメータ。冷却設計の基礎量。",
    references=("classical pulse-power engineering",),
))

_reg(ExplanationSet(
    key="effective_average_power", display_name="実効平均電力 (Ppeak·D)",
    beginner="装置が実際にまわっている平均電力の見積もり値。1 kW 制約の判定に使います。",
    researcher=(
        "P_eff = P_peak × D。観測窓平均 P̄ と桁オーダーが一致すべき。"
        "大きく乖離 ⇔ 観測窓内のパルス分布 or D 推定の不具合。"),
    phd="1 kW 制約は研究室慣例（2026-04-23 会議）。装置予算バジェットとの突き合わせに使用。",
    references=("lab meeting 2026-04-23",),
))

_reg(ExplanationSet(
    key="abs_power_mean", display_name="絶対値電力 時間平均 ⟨|P|⟩",
    beginner="電力の絶対値を平均したもの。誘導/容量リターンも全て「仕事」として数える。",
    researcher=(
        "P̄ と ⟨|P|⟩ の差が誘導性・容量性成分の大きさ。"
        "⟨|P|⟩ / P̄ が 1 に近い ⇔ 抵抗性負荷、>> 1 ⇔ リアクタンス支配。"),
    phd="displacement current との分離が必要な場合は Peeters 2015 の補正を併用。",
    references=("Peeters 2015 PSST 24:015014",),
))

_reg(ExplanationSet(
    key="crest_factor", display_name="Crest factor CF",
    beginner="ピークと実効値の比。鋭いパルスほど値が大きい。",
    researcher="正弦波で √2、パルス列で ≈ √(1/D)。本データ CF≈9 → D≈1.2% と整合。",
    phd="振幅分布の非ガウス性指標。CF 過大 ⇔ 突発スパイク（トリガ誤検出の疑い）。",
    references=("classical signal analysis",),
))

_reg(ExplanationSet(
    key="form_factor", display_name="Form factor FF",
    beginner="実効値と絶対値平均の比。波形の「歪み」の指標。",
    researcher="正弦波で π/(2√2)≈1.11、パルスで大。",
    phd="", references=(),
))

_reg(ExplanationSet(
    key="power_density", display_name="プラズマ電力密度 p_vol",
    beginner="プラズマ体積 1 m³ あたりに投入されている電力。",
    researcher=(
        "反応速度の直接ドライバ。液中ストリーマで 10⁹〜10¹¹ W/m³ = 1〜100 kW/cm³ が典型。"
        "電極ギャップ × 電極面積 or 発光画像から V_plasma を推定し入力。"),
    phd="Thermal conductivity-limited regime の境界として p_vol ~ 10¹⁰ W/m³ 付近が重要。",
    references=("Bruggeman 2016 PSST 25:053002",),
))


# ---- Oil synthesis KPIs -----------------------------------------------

_reg(ExplanationSet(
    key="sei", display_name="比エネルギー投入量 SEI",
    beginner="CO₂ 1 mol を処理するのに投入したエネルギー。油合成効率の根本指標。",
    researcher=(
        "典型 CO₂ プラズマで 300〜1000 kJ/mol（3〜10 eV/molecule）。"
        "低いほど効率良、ただし過度に低いと変換率 χ が低下。"),
    phd=(
        "η_SE × (ΔHr/SEI) の関係で単位パス効率と結合。"
        "最適点は χ vs SEI の関数で決まる（Snoeckx & Bogaerts 2017 Fig.6）。"),
    references=("Snoeckx & Bogaerts 2017 CSR 46:5805",),
))

_reg(ExplanationSet(
    key="energy_cost", display_name="エネルギーコスト EC",
    beginner="目的物 1 mol を作るのに必要なエネルギー。数字が小さいほど低コスト。",
    researcher=(
        "メタノール合成で 600〜2000 kJ/mol が報告値。"
        "触媒協調で 400 kJ/mol まで下がる報告もあり（2020 JJIE 99:104）。"),
    phd="Free-energy change ΔG(T) との比から Second-law efficiency を直接評価できる。",
    references=("Bogaerts & Neyts 2018 ACS Energy Lett 3:1013",
                "2020_JJIE_99-104"),
))

_reg(ExplanationSet(
    key="chi_co2", display_name="CO₂ 変換率 χ",
    beginner="入力 CO₂ のうち何 % が反応したか。",
    researcher=(
        "液中プラズマ CO₂ 還元で 1〜20 % が典型（Snoeckx & Bogaerts 2017）。"
        "高 SEI で χ 増加するが、η_SE は逆にトレードオフ。"),
    phd="",
    references=("Snoeckx & Bogaerts 2017 CSR 46:5805",),
))

_reg(ExplanationSet(
    key="eta_se", display_name="単位エネルギー変換効率 η_SE",
    beginner="投入エネルギーのうち CO₂ 還元で化学エネルギーに変わった割合。",
    researcher="液中プラズマで 5〜20 % が典型。>40 % は触媒併用が必須。",
    phd="", references=("Snoeckx & Bogaerts 2017 CSR 46:5805",),
))

_reg(ExplanationSet(
    key="asf", display_name="ASF 連鎖成長確率 α",
    beginner="生成物の炭素鎖がどこまで伸びるかを決める確率。0.9 近くなら灯油・軽油域。",
    researcher=(
        "Fischer-Tropsch 合成で α=0.7〜0.95 が典型。"
        "α>0.95 ⇔ ワックス（重油）、α<0.5 ⇔ ガソリン〜C2。"),
    phd=(
        "Anderson-Schulz-Flory 分布は lngaussian に従い log(Wn/n) vs n が直線。"
        "実験データの直線性から α の不確かさを直接評価可能。"),
    references=("Anderson 1984",),
))


# ---- Non-equilibrium plasma --------------------------------------------

_reg(ExplanationSet(
    key="e_over_n", display_name="換算電場 E/N",
    beginner="気体粒子 1 個あたりの電場。電子がどれだけエネルギーを得るかを決める。",
    researcher=(
        "Td 単位（1 Td = 1e-21 V·m²）。CO₂ プラズマで 50〜300 Td が電子電離・解離の"
        "活性域。本ソフトはユーザ入力 E [V/m] + 圧力 + T_gas から算出。"),
    phd=(
        "EEDF の形状を決める第一パラメータ。Bolsig+ 数値解に E/N を入れれば"
        "k(ε) 断面積と合わせて電子衝突率が求まる。"),
    references=("Phelps LXCat", "Fridman 2008"),
))

_reg(ExplanationSet(
    key="mean_e_energy", display_name="電子平均エネルギー ⟨ε⟩（推定）",
    beginner="電子の平均的なエネルギー。CO₂ を壊すには 5.5 eV 以上、電離には 13.8 eV 必要。",
    researcher=(
        "0.02·E/N [eV/Td] の粗近似。精密には BOLSIG+ 解を要する。"
        "CO₂ 振動励起 ε~1 eV が最効率の還元モード。"),
    phd=(
        "EEDF 非 Maxwell 時は moment 積分が必要。Ridenti 2015 の empirical fit "
        "は CO₂ 背景で ±30 % 程度の精度。"),
    references=("Ridenti et al. 2015 PSST",),
))

_reg(ExplanationSet(
    key="tv_rot_ratio", display_name="非平衡度 T_e/T_gas",
    beginner="電子温度とガス温度の比。10 以上なら「熱くないのに反応する」効率良モード。",
    researcher=(
        "液中プラズマで T_e/T_gas > 30 は非熱的 CO₂ 還元に有利。"
        "R² が高い Boltzmann plot から得た T_e を使うのが前提。"),
    phd="Grain 温度・ν_coll / ν_ionization 比とも関連。",
    references=("Fridman 2008",),
))

_reg(ExplanationSet(
    key="t_vib", display_name="振動温度 Tv",
    beginner="気体分子の振動（ばね運動）の温度。CO₂ 還元では T_gas より Tv が高いほど有利。",
    researcher=(
        "CO₂ 3rd vibrational ladder climbing モードで最大効率（Fridman 2008）。"
        "Tv ≈ 3000-6000 K が目標領域。2 バンド強度比で推定。"),
    phd="Treanor 分布の仮定。CO₂ asymmetric stretch 2349 cm⁻¹ = 0.291 eV。",
    references=("Fridman 2008", "Bruggeman 2014 PSST 23:045022"),
))


# ---- Operational ------------------------------------------------------

_reg(ExplanationSet(
    key="budget_margin", display_name="装置電力予算 余裕度",
    beginner="装置全体が 1 kW 以下で動いているかのチェック。余裕が 30 % 以上なら健全。",
    researcher=(
        "M = (W_budget − P_est)/W_budget。< 10 % で警告、< 0 で超過エラー。"
        "Upload サイドバーで予算値・Ppeak・D から自動算出。"),
    phd="瞬時ピーク電力（数百 kW）に気を取られないよう、平均換算値で判断するのが肝。",
    references=("lab meeting 2026-04-23",),
))

_reg(ExplanationSet(
    key="heat_dissipation", display_name="冷却必要量 Q_cool",
    beginner="プラズマ投入電力のうち熱になって装置外へ捨てる分。水冷要否の判定に。",
    researcher="Q_cool = P̄ − P̄_chem。反応器の熱交換器能力と比較。",
    phd="",
    references=(),
))

_reg(ExplanationSet(
    key="eta_device", display_name="装置→プラズマ効率 η_dev",
    beginner="コンセント電力のうちプラズマに届いた割合。電源効率の指標。",
    researcher=(
        "70〜95 % が妥当。それ以下なら電源 / トランス / 整流の損失が大。"
        "会議 2026-04-23 のコンセント側比較アイテム。"),
    phd="",
    references=("lab meeting 2026-04-23",),
))


EXPLANATIONS: dict[str, ExplanationSet] = dict(_ALL)


def get_explanation(key: str) -> ExplanationSet | None:
    return EXPLANATIONS.get(key)
