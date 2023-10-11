import os
import urllib.parse
import json
import random

from datetime import datetime, timedelta

from fastapi import Request, FastAPI, HTTPException

from linebot.v3 import (
    WebhookParser
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.webhooks import (
    MessageEvent,
    PostbackEvent,
    TextMessageContent,
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    TemplateMessage,
    ImageMessage,
    ButtonsTemplate,
    PostbackAction,
)


import dynamodb_local
import s3_local

import kakinotane_image

app = FastAPI()


@app.post("/webhook")
def post_webhook():
    print(app.current_event.body)
    print(app.current_event.headers)

    body: dict = app.current_event.json_body
    body_raw = app.current_event.body
    headers = app.current_event.headers

    header_sig = headers["x-line-signature"]

    current_time = datetime.now().timestamp()


    # get channel_secret and channel_access_token from your environment variable
    channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
    channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)

    table_name = os.getenv('TABLE_KAKINOTANE_USER')
    bucket_name = os.getenv('BUCKET_KAKINOTANE')

    if channel_secret is None:
        print('Specify LINE_CHANNEL_SECRET as environment variable.')
        return {}
    if channel_access_token is None:
        print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
        return {}

    parser = WebhookParser(channel_secret)

    configuration = Configuration(
        access_token=channel_access_token
    )

    try:
        events = parser.parse(body_raw, header_sig)
    except InvalidSignatureError:
        raise Exception("Invalid signature")

    for event in events:
        if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
            ratio = random.random()

            correct_ans = "{} % : {} %".format((int)(ratio * 100), (int)((1 - ratio) * 100))
            correct_ans_action = PostbackAction(label=correct_ans, data=correct_ans)

            msg = TemplateMessage(
                    alt_text="test",
                    template=ButtonsTemplate(
                        text="比率は？",
                        actions=[
                            PostbackAction(label=correct_ans, data=correct_ans),
                            PostbackAction(label="test2", data="test2"),
                            PostbackAction(label="test3", data="test3"),
                        ]
                    )
            )

            # kakinotane
            kakinotane_image.create_kakinotane_image(ratio, output_file_name="/tmp/output.jpg")

            # upload file
            output_file_name = "{}.jpg".format(event.source.user_id)
            s3_local.put_object(bucket_name, "/tmp/output.jpg", output_file_name)
            image_url = s3_local.get_public_url(bucket_name, output_file_name)

            # put database
            data = {
                "user_id": event.source.user_id,
                "correct_ans": correct_ans,
            }
            dynamodb_local.put_item(table_name, data)

            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            ImageMessage(originalContentUrl=image_url, previewImageUrl=image_url),
                            msg,
                        ]
                    )
                )
        elif isinstance(event, PostbackEvent):
            # check answer
            print("test")

            userdata = dynamodb.get_item(table_name, event.source.user_id)
            correct_ans = userdata["correct_ans"]


    return {}
