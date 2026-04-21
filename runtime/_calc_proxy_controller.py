import json

import jwt
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler.api_gateway import ApiGatewayResolver, CORSConfig, ProxyEventType, Response
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.validation import SchemaValidationError

from domain import dynamodb_utils
from domain.calculator_service import CalculatorService
from domain.utils import CustomEncoder, get_boolean_env_var

log_events = get_boolean_env_var("LOG_EVENTS")  # logging events is useful for debugging
logger = Logger()
tracer = Tracer()
calc_service = CalculatorService(logger=logger)


class NotFoundError(Exception):
    pass


class BadRequestError(Exception):
    pass


class InternalError(Exception):
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

CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_TEXT = "text/plain"


@app.get("/calc/healthcheck")
def healthcheck() -> Response:
    """
    Basic health check
    """
    response = {"Message": "Ok calc api"}
    return Response(status_code=200, content_type=CONTENT_TYPE_JSON, body=json.dumps(response))


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, context):
    logger.info(event)
    logger.info(context)
    return app.resolve(event, context)


@app.get("/calc/filestatus/<user_id>/<file_submission_id>")
@tracer.capture_method
def filestatus_w_user_id(user_id: str, file_submission_id: str) -> Response:
    """
    Gets the status of submission file.
    Args:
        user_id(str):
            A string with the user's id
        file_submission_id(str):
            A string with the format <MeasurementYear>-<OrganizationId>-<SubmissionId>-<Timestamp>.xml
            that identifies a submission

    Returns:
        <HTML_code>: Body
        400: None (Malformed file_submission_id)
        401: None (Unauthorized)
        404: A dict with the errorMessage "File not found." (No entry for the supplied user_id and file_submission_id)
        200: A dict with the file's status (The file is Validated)
        406: A dict with the file's status (The file is Invalid)
        409: A dict with the file's status (The file has a Wrong Timestamp)
        202: A dict with the file's status (The file is Calculated)
        500: A dict with the file's status (Calculus Error)
        201: A dict with the file's status (The file is Exported)
        500: A dict with the file's status (Export Error)
    """

    logger.info(
        "GET filestatus request, relative path: {}/{}/{}".format("/calc/filestatus", user_id, file_submission_id)
    )
    try:
        if not file_submission_id.endswith(".xml"):
            file_submission_id += ".xml"
        # The timestamp that identifies each submission upload for uploads of the same file
        timestamp = 0
        # The file identifier without the timestamp, i.e., <MeasurementYear>-<OrganizationId>-<SubmissionId>.xml
        file_id = ""
        db_table = dynamodb_utils.get_table()
        file_name_parts = file_submission_id.split("-")
        try:
            headers = app.current_event.headers
            token = headers["Authorization"]
            token = token.split(" ")[1]
            decoded = jwt.decode(token, options={"verify_signature": False})
            header_user_id = decoded["sub"]
            if header_user_id != user_id:
                logger.error(
                    "Trying to access files from a different user. Auth header user: {} path user {}".format(
                        header_user_id, user_id
                    )
                )
                return Response(status_code=401, content_type=CONTENT_TYPE_JSON, body=None)
        except Exception:
            logger.info(
                'Failed to load "Authorization" header, '
                + "maybe the function was called directly from the API gateway console."
            )
        if len(file_name_parts) == 4:  # file_name = <MeasurementYear>-<OrganizationId>-<SubmissionId>-<Timestamp>.xml
            file_id = "{}-{}-{}.xml".format(file_name_parts[0], file_name_parts[1], file_name_parts[2])
            timestamp = int(file_name_parts[3][: file_name_parts[3].index(".")])  # Between the last '-' and the '.'

        else:
            logger.error(
                "The file name should follow the format "
                + "<MeasurementYear>-<OrganizationId>-<SubmissionId>-<Timestamp>.xml"
            )
            return Response(status_code=400, content_type=CONTENT_TYPE_JSON, body=None)

        # Get the file status form DynamoDB
        file_status = dynamodb_utils.get_file_status(
            db_table, user_id=user_id, file_id=file_id, timestamp=timestamp, logger=logger
        )
        # If there is a corresponding entry in the database
        if file_status is not None:
            # Will be one of the util.FileStatus values, which correspond to the HTTP code
            http_code = int(file_status["status"])

            # If the file is in one of the processing stages i.e., Validating, Calculating or Exporting
            if http_code % 100 == 1:
                return Response(status_code=http_code, content_type=CONTENT_TYPE_JSON, body=None)
            else:
                return Response(
                    status_code=http_code,
                    content_type=CONTENT_TYPE_JSON,
                    body=json.dumps(file_status, cls=CustomEncoder),
                )
        # There is no corresponding entry in the database
        else:
            logger.error("No entry found for the submission file")
            return Response(
                status_code=404, content_type=CONTENT_TYPE_JSON, body=json.dumps({"errorMessage": "File not found."})
            )
    except (ValueError, TypeError) as e:
        logger.exception("There was an error in the domain service")
        raise BadRequestError() from e


