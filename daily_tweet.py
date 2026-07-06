import yfinance as yf
import anthropic
import tweepy
import os
import datetime

# ウォッチリスト（銘柄コード: 銘柄名）
# ※ポートフォリオの銘柄 + 主要銘柄
WATCHLIST = {
    "1605.T": "INPEX",
    "4385.T": "メルカリ",
    "4661.T": "オリエンタルランド",
    "5401.T": "日本製鉄",
    "7267.T": "本田技研",
    "8117.T": "中央自動車工業",
    "8306.T": "三菱UFJ",
    "9023.T": "東京メトロ",
    # 主要銘柄
    "6758.T": "ソニー",
    "9984.T": "ソフトバンクG",
    "7203.T": "トヨタ",
    "9432.T": "NTT",
    "6902.T": "デンソー",
    "4519.T": "中外製薬",
    "6861.T": "キーエンス",
    "8058.T": "三菱商事",
    "8031.T": "三井物産",
    "6501.T": "日立製作所",
    "6752.T": "パナソニック",
    "7751.T": "キヤノン",
}

def get_nikkei():
    try:
        ticker = yf.Ticker("^N225")
        hist = ticker.history(period="5d")
        if len(hist) < 2:
            return None
        today = hist.iloc[-1]
        prev = hist.iloc[-2]
        change = today["Close"] - prev["Close"]
        change_pct = (change / prev["Close"]) * 100
        return {
            "price": today["Close"],
            "change": change,
            "change_pct": change_pct,
        }
    except Exception as e:
        print(f"日経平均取得エラー: {e}")
        return None

def get_movers(threshold=2.0):
    movers = []
    for symbol, name in WATCHLIST.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if len(hist) < 2:
                continue
            today = hist.iloc[-1]
            prev = hist.iloc[-2]
            change_pct = ((today["Close"] - prev["Close"]) / prev["Close"]) * 100
            if abs(change_pct) >= threshold:
                movers.append({
                    "code": symbol.replace(".T", ""),
                    "name": name,
                    "price": today["Close"],
                    "change_pct": change_pct,
                })
        except:
            pass
    return sorted(movers, key=lambda x: abs(x["change_pct"]), reverse=True)[:4]

def generate_tweet(nikkei, movers):
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    date_str = today.strftime("%-m/%-d")

    movers_text = "\n".join(
        [f"- {m['name']}({m['code']}): {m['change_pct']:+.1f}%" for m in movers]
    ) if movers else "特になし"

    prompt = f"""以下の株式市場データをもとに、今日の注目銘柄・市場解説のツイートを作成してください。

【データ】
日付: {date_str}
日経平均: {nikkei['price']:,.0f}円 ({nikkei['change_pct']:+.1f}%)
大きく動いた銘柄:
{movers_text}

【条件】
- 全体で200文字以内（ハッシュタグ含む）
- 日経平均の動きに一言コメント
- 動いた銘柄があれば理由を1〜2行で推測
- 清原達郎の「割安小型株」投資の視点があると良い
- 最後に #日本株 #株式投資 のハッシュタグ
- 絵文字で読みやすく
- 投資推奨・断定的な表現は避ける（情報提供のみ）
- ツイート本文のみ出力してください"""

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()

def post_tweet(text):
    client = tweepy.Client(
        consumer_key=os.environ["TWITTER_API_KEY"],
        consumer_secret=os.environ["TWITTER_API_SECRET"],
        access_token=os.environ["TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
    )
    response = client.create_tweet(text=text)
    print(f"投稿完了 (ID: {response.data['id']})")

def main():
    print("=== 日次ツイート生成 ===")

    print("日経平均を取得中...")
    nikkei = get_nikkei()
    if not nikkei:
        print("日経平均データを取得できませんでした")
        return

    print(f"日経平均: {nikkei['price']:,.0f}円 ({nikkei['change_pct']:+.1f}%)")

    print("大きく動いた銘柄を確認中...")
    movers = get_movers()
    for m in movers:
        print(f"  {m['name']}: {m['change_pct']:+.1f}%")

    print("ツイートを生成中...")
    tweet = generate_tweet(nikkei, movers)
    print(f"\n【生成されたツイート】\n{tweet}\n")
    print(f"文字数: {len(tweet)}")

    if os.environ.get("DRY_RUN") == "true":
        print("DRY_RUN モード：ツイートは投稿されません")
    else:
        print("Twitterに投稿中...")
        post_tweet(tweet)

if __name__ == "__main__":
    main()
