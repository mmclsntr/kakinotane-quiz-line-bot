import os
import urllib.parse
import json
import random

from datetime import datetime, timedelta

from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import LambdaFunctionUrlResolver, Response, content_types, CORSConfig
from aws_lambda_powertools.event_handler.exceptions import (
    NotFoundError,
)
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext

from linebot.v3 import (
    WebhookParser
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.webhooks import (
    MessageEvent,
    PostbackEvent,
    FollowEvent,
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
    QuickReply,
    QuickReplyItem,
    MessageAction,
)


import dynamodb
import s3

import kakinotane_image

logger = Logger()

app = LambdaFunctionUrlResolver()


@app.post("/webhook")
def post_webhook():
    logger.info(app.current_event.body)
    logger.info(app.current_event.headers)

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
        logger.error('Specify LINE_CHANNEL_SECRET as environment variable.')
        return {}
    if channel_access_token is None:
        logger.error('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
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
        if isinstance(event, FollowEvent):
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(
                                text="柿の種とピーナッツの比率を当てるゲームです。",
                                quick_reply=QuickReply(
                                    items=[
                                        QuickReplyItem(
                                            action=MessageAction(label="スタート", text="スタート")
                                        ),
                                    ]
                                )
                            ),
                        ]
                    )
                )
        elif isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
            ratio = random.random()

            correct_percent = (int)(ratio * 100)
            dummy_percent_1 = correct_percent + random.randint(-10, 10)
            dummy_percent_2 = correct_percent - random.randint(-10, 10)

            correct_ans = "{} % : {} %".format(correct_percent, 100 - correct_percent)
            dummy_ans_1 = "{} % : {} %".format(dummy_percent_1, 100 - dummy_percent_1)
            dummy_ans_2 = "{} % : {} %".format(dummy_percent_2, 100 - dummy_percent_2)

            correct_ans_act = PostbackAction(label=correct_ans, data=correct_ans)
            dummy_ans_1_act = PostbackAction(label=dummy_ans_1, data=dummy_ans_1)
            dummy_ans_2_act = PostbackAction(label=dummy_ans_2, data=dummy_ans_2)
            acts = [
                correct_ans_act,
                dummy_ans_1_act,
                dummy_ans_2_act,
            ]

            random.shuffle(acts)

            msg = TemplateMessage(
                    alt_text="test",
                    template=ButtonsTemplate(
                        text='柿の種 : ピーナッツ の比率は？？',
                        actions=acts
                    )
            )

            # kakinotane
            kakinotane_image.create_kakinotane_image(ratio, output_file_name="/tmp/output.jpg")

            # upload file
            output_file_name = "{}.jpg".format(event.source.user_id)
            s3.put_object(bucket_name, "/tmp/output.jpg", output_file_name)
            image_url = s3.get_public_url(bucket_name, output_file_name)

            # put database
            data = {
                "user_id": event.source.user_id,
                "correct_ans": correct_ans,
            }
            dynamodb.put_item(table_name, data)

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
            logger.info("test")

            postback_data = event.postback.data

            userdata = dynamodb.get_item(table_name, {"user_id": event.source.user_id})
            correct_ans = userdata["correct_ans"]

            if correct_ans == postback_data:
                msg = "正解！"
            else:
                msg = "ざんねーん"

            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(
                                text=msg,
                                quick_reply=QuickReply(
                                    items=[
                                        QuickReplyItem(
                                            action=MessageAction(label="次へ", text="次へ")
                                        ),
                                    ]
                                )
                            ),
                        ]
                    )
                )


    return {}


# You can continue to use other utilities just as before
@logger.inject_lambda_context(correlation_id_path=correlation_paths.LAMBDA_FUNCTION_URL)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    logger.info(event)
    return app.resolve(event, context)