# flake8: noqa: C901
@app.post("/calc/configuration/<user_id>/<file_submission_id>")
@tracer.capture_method
def calculate_configuration_w_user_id(user_id: str, file_submission_id: str) -> Response:  # flake8: noqa: C901
    """
    Calculate the MRSSs for a submission file.
    Args:
        user_id(str):
            A string with the user's id
        file_submission_id(str):
            A string with the format <MeasurementYear>-<OrganizationId>-<SubmissionId>-<Timestamp>.xml
            that identifies a submission

    Returns:
        <HTML_code>: Body
        400: None (Malformed file_submission_id)
        401: None (Unauthorized)
        404: A dict with the errorMessage "File not found." (No entry for the supplied user_id and file_submission_id)
        200: A dict in the format {"outputMetadata": output_metadata, "preProcessedMrsss": mrsss} (Successful calculus)
        500: A dict with errorMessage produced by the calculus or "Unknown calculus error."
    """

    logger.info(
        "POST configuration request, relative path: {}/{}/{}".format("/calc/configuration", user_id, file_submission_id)
    )
    try:
        db_table = dynamodb_utils.get_table()
        try:
            headers = app.current_event.headers
            token = headers["Authorization"]
            token = token.split(" ")[1]
            decoded = jwt.decode(token, options={"verify_signature": False})
            header_user_id = decoded["sub"]
            if header_user_id != user_id:
                logger.error(
                    "Trying to access files from a different user. Auth header user: {} path user {}".format(
                        header_user_id, user_id
                    )
                )
                return Response(status_code=401, content_type=CONTENT_TYPE_JSON, body=None)
        except Exception:
            logger.info(
                'Failed to load "Authorization" header, '
                + "maybe the function was called directly from the API gateway console."
            )
        request_body: dict = app.current_event.json_body
        if not file_submission_id.endswith(".xml"):
            file_submission_id += ".xml"

        file_name_parts = file_submission_id.split("-")
        measurement_year = request_body["measurementYear"] if "measurementYear" in request_body else None
        combine = request_body["combine"] if "combine" in request_body else []
        # The timestamp that identifies each submission upload for submissions of the same file
        timestamp = 0
        # The file identifier without the timestamp, i.e., <MeasurementYear>-<OrganizationId>-<SubmissionId>.xml
        file_id = ""
        if len(file_name_parts) == 4:  # file_name = <MeasurementYear>-<OrganizationId>-<SubmissionId>-<Timestamp>.xml
            file_id = "{}-{}-{}.xml".format(file_name_parts[0], file_name_parts[1], file_name_parts[2])
            timestamp = int(file_name_parts[3][: file_name_parts[3].index(".")])  # Between the last '-' and the '.'
            if measurement_year is not None:
                if str(measurement_year) != file_name_parts[0]:
                    logger.error(
                        "The file name should follow the format "
                        + "<MeasurementYear>-<OrganizationId>-<SubmissionId>-<Timestamp>.xml"
                    )
                    return Response(status_code=400, content_type=CONTENT_TYPE_JSON, body=None)
            else:
                measurement_year = int(file_name_parts[0])
        else:
            logger.error(
                "The file name should follow the format "
                + "<MeasurementYear>-<OrganizationId>-<SubmissionId>-<Timestamp>.xml"
            )
            return Response(status_code=400, content_type=CONTENT_TYPE_JSON, body=None)
        s3Key = "validated/{}/{}".format(user_id, file_id)
        # Get the current file status form DynamoDB
        file_status = dynamodb_utils.get_file_status(
            db_table, user_id=user_id, file_id=file_id, timestamp=timestamp, logger=logger
        )
        # If there is a corresponding entry in the database
        if file_status is not None:
            # Calculate the MRSSs
            if "outputMetadata" in file_status:
                mrsss = calc_service.get_pre_processed_mrsss(
                    user_id=user_id,
                    file_id=file_id,
                    s3_key=s3Key,
                    year=measurement_year,
                    timestamp=timestamp,
                    combine=combine,
                )
                output_metadata = file_status["outputMetadata"]
                # Success
                if mrsss is not None:
                    return Response(
                        status_code=200,
                        content_type=CONTENT_TYPE_JSON,
                        body=json.dumps(
                            {"outputMetadata": output_metadata, "preProcessedMrsss": mrsss}, cls=CustomEncoder
                        ),
                    )
                # Calculus error
                else:
                    # Get the new file status form DynamoDB
                    file_status = dynamodb_utils.get_file_status(
                        db_table, user_id=user_id, file_id=file_id, timestamp=timestamp, logger=logger
                    )
                    # if the MRSSs calculation specified an error in the new file status
                    if (int(file_status["status"]) % 100) not in {1, 2}:
                        return Response(
                            status_code=500,
                            content_type=CONTENT_TYPE_JSON,
                            body=json.dumps({"errorMessage": file_status["errorMessage"]}, cls=CustomEncoder),
                        )
            else:
                return Response(
                    status_code=500,
                    content_type=CONTENT_TYPE_JSON,
                    body=json.dumps({"errorMessage": "File is entry is missing the metadata."}, cls=CustomEncoder),
                )
            return Response(
                status_code=500,
                content_type=CONTENT_TYPE_JSON,
                body=json.dumps({"errorMessage": "Unknown calculus error."}, cls=CustomEncoder),
            )
        # There is no corresponding entry in the database
        else:
            return Response(
                status_code=404, content_type=CONTENT_TYPE_JSON, body=json.dumps({"errorMessage": "File not found."})
            )
    except (ValueError, TypeError, SchemaValidationError) as e:
        logger.error("There was an error in the domain service")
        logger.error(str(e))
        raise BadRequestError() from e


