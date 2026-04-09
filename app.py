from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from datetime import datetime, timedelta, timezone
import os
import shlex

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise ValueError("Missing CHANNEL_ACCESS_TOKEN or CHANNEL_SECRET environment variable")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 台灣時區 UTC+8
TW_TZ = timezone(timedelta(hours=8))

bosses = [
    {"name": "不死鳥", "tags": ["不死", "火鳥", "鳥"], "respawn": 480},
    {"name": "伊弗利特", "tags": ["38", "39", "391", "EF", "Ef", "eF", "ef", "ㄧ佛", "一佛", "伊佛", "衣服"], "respawn": 120},
    {"name": "大腳瑪幽", "tags": ["61", "大腳", "腳"], "respawn": 180},
    {"name": "巨大飛龍", "tags": ["82", "巨非", "巨飛", "飛龍"], "respawn": 360},
    {"name": "86左飛龍", "tags": ["861", "左"], "respawn": 120},
    {"name": "83飛龍", "tags": ["83"], "respawn": 180},
    {"name": "85飛龍", "tags": ["85"], "respawn": 180},
    {"name": "86右飛龍", "tags": ["862", "又", "右"], "respawn": 120},
    {"name": "大黑長者", "tags": ["863", "大黑", "大黑老", "黑", "黑老"], "respawn": 180},
    {"name": "巨大鱷魚", "tags": ["43", "51", "巨鱷", "鱷魚"], "respawn": 180},
    {"name": "巨大蜈蚣", "tags": ["06", "6", "巨型蠕蟲", "海底", "海蟲", "蜈蚣", "蟲"], "respawn": 120},
    {"name": "變形怪首領", "tags": ["變", "變型怪", "變形怪", "變怪"], "respawn": 420},
    {"name": "強盜頭目", "tags": ["27", "28", "強盜"], "respawn": 180},
    {"name": "小綠", "tags": ["46", "54", "G", "g", "綠", "綠王"], "respawn": 120},
    {"name": "小紅", "tags": ["R", "r", "紅", "紅王"], "respawn": 120},
    {"name": "蜘蛛", "tags": ["34", "35", "拉亞"], "respawn": 240},
    {"name": "樹精", "tags": ["191", "20", "491", "樹"], "respawn": 180},
    {"name": "四色", "tags": ["4C", "4c", "4色", "67", "76"], "respawn": 120},
    {"name": "死亡騎士", "tags": ["05", "死騎"], "respawn": 540},
    {"name": "力卡溫", "tags": ["力卡溫", "狼", "狼王", "郎", "郎王"], "respawn": 480},
    {"name": "卡司特", "tags": ["25", "", "卡", "卡王"], "respawn": 450},
    {"name": "克特", "tags": ["12"], "respawn": 600},
    {"name": "古代巨人", "tags": ["69", "70", "古巨", "巨人"], "respawn": 510},
    {"name": "惡魔監視者", "tags": ["7", "監視者", "象7", "象牙塔"], "respawn": 360},
    {"name": "曼波王", "tags": ["曼波王"], "respawn": 480},
    {"name": "精靈監視者", "tags": ["精靈監視者"], "respawn": 240},
    {"name": "貝里斯", "tags": ["72", "將軍", "暗黑大將", "貝"], "respawn": 360},
    {"name": "賽尼斯", "tags": ["304", "賽", "賽尼斯"], "respawn": 180},
    {"name": "烏克庫斯(23王)", "tags": ["23"], "respawn": 360},
    {"name": "奈克偌斯(57王)", "tags": ["57"], "respawn": 240},
    {"name": "巨蟻女皇", "tags": ["25", "26", "螞蟻"], "respawn": 210},
]

spawn_list = []


def now_tw():
    return datetime.now(TW_TZ)


def find_boss(keyword):
    keyword = keyword.strip()
    for b in bosses:
        if keyword == b["name"] or keyword in b["tags"]:
            return b
    return None


