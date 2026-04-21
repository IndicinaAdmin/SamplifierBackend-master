import json
from datetime import datetime, timedelta, timezone

import jwt
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler.api_gateway import ApiGatewayResolver, CORSConfig, ProxyEventType, Response
from aws_lambda_powertools.event_handler.exceptions import UnauthorizedError

from domain import dynamodb_utils
from domain.user_service import UserService
from domain.utils import get_boolean_env_var

log_events = get_boolean_env_var("LOG_EVENTS")  # logging events is usefull for debugging
logger = Logger()
tracer = Tracer()


class BadRequestError(Exception):
    pass


app = ApiGatewayResolver(
    proxy_type=ProxyEventType.APIGatewayProxyEvent,
    cors=CORSConfig(
        allow_origin="*",
        expose_headers=["x-exposed-response-header"],
        allow_headers=["x-custom-request-header"],
        max_age=100,
        allow_credentials=True,
    ),
)

CONTENT_TYPE = "application/json"


@app.get("/user/healthcheck")
def healthcheck() -> Response:
    response = {"Message": "Ok user api healthcheck"}
    return Response(status_code=200, content_type=CONTENT_TYPE, body=json.dumps(response))


@app.delete("/user/<user_name>")
@tracer.capture_method
def deleteUser(user_name) -> Response:
    logger.info("DELETE user request, relative path: {}/{}".format("/user", user_name))
    app_metadata = {"action": "DeleteUser", "pathParams": {"username": user_name}}
    try:
        headers = app.current_event.headers
        token = headers["Authorization"]
        token = token.split(" ")[1]
        decoded = jwt.decode(token, options={"verify_signature": False})
        header_user_name = decoded["cognito:username"]
        app_metadata.update(
            {
                "email": str(decoded["email"]),
                "username": str(decoded["cognito:username"]),
                "sub": str(decoded["sub"]),
            }
        )
        if header_user_name != user_name:
            logger.error(
                "Trying to delete account from a different user. Auth header user: {} path user {}".format(
                    header_user_name, user_name
                )
            )
            raise UnauthorizedError("Unauthorized")

        user_service = UserService(logger)
        user_service.delete_user(user_name)
        app_metadata.update({"resultCode": 200, "resultMessage": "Success"})
        logger.info(json.dumps({"appMetadata": app_metadata}))

        response = {"Message": "User deleted"}
        return Response(status_code=200, content_type=CONTENT_TYPE, body=json.dumps(response))
    except UnauthorizedError as err:
        logger.error(str(err))
        app_metadata.update({"resultCode": 401, "resultMessage": "Unauthorized", "pythonException": str(err)})
        logger.info(json.dumps({"appMetadata": app_metadata}))
        return Response(status_code=401, content_type=CONTENT_TYPE, body=None)
    except RuntimeError as err:
        logger.error(str(err))
        app_metadata.update({"resultCode": 401, "resultMessage": "Runtime Error", "pythonException": str(err)})
        logger.info(json.dumps({"appMetadata": app_metadata}))
        return Response(status_code=500, content_type=CONTENT_TYPE, body=None)


@app.get("/user/allow-new-upload/<user_id>")
@tracer.capture_method
def allowUserUpload(user_id) -> Response:
    """
    Checks if the user has not uploaded a file in the last 3 seconds and therefore is allowed to upload a new file.
    Also tells how long the frontend should wait before uploading again.
    Args:
        user_id(str): a string with the user's id

    Returns:
        <HTML_code>: Body
        200: None
        429: A dict with the format:
            {
                "waitTime": <the time to wait in seconds before a new submission>
            }
    """
    app_metadata = {"action": "AllowNewUpload", "pathParams": {"user_id": user_id}}
    try:
        logger.info("GET allow upload request, relative path: {}/{}".format("/user/allow-new-upload", user_id))
        db_table = dynamodb_utils.get_table()
        last_upload_on_db = dynamodb_utils.get_last_user_upload(db_table=db_table, user_id=user_id)
        if last_upload_on_db is None:
            return Response(status_code=200, content_type=CONTENT_TYPE, body=None)
        last_upload_datetime = datetime.fromisoformat(last_upload_on_db["lastUpload"])
        now = datetime.now(timezone.utc)
        delta = now - last_upload_datetime
        logger.debug("Delta since last upload: {}".format(str(delta)))
        app_metadata["timedeltaSinceLastUpload"] = str(delta)
        if delta < timedelta(seconds=3):
            app_metadata.update(
                {
                    "resultCode": 401,
                    "resultMessage": "Too soon",
                }
            )
            logger.info(json.dumps({"appMetadata": app_metadata}))
            return Response(
                status_code=429, content_type=CONTENT_TYPE, body=json.dumps({"waitTime": (3 - delta.seconds)})
            )
        else:
            app_metadata.update(
                {
                    "resultCode": 200,
                    "resultMessage": "Allowed",
                }
            )
            logger.info(json.dumps({"appMetadata": app_metadata}))
            return Response(status_code=200, content_type=CONTENT_TYPE, body=None)
    except (ValueError, TypeError) as err:
        logger.error("There was an error in the domain service")
        app_metadata.update({"resultCode": 401, "resultMessage": "Runtime Error", "pythonException": str(err)})
        logger.info(json.dumps({"appMetadata": app_metadata}))
        raise BadRequestError() from err


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, context):
    return app.resolve(event, context)