@app.post("/calc/exportcsv/<user_id>/<file_submission_id>")
@tracer.capture_method
def export(user_id: str, file_submission_id: str) -> Response:
    """
    Gets the result exported to a specific format.
    Args:
        user_id(str):
            A string with the user's id
        file_submission_id(str):
            A string with the format <MeasurementYear>-<OrganizationId>-<SubmissionId>-<Timestamp>.xml
            that identifies a submission

    Returns:
        <HTML_code>: Body
        400: None (Malformed file_submission_id)
        404: A dict with the errorMessage "File not found." (No entry for the supplied user_id and file_submission_id)
        201: A file in the chosen format
        500: A dict with the file's status (Export Error)
    """

    logger.info(
        "POST exportcsv request, relative path: {}/{}/{}".format("/calc/exportcsv", user_id, file_submission_id)
    )
    try:
        if not file_submission_id.endswith(".xml"):
            file_submission_id += ".xml"
        # The timestamp that identifies each submission upload for submissions of the same file
        timestamp = 0
        # The file identifier without the timestamp, i.e., <MeasurementYear>-<OrganizationId>-<SubmissionId>.xml
        file_id = ""
        db_table = dynamodb_utils.get_table()
        request_body: dict = app.current_event.json_body
        file_name_parts = file_submission_id.split("-")
        try:
            headers = app.current_event.headers
            token = headers["Authorization"]
            token = token.split(" ")[1]
            decoded = jwt.decode(token, options={"verify_signature": False})
            header_user_id = decoded["sub"]
            if header_user_id != user_id:
                logger.error(
                    "Trying to acess files from a different user. Auth header user: {} path user {}".format(
                        header_user_id, user_id
                    )
                )
                return Response(status_code=401, content_type=CONTENT_TYPE_JSON, body=None)
        except Exception:
            logger.info(
                'Failed to load "Authorization" header, '
                + "maybe the function was called directly from the API gateway console."
            )
        if len(file_name_parts) == 4:  # file_name = <MeasurementYear>-<OrganizationId>-<SubmissionId>-<Timestamp>.xml
            file_id = "{}-{}-{}.xml".format(file_name_parts[0], file_name_parts[1], file_name_parts[2])
            timestamp = int(file_name_parts[3][: file_name_parts[3].index(".")])  # Between the last '-' and the '.'

        else:
            logger.error(
                "The file name should follow the format "
                + "<MeasurementYear>-<OrganizationId>-<SubmissionId>-<Timestamp>.xml"
            )
            return Response(status_code=400, content_type=CONTENT_TYPE_JSON, body=None)

        # Get the file status form DynamoDB
        file_status = dynamodb_utils.get_file_status(
            db_table, user_id=user_id, file_id=file_id, timestamp=timestamp, logger=logger
        )
        # If there is a corresponding entry in the database
        if file_status is not None:
            if request_body is not None and "oversamples" in request_body:
                oversamples = request_body["oversamples"]
                csv = calc_service.export_csv(
                    user_id=user_id, file_id=file_id, timestamp=timestamp, oversamples=oversamples
                )
                return Response(
                    status_code=201,
                    content_type="text/csv",
                    body=csv,
                    headers={"Content-Disposition": "attachment;filename=samplifier-{}.csv".format(file_id)},
                )
            else:
                logger.error("The request body is missing the oversamples")
                return Response(status_code=400, content_type=CONTENT_TYPE_JSON, body=None)

        # There is no corresponding entry in the database
        else:
            logger.error("No entry found for the submission file")
            return Response(
                status_code=404, content_type=CONTENT_TYPE_JSON, body=json.dumps({"errorMessage": "File not found."})
            )
    except (ValueError, TypeError) as e:
        logger.exception("There was an error in the domain service")
        raise BadRequestError() from e


