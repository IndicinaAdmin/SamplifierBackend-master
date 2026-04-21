import runtime._calc_proxy_controller as c
from aws_lambda_powertools.utilities.typing import LambdaContext
context = LambdaContext

file_name = "2022-44444-33333-1701214402659.xml"
user_pool = 'us-east-1_4vcI0N3vV'
client_id = '5q1h64jcojrkb85ulsnhi6a59l'
identity_pool_id = "us-east-1:b0bb612d-08fc-41ba-a10c-45d03eb7a9d6"

def test_calc():
    from flow.Auth import Auth
    auth = Auth(user_pool, client_id, identity_pool_id)
    auth.authenticate("flavio.gomes+1@francioni.co", "Welcome1!")
    cognito_sub = auth.get_sub()
    access_token = auth.get_access_token

    event = {
        "resource": "/calc/{proxy+}",
        "path": f"/calc/filestatus/{cognito_sub}/{file_name}",
        "httpMethod": "GET",
        "headers": {
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Authorization": f"Bearer {access_token}",
            "Host": "api.dev.samplifier.app",
            "origin": "https://dev.samplifier.app",
            "referer": "https://dev.samplifier.app/",
            "sec-ch-ua": "\"Google Chrome\";v=\"119\", \"Chromium\";v=\"119\", \"Not?A_Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"macOS\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "X-Amzn-Trace-Id": "Root=1-656678c8-48062fc86aec37e62ccf1202",
            "X-Forwarded-For": "37.228.243.133",
            "X-Forwarded-Port": "443",
            "X-Forwarded-Proto": "https"
        },
        "multiValueHeaders": {
            "accept": [
                "application/json, text/plain, */*"
            ],
            "accept-encoding": [
                "gzip, deflate, br"
            ],
            "accept-language": [
                "en-GB,en-US;q=0.9,en;q=0.8"
            ],
            "Authorization": [
                f"Bearer {access_token}"
            ],
            "Host": [
                "api.dev.samplifier.app"
            ],
            "origin": [
                "https://dev.samplifier.app"
            ],
            "referer": [
                "https://dev.samplifier.app/"
            ],
            "sec-ch-ua": [
                "\"Google Chrome\";v=\"119\", \"Chromium\";v=\"119\", \"Not?A_Brand\";v=\"24\""
            ],
            "sec-ch-ua-mobile": [
                "?0"
            ],
            "sec-ch-ua-platform": [
                "\"macOS\""
            ],
            "sec-fetch-dest": [
                "empty"
            ],
            "sec-fetch-mode": [
                "cors"
            ],
            "sec-fetch-site": [
                "same-site"
            ],
            "User-Agent": [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            ],
            "X-Amzn-Trace-Id": [
                "Root=1-656678c8-48062fc86aec37e62ccf1202"
            ],
            "X-Forwarded-For": [
                "37.228.243.133"
            ],
            "X-Forwarded-Port": [
                "443"
            ],
            "X-Forwarded-Proto": [
                "https"
            ]
        },
        "queryStringParameters": None,
        "multiValueQueryStringParameters": None,
        "pathParameters": {
            "proxy": f"filestatus/{cognito_sub}/{file_name}"
        },
        "stageVariables": None,
        "requestContext": {
            "resourceId": "1xhlxw",
            "authorizer": {
                "claims": {
                    "sub": cognito_sub,
                    "email_verified": "true",
                    "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_4vcI0N3vV",
                    "cognito:username": cognito_sub,
                    "given_name": "Flavio",
                    "origin_jti": "35275777-b19b-469e-b946-20272124bda1",
                    "aud": "5q1h64jcojrkb85ulsnhi6a59l",
                    "event_id": "bfb91b26-4dea-4609-8354-d5abfe82286d",
                    "token_use": "id",
                    "auth_time": "1701214379",
                    "custom:companyName": "Francioni",
                    "exp": "Tue Nov 28 23:47:59 UTC 2023",
                    "iat": "Tue Nov 28 23:32:59 UTC 2023",
                    "family_name": "Gomes",
                    "jti": "0f5bc0a1-70ef-43cb-b2d2-ea6ccb69462b",
                    "email": "flavio.gomes+1@francioni.co"
                }
            },
            "resourcePath": "/calc/{proxy+}",
            "httpMethod": "GET",
            "extendedRequestId": "PIfPUEhJoAMEoxg=",
            "requestTime": "28/Nov/2023:23:33:28 +0000",
            "path": f"/calc/filestatus/{cognito_sub}/{file_name}",
            "accountId": "267274201794",
            "protocol": "HTTP/1.1",
            "stage": "v1",
            "domainPrefix": "api",
            "requestTimeEpoch": 1701214408166,
            "requestId": "75a7ccd4-5193-4361-88ff-3c0e264bad06",
            "identity": {
                "cognitoIdentityPoolId": None,
                "accountId": None,
                "cognitoIdentityId": None,
                "caller": None,
                "sourceIp": "37.228.243.133",
                "principalOrgId": None,
                "accessKey": None,
                "cognitoAuthenticationType": None,
                "cognitoAuthenticationProvider": None,
                "userArn": None,
                "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "user": None
            },
            "domainName": "api.dev.samplifier.app",
            "apiId": "obvptl5h5e"
        },
        "body": None,
        "isBase64Encoded": False
    }

    response = c.handler(event, context)
    print("=====")
    print(response)
    assert response["statusCode"] == 200

