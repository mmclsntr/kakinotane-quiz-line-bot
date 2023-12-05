FROM public.ecr.aws/lambda/python:3.8-arm64

RUN yum update -y && yum install -y mesa-libGL mesa-libGL-devel mesa-libGLU-devel libpng-devel

COPY . ./
RUN pip install -r requirements.txt

CMD ["line_webhook_lambda_handler.lambda_handler"]
