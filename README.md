# Kakinotane Quiz LINE Bot

![arch](docs/kakitaipi_arch.png)

# Requirements
- Serverless Framework
- AWS CLI

# Deploy

```sh
sls deploy \
    --param="line_channel_secret={LINE Channel Secret}" \
    --param="line_access_token={LINE Access Token}" \
    --aws-profile {aws profile}
```