def parse_time(time_str):
    now = now_tw()

    if time_str == "6666":
        return now

    if ":" in time_str:
        try:
            t = datetime.strptime(time_str, "%H:%M:%S")
            return now.replace(hour=t.hour, minute=t.minute, second=t.second, microsecond=0)
        except ValueError:
            return None

    if len(time_str) == 4 and time_str.isdigit():
        try:
            hour = int(time_str[:2])
            minute = int(time_str[2:])
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        except ValueError:
            return None

    return None


def add_record(time_str, keyword, note=""):
    boss = find_boss(keyword)
    if not boss:
        return "❌ 找不到王"

    death_time = parse_time(time_str)
    if not death_time:
        return "❌ 時間格式錯誤"

    spawn_time = death_time + timedelta(minutes=boss["respawn"])

    for b in spawn_list:
        if b["name"] == boss["name"]:
            b["time"] = spawn_time
            b["note"] = note
            b["respawn"] = boss["respawn"]
            return (
                f"♻️ 已更新 [{boss['name']}]\n"
                f"死亡時間：{death_time.strftime('%m/%d %H:%M:%S')}\n"
                f"下次出現：{spawn_time.strftime('%m/%d %H:%M:%S')}"
            )

    spawn_list.append({
        "name": boss["name"],
        "time": spawn_time,
        "note": note,
        "respawn": boss["respawn"]
    })

    return (
        f"✅ 新增 [{boss['name']}]\n"
        f"死亡時間：{death_time.strftime('%m/%d %H:%M:%S')}\n"
        f"下次出現：{spawn_time.strftime('%m/%d %H:%M:%S')}\n"
        f"📌 目前共 {len(spawn_list)} 隻王"
    )


def show_table():
    if not spawn_list:
        return "目前沒有紀錄"

    now = now_tw()
    display_list = []

    for b in spawn_list:
        display_time = b["time"]
        respawn_minutes = b["respawn"]
        overdue_count = 0

        while display_time < now:
            display_time += timedelta(minutes=respawn_minutes)
            overdue_count += 1

        diff = int((display_time - now).total_seconds() / 60)

        if diff <= 30:
            status = f"🟡剩{diff}分"
        elif diff <= 60:
            status = f"🟢剩{diff}分"
        else:
            status = f"⚪剩{diff}分"

        if overdue_count > 0:
            note_text = ""
        else:
            note_text = f" #{b['note']}" if b["note"] else ""

        overdue_text = f" (過{overdue_count})" if overdue_count > 0 else ""

        display_list.append({
            "time": display_time,
            "text": f"{display_time.strftime('%H:%M:%S')} {b['name']}{note_text}{overdue_text}（{status}）"
        })

    display_list.sort(key=lambda x: x["time"])

    lines = ["出王時間表："]
    for item in display_list:
        lines.append(item["text"])

    return "\n".join(lines)


def help_text():
    return (
        "🔥 天堂M 王計時系統\n"
        "可用指令：\n"
        "1. 1800 飛龍\n"
        "2. 18:00:00 飛龍 空\n"
        "3. 6666 飛龍 空\n"
        "4. 6666 861 這邊備註\n"
        "5. 6666 861 \"這邊備註 含空格\"\n"
        "6. 出\n"
        "7. 紀錄王數量\n"
        "8. 維護重置\n"
        "9. help"
    )


@app.route("/", methods=["GET"])
def home():
    return "LINE Bot is running"


@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ 簽名錯誤")
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_msg = event.message.text.strip()

    if user_msg == "出":
        reply_text = show_table()

    elif user_msg == "紀錄王數量":
        reply_text = f"📊 目前已紀錄：{len(spawn_list)} 隻"

    elif user_msg == "維護重置":
        spawn_list.clear()
        reply_text = "🔄 已清空所有紀錄"

    elif user_msg.lower() == "help":
        reply_text = help_text()

    else:
        try:
            parts = shlex.split(user_msg)
        except ValueError:
            return

        if len(parts) >= 2:
            time_str = parts[0]
            keyword = parts[1]
            note = " ".join(parts[2:]) if len(parts) >= 3 else ""
            reply_text = add_record(time_str, keyword, note)
        else:
            return

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)