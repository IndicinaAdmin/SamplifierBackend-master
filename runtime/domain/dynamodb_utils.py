from datetime import datetime
from typing import Union

import boto3
from aws_lambda_powertools import Logger

from domain.utils import FileStatus

"""
A collection of functions to handle Database entries
"""


def get_table():
    """
    Gets the DynamoDB table

    Returns:
        the DynamoDB table
    """
    db_conn = boto3.resource("dynamodb")
    ssm = boto3.client("ssm")
    table_name = ssm.get_parameter(Name="/samplifier/dynamodb/table/name")["Parameter"]["Value"]
    db_table = db_conn.Table(table_name)
    return db_table


def update_last_user_upload(db_table, user_id: str, last_upload: datetime):
    """
    Update the last time a user uploaded a file

    Args:
        db_table:
            a manipulable DynamoDB table
        user_id(str):
            a string with the user's id
        last_upload(datetime):
            the datetime of the last upload
    """
    item = {"pk": user_id, "sk": "LastUpload", "lastUpload": last_upload.isoformat()}
    db_table.put_item(Item=item)


def get_last_user_upload(db_table, user_id: str, logger: Logger = None) -> Union[dict, None]:
    """
    Gets the datetime of the last time a user uploaded a file
    Args:
        db_table: a manipulable DynamoDB table
        user_id(str): a string with the user's id
        logger: a logger to log logs
    Returns:
        A dict with the format {"lastUpload": datetime.datetime.isoformat()}
    """
    if logger is not None:
        logger.info("Getting last user upload:\ndb_table: {},\nuser_id: {}".format(db_table, user_id))
    keys = {
        "pk": user_id,
        "sk": "LastUpload",
    }
    try:
        item = db_table.get_item(Key=keys)["Item"]
    except Exception:
        if logger is not None:
            logger.info("No last upload entry on DynamoDB.")
        return None
    if item is None:
        if logger is not None:
            logger.info("No last upload entry on DynamoDB.")
        return None
    if logger is not None:
        logger.info("Retrieved item:\n{}".format(item))

    item.pop("pk")
    item.pop("sk")
    return item


def update_file_status(
    db_table,
    user_id: str,
    file_id: str,
    new_status: FileStatus,
    timestamp: int = 0,
    error_msg: str = None,
    pre_processed_mrsss: dict = None,
    output_metadata: dict = None,
):
    """
    Inserts or updates the status of a submission file at DynamoDB

    Args:
        db_table:
            a manipulable DynamoDB table
        user_id(str):
            a string with the user's id
        file_id(str):
            a string with the file_id in the format <OrganizationId>-<SubmissionId>.xml
        new_status(str):
            a FileStatus with the new file status
        timestamp(int):
            an int with the timestamp of the calculus request.
            Defaults to 0 meaning a new xml file where no calculus where performed yet.
        error_msg(str):
            the error message to be displayed
        pre_processed_mrsss(dict):
            the pre-processed MRSSs for a file
        output_metadata(dict):
            the file metadata that shows on the calculator output page and export files
    """
    new_item = {
        "pk": user_id,
        "sk": "File-{}".format(file_id),
        "status": new_status.value,
        "timestamp": timestamp,
    }
    old_item_retrieved = False  # To avoid making two reads of the old entry in DynamoDB
    old_item = None
    if error_msg is not None:
        new_item["errorMessage"] = error_msg

    if pre_processed_mrsss is not None:
        new_item["preProcessedMrsss"] = pre_processed_mrsss
    else:  # Keep the old preProcessedMrsss
        old_item = get_file_status(db_table=db_table, user_id=user_id, file_id=file_id, timestamp=timestamp)
        old_item_retrieved = True
        if old_item is not None and "preProcessedMrsss" in old_item:
            new_item["preProcessedMrsss"] = old_item["preProcessedMrsss"]

    if output_metadata is not None:
        new_item["outputMetadata"] = output_metadata
    else:  # Keep the old outputMetadata
        if not old_item_retrieved:
            old_item = get_file_status(db_table=db_table, user_id=user_id, file_id=file_id, timestamp=timestamp)
        if old_item is not None and "outputMetadata" in old_item:
            new_item["outputMetadata"] = old_item["outputMetadata"]

    db_table.put_item(Item=new_item)


def get_file_status(db_table, user_id: str, file_id: str, timestamp: int, logger: Logger = None) -> Union[dict, None]:
    """
    Gets the status of a submission file from its corresponding DynamoDb entry
    Args:
        db_table:
        user_id(str): a string with the user's id
        file_id(str): a string with the file_id in the format <OrganizationId>-<SubmissionId>.xml
        timestamp(int): an int with the timestamp of the calculus request
        logger(aws_lambda_powertools.Logger): a Logger to log logs

    Returns:
        A dict with the file's status
    """
    if logger is not None:
        logger.info(
            "Getting file status:\ndb_table: {},\nuser_id: {},\nfile_id: {},\ntimestamp: {}".format(
                db_table, user_id, file_id, timestamp
            )
        )
    keys = {"pk": user_id, "sk": "File-{}".format(file_id)}
    try:
        item = db_table.get_item(Key=keys)["Item"]
    except Exception:
        if logger is not None:
            logger.error("Error on retrieving DynamoDB item.")
        return None
    if logger is not None:
        logger.info("Retrieved item:\n{}".format(item))
    if item is not None:
        # Wrong (old) calculus key
        if "timestamp" not in item or item["timestamp"] not in [0, timestamp]:
            old_timestamp = item["timestamp"] if "timestamp" in item else None
            item = {
                "status": FileStatus.WRONG_TIMESTAMP.value,
                "errorMessage": "We found an previous submission of the same file. Replacing previous file.",
            }
            if old_timestamp is not None:
                item["oldTimestamp"] = old_timestamp
        else:
            item.pop("pk")
            item.pop("sk")
    return item


def update_calculus_parameters(db_table, parameter_name: str, parameters: Union[list, set, dict], logger: Logger = None):
    """
    Inserts or updates a calculus parameter on DynamoDB

    Args:
        db_table: a manipulable DynamoDB table
        parameter_name(str): the name of the calculus parameter
        parameters(str): the attributes of the calculus parameter entry
    """
    item = {"pk": parameter_name, "sk": "CalculusParameter", "parameters": parameters}
    db_table.put_item(Item=item)


def get_calculus_parameters(db_table, parameter_name: str, logger: Logger = None) -> Union[set, dict, None]:
    """
    Gets a calculus parameter from DynamoDB

    Args:
        db_table: a manipulable DynamoDB table
        parameter_name(str): the name of the calculus parameter
    Returns:
        A dict with the stored calculus parameters
    """
    keys = {"pk": parameter_name, "sk": "CalculusParameter"}
    try:
        item = db_table.get_item(Key=keys)["Item"]
        logger.info("Retrieved parameter: {} from DynamoDB table: {}.".format(parameter_name, db_table))
        return set(item["parameters"]) if isinstance(item["parameters"], list) else item["parameters"]
    except Exception as ex:
        if logger is not None:
            logger.error("Error on retrieving parameter: {} from DynamoDB table: {}.".format(parameter_name, db_table))
            logger.error(ex)
        return None