@app.post("/calc/oversamples/<user_id>/<file_submission_id>")
@tracer.capture_method
def save_oversamples(user_id: str, file_submission_id: str) -> Response:
    """
    Saves the result to S3.
    Args:
        user_id(str):
            A string with the user's id
        file_submission_id(str):
            A string with the format <MeasurementYear>-<OrganizationId>-<SubmissionId>-<Timestamp>.xml
            that identifies a submission

    Returns:
        <HTML_code>: Body
        400: None (Malformed file_submission_id)
        401: None (Unauthorized)
        404: A dict with the errorMessage "File not found." (No entry for the supplied user_id and file_submission_id)
        201: Success, the result has been saved
        500: A dict with a errorMessage
    """

    logger.info(
        "POST oversamples request, relative path: {}/{}/{}".format("/calc/oversamples", user_id, file_submission_id)
    )
    try:
        if "." in file_submission_id:  # Remove the extension
            file_submission_id = file_submission_id[: file_submission_id.index(".")]
        # The timestamp that identifies each submission upload for submissions of the same file
        timestamp = 0
        # The file identifier without the timestamp, i.e., <MeasurementYear>-<OrganizationId>-<SubmissionId>.xml
        file_id = ""
        db_table = dynamodb_utils.get_table()
        request_body: dict = app.current_event.json_body
        file_name_parts = file_submission_id.split("-")
        try:
            headers = app.current_event.headers
            token = headers["Authorization"]
            token = token.split(" ")[1]
            decoded = jwt.decode(token, options={"verify_signature": False})
            header_user_id = decoded["sub"]
            if header_user_id != user_id:
                logger.error(
                    "Trying to acess files from a different user. Auth header user: {} path user {}.".format(
                        header_user_id, user_id
                    )
                )
                return Response(status_code=401, content_type=CONTENT_TYPE_JSON, body=None)
        except Exception:
            logger.info(
                'Failed to load "Authorization" header, '
                + "maybe the function was called directly from the API gateway console."
            )
        if len(file_name_parts) == 4:  # file_name = <MeasurementYear>-<OrganizationId>-<SubmissionId>-<Timestamp>.xml
            file_id = "{}-{}-{}.xml".format(file_name_parts[0], file_name_parts[1], file_name_parts[2])
            timestamp = int(file_name_parts[3])
        else:
            logger.error(
                "The file name should follow the format "
                + "<MeasurementYear>-<OrganizationId>-<SubmissionId>-<Timestamp>.xml"
            )
            return Response(status_code=400, content_type=CONTENT_TYPE_JSON, body=None)

        # Get the file status form DynamoDB
        file_status = dynamodb_utils.get_file_status(
            db_table, user_id=user_id, file_id=file_id, timestamp=timestamp, logger=logger
        )
        # If there is a corresponding entry in the database
        if file_status is not None:
            if request_body is not None and "oversamples" in request_body:
                oversamples = request_body["oversamples"]
                save_error = calc_service.save_oversamples(
                    user_id=user_id, file_submission_id=file_submission_id, oversamples=oversamples
                )
                if save_error is None:
                    return Response(status_code=201, content_type=CONTENT_TYPE_JSON, body=None)
                else:
                    return Response(
                        status_code=500, content_type=CONTENT_TYPE_JSON, body=json.dumps({"errorMessage": save_error})
                    )
            else:
                logger.error("The request body is missing the oversamples.")
                return Response(status_code=400, content_type=CONTENT_TYPE_JSON, body=None)
        # There is no corresponding entry in the database
        else:
            logger.error("No entry found for the submission file.")
            return Response(
                status_code=404, content_type=CONTENT_TYPE_JSON, body=json.dumps({"errorMessage": "File not found."})
            )
    except (ValueError, TypeError) as e:
        logger.exception("There was an error in the domain service.")
        raise BadRequestError() from e
