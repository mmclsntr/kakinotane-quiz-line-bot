import os
import random
import re

from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import LambdaFunctionUrlResolver
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
    QuickReply,
    QuickReplyItem,
    MessageAction,
)


import dynamodb
import s3

import kakinotane_image


logger = Logger()

app = LambdaFunctionUrlResolver()


ANS_TEMPLATE = "{} % : {} %"
ANS_REGEX_PATTERN = r'[0-9]+ % : [0-9]+ %'
MIN_PERCENT = 10
MAX_PERCENT = 90


def generate_kakinotane_image(percentage: int, user_id: str, bucket_name: str) -> str:
    output_local = "/tmp/{}.jpg".format(user_id)
    output_s3 = "{}.jpg".format(user_id)

    # Generate kakinotane image
    kakinotane_image.create_kakinotane_image(percentage * 0.01, output_file_name=output_local)

    # upload image file
    s3.put_object(bucket_name, output_local, output_s3)
    image_url = s3.get_public_url(bucket_name, output_s3)

    return image_url


def create_selections(step: int) -> tuple:
    percent_1 = random.randrange(MIN_PERCENT + step * 2, MAX_PERCENT - step * 2, step)

    if percent_1 + 20 >= MAX_PERCENT:
        percent_2 = percent_1 + random.randrange(0, MAX_PERCENT - percent_1, step) + step
    else:
        percent_2 = percent_1 + random.randrange(0, 20, step) + step

    if percent_1 - 20 <= MIN_PERCENT:
        percent_3 = percent_1 - random.randrange(0, percent_1 - MIN_PERCENT, step) - step
    else:
        percent_3 = percent_1 - random.randrange(0, 20, step) - step

    return percent_1, percent_2, percent_3



@app.post("/webhook")
def post_webhook():
    logger.info(app.current_event.body)
    logger.info(app.current_event.headers)

    body_raw = app.current_event.body
    headers = app.current_event.headers

    header_sig = headers["x-line-signature"]

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
            logger.info(event.message)

            message_text = event.message.text

            pttn = re.compile(ANS_REGEX_PATTERN)
            if pttn.match(message_text) is not None:
                ### Check answer ###

                # check answer
                userdata = dynamodb.get_item(table_name, {"user_id": event.source.user_id})
                correct_ans = userdata["correct_ans"]

                if correct_ans == message_text:
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
                                                action=MessageAction(label="初級", text="初級")
                                            ),
                                            QuickReplyItem(
                                                action=MessageAction(label="中級", text="中級")
                                            ),
                                            QuickReplyItem(
                                                action=MessageAction(label="上級", text="上級")
                                            ),
                                        ]
                                    )
                                ),
                            ]
                        )
                    )
            else:
                ### Create quiz ###

                # select level
                if message_text == "初級":
                    step = 10
                elif message_text == "中級":
                    step = 5
                elif message_text == "上級":
                    step = 1
                else:
                    step = 5

                # create selections
                percent_1, percent_2, percent_3 = create_selections(step)

                correct_percent = random.choice([percent_1, percent_2, percent_3])

                # Generate kakinotane image
                logger.info("ratio: {}".format(correct_percent))

                image_url = generate_kakinotane_image(correct_percent, event.source.user_id, bucket_name)

                correct_ans = ANS_TEMPLATE.format(correct_percent, 100 - correct_percent)
                ans_1 = ANS_TEMPLATE.format(percent_1, 100 - percent_1)
                ans_2 = ANS_TEMPLATE.format(percent_2, 100 - percent_2)
                ans_3 = ANS_TEMPLATE.format(percent_3, 100 - percent_3)

                logger.info("{}: {}  {}  {}".format(correct_ans, ans_1, ans_2, ans_3))

                # put database
                data = {
                    "user_id": event.source.user_id,
                    "correct_ans": correct_ans,
                }
                dynamodb.put_item(table_name, data)

                # create action message
                ans_1_act = MessageAction(label=ans_1, text=ans_1)
                ans_2_act = MessageAction(label=ans_2, text=ans_2)
                ans_3_act = MessageAction(label=ans_3, text=ans_3)
                acts = [
                    ans_1_act,
                    ans_2_act,
                    ans_3_act,
                ]
                random.shuffle(acts)

                msg = TemplateMessage(
                        alt_text="柿の種 : ピーナッツ の比率は？？",
                        template=ButtonsTemplate(
                            text='柿の種 : ピーナッツ の比率は？？',
                            actions=acts
                        )
                )

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

    return {}


# You can continue to use other utilities just as before
@logger.inject_lambda_context(correlation_id_path=correlation_paths.LAMBDA_FUNCTION_URL)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    logger.info(event)
    return app.resolve(event, context)
