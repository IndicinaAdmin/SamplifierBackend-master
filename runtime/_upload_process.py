import gc
import json
import urllib.parse as url_parser
import xml.etree.ElementTree as ET

import boto3
from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.tracing import Tracer

from domain.dynamodb_utils import update_calculus_parameters, update_file_status, update_last_user_upload
from domain.utils import ConfigFileType, FileStatus, find_and_parse_int, parse_boolean

logger = Logger()
tracer = Tracer()

log_events = None
s3 = None
ssm = None
table_name = None
db_table = None
COMPATIBLE_CSV_SEPS = [",", ";", "|", "\t", " "]


def _copy_to(dest_folder: str, bucket_name: str, key: str, dest_file_name: str = None, del_original: bool = False):
    """
    Copies a file in s3 to another folder.

    Args:
        dest_folder(str): a string with the destiny folder
        bucket_name(str): the S3 bucket
        key(str): the original file's S3 key
        dest_file_name(str, optional): a string to change the name of the destiny file
        del_original(bool, optional): if true deletes the original file, effectively moving the file
    """
    global logger, db_table, s3
    file_path = key.split("/")
    if dest_file_name:
        file_path[-1] = dest_file_name
    dest_key = dest_folder

    for path_node in file_path[1:]:
        dest_key += "/{}".format(path_node)

    s3.copy_object(Bucket=bucket_name, Key=dest_key, CopySource={"Bucket": bucket_name, "Key": key})
    if del_original:
        s3.delete_object(Bucket=bucket_name, Key=key)


# flake8: noqa: C901
def _handle_new_xml(xml_string: str, bucket_name: str, key: str):  # flake8: noqa: C901
    """
    Handles a new XML submission.

    Args:
        xml_string(str): the file as a xml_string
        bucket_name(str): the S3 bucket
        key(str): the file's key
    """
    global logger, db_table

    logger.info("Processing new submission file {}".format(key))

    timestamp = 0  # The timestamp that identifies each submission upload among other submissions of the same file
    file_id = ""  # The file identifier without the timestamp, i.e., <OrganizationId>-<SubmissionId>.xml
    # key = pending/<user_id>/<file_name>
    _, user_id, file_name = key.split("/")

    file_name_parts = file_name.split("-")
    logger.info(file_name_parts)
    if len(file_name_parts) == 4:  # file_name = <MeasurementYear>-<OrganizationId>-<SubmissionId>-<Timestamp>.xml
        file_id = "{}-{}-{}.xml".format(file_name_parts[0], file_name_parts[1], file_name_parts[2])
        timestamp = int(file_name_parts[3][: file_name_parts[3].index(".")])

    else:
        logger.error(
            "The file name should follow the format <MeasurementYear>-<OrganizationId>-<SubmissionId>-<Timestamp>.xml"
        )
        update_file_status(
            db_table=db_table,
            user_id=user_id,
            file_id="INVALID-" + file_name,
            new_status=FileStatus.INVALID,
            timestamp=timestamp,
            error_msg=(
                "There was an error in the upload process. "
                + "Please try check if your file has an OrganizationId and SubmissionId and try again."
            ),
        )
        _copy_to("invalid", bucket_name, key, del_original=True)
        return

    try:
        xml_root = ET.fromstring(xml_string)
    except Exception as ex:
        logger.error("Cannot parse file {} to xml tree".format(key))
        logger.error(str(ex))
        update_file_status(
            db_table=db_table,
            user_id=user_id,
            file_id=file_id,
            new_status=FileStatus.INVALID,
            timestamp=timestamp,
            error_msg="Can not parse file to xml tree.",
        )
        _copy_to("invalid", bucket_name, key, dest_file_name=file_id, del_original=True)
        return
    # Submission is the root element, extract the Metadata 2nd level element.
    metadata = xml_root.find("Metadata")
    del xml_root
    gc.collect()
    if metadata is None:
        logger.error("Can not find Metadata element in the file {}".format(key))
        update_file_status(
            db_table=db_table,
            user_id=user_id,
            file_id=file_id,
            new_status=FileStatus.INVALID,
            error_msg="Can not find Metadata element in the file.",
        )
        _copy_to("invalid", bucket_name, key, dest_file_name=file_id, del_original=True)
        return
    submission_id = metadata.find("SubmissionId")
    if submission_id is None:
        update_file_status(
            db_table=db_table,
            user_id=user_id,
            file_id=file_id,
            new_status=FileStatus.INVALID,
            timestamp=timestamp,
            error_msg="File is missing the SubmissionId metadata",
        )
        logger.error("Invalid file {}. Missing the SubmissionId metadata".format(key))
        _copy_to("invalid", bucket_name, key, dest_file_name=file_id, del_original=True)
        return
    elif submission_id.text != file_name_parts[-2]:  # The second to last is always the submission id
        update_file_status(
            db_table=db_table,
            user_id=user_id,
            file_id=file_id,
            new_status=FileStatus.INVALID,
            timestamp=timestamp,
            error_msg=(
                "There was an error in the upload process. "
                + "The SubmssionId in the file name diverges from the file's metadata SubmissionId."
            ),
        )
        logger.error(
            str(
                "This is probably a front end error. "
                + "Invalid file {} the SubmissionId metadata diverges from the SubmissionId in the file name."
            ).format(key)
        )
        _copy_to("invalid", bucket_name, key, dest_file_name=file_id, del_original=True)
        return
    organization_id = metadata.find("OrganizationId")
    if organization_id is None:
        update_file_status(
            db_table=db_table,
            user_id=user_id,
            file_id=file_id,
            new_status=FileStatus.INVALID,
            timestamp=timestamp,
            error_msg="File is missing the OrganizationId metadata.",
        )
        logger.error("Invalid file {} missing the OrganizationId metadata".format(key))
        _copy_to("invalid", bucket_name, key, dest_file_name=file_id, del_original=True)
        return
    elif organization_id.text != file_name_parts[-3]:  # The third to last is always the submission id
        update_file_status(
            db_table=db_table,
            user_id=user_id,
            file_id=file_id,
            new_status=FileStatus.INVALID,
            timestamp=timestamp,
            error_msg=(
                "There was an error in the upload process. "
                + "The OrganizationId in the file name diverges from the file's real OrganizationId."
            ),
        )
        logger.error(
            str(
                "This is probably a front end error. Invalid file {} "
                + "the OrganizationId metadata diverges from the OrganizationId in the file name."
            ).format(key)
        )
        _copy_to("invalid", bucket_name, key, dest_file_name=file_id, del_original=True)
        return
    organization_name = metadata.find("OrganizationName")
    if organization_name is None:
        update_file_status(
            db_table=db_table,
            user_id=user_id,
            file_id=file_id,
            new_status=FileStatus.INVALID,
            timestamp=timestamp,
            error_msg="File is missing the OrganizationName metadata",
        )
        logger.error("Invalid file {} missing the OrganizationName metadata.".format(key))
        _copy_to("invalid", bucket_name, key, dest_file_name=file_id, del_original=True)
        return
    reporting_product = metadata.find("ReportingProduct")
    if reporting_product is None:
        update_file_status(
            db_table=db_table,
            user_id=user_id,
            file_id=file_id,
            new_status=FileStatus.INVALID,
            timestamp=timestamp,
            error_msg="File is missing the ReportingProduct metadata",
        )
        logger.error("Invalid file {} missing the ReportingProduct metadata.".format(key))
        _copy_to("invalid", bucket_name, key, dest_file_name=file_id, del_original=True)
        return

    product_line = metadata.find("ProductLine")
    if product_line is None:
        update_file_status(
            db_table=db_table,
            user_id=user_id,
            file_id=file_id,
            new_status=FileStatus.INVALID,
            timestamp=timestamp,
            error_msg="File is missing the ProductLine metadata.",
        )
        logger.error("Invalid file {} missing the ProductLine metadata.".format(key))
        _copy_to("invalid", bucket_name, key, dest_file_name=file_id, del_original=True)
        return

    special_project = metadata.find("SpecialProject")
    if product_line.text == "Medicare" and special_project is None:
        update_file_status(
            db_table=db_table,
            user_id=user_id,
            file_id=file_id,
            new_status=FileStatus.INVALID,
            timestamp=timestamp,
            error_msg="File's ProductLine is Medicare but it is missing the SpecialProject metadata.",
        )
        logger.error(
            "Invalid file {} ProductLine is Medicare but it is missing the SpecialProject metadata.".format(key)
        )
        _copy_to("invalid", bucket_name, key, dest_file_name=file_id, del_original=True)
        return

    measurement_year = metadata.find("MeasurementYear")
    if measurement_year is None:
        update_file_status(
            db_table=db_table,
            user_id=user_id,
            file_id=file_id,
            new_status=FileStatus.INVALID,
            timestamp=timestamp,
            error_msg="File is missing the MeasurementYear metadata",
        )
        logger.error("Invalid file {} missing the MeasurementYear metadata.".format(key))
        _copy_to("invalid", bucket_name, key, dest_file_name=file_id, del_original=True)
        return

    audited = metadata.find("IsAuditable")
    if audited is None:
        update_file_status(
            db_table=db_table,
            user_id=user_id,
            file_id=file_id,
            new_status=FileStatus.INVALID,
            timestamp=timestamp,
            error_msg="File is missing the IsAuditable metadata",
        )
        logger.error("Invalid file {} missing the IsAuditable metadata.".format(key))
        _copy_to("invalid", bucket_name, key, dest_file_name=file_id, del_original=True)
        return

    logger.info("File {} successfully validated".format(key))

    _copy_to("validated", bucket_name, key, dest_file_name=file_id, del_original=True)

    if special_project is not None and special_project.text is not None and special_project.text != "None":
        if special_project.text.startswith("CMS"):  # CMS means MedicareMA
            special_project_value = "MA"
        else:
            special_project_value = special_project.text
    else:
        special_project_value = " "
    output_metadata = {
        "audited": parse_boolean(audited.text),
        "organizationName": organization_name.text,
        "productLine": product_line.text,
        "specialProject": special_project_value,
        "reportingProduct": reporting_product.text,
        "organizationId": organization_id.text,
        "submissionId": submission_id.text,
    }
    update_file_status(
        db_table=db_table,
        user_id=user_id,
        file_id=file_id,
        new_status=FileStatus.VALID,
        timestamp=timestamp,
        error_msg="No Error",
        output_metadata=output_metadata,
    )
    logger.info("File metadata added to the file entry on DynamoDB".format(key))


def _handle_new_config_file(file_as_string: str, bucket_name: str, key: str):
    """
    Handles the insertion of new configuration file.
    Args:
        file_as_string(str): a string with the file's content
        bucket_name(str): the S3 bucket name
        key(str): the file's key
    """
    global logger, db_table, COMPATIBLE_CSV_SEPS

    logger.info("Processing new config file {}".format(key))

    parameters = {}

    # key = configs/<config_file_type>/<year>/<file_name>
    file_path = key.split("/")
    if len(file_path) < 4:
        logger.error("Invalid config path {}".format(key))
        return

    if file_path[1] == ConfigFileType.REFERENCE_ARRAY.value and (
        file_path[-1].endswith(".csv") or file_path[-1].endswith(".CSV")
    ):  # csv file

        rows = file_as_string.splitlines()

        for i in range(len(rows)):
            if not (
                "inimum" in rows[i]
                or "mrss" in rows[i]
                or "MRSS" in rows[i]
                or rows[i] == ""  # skip headers
                or rows[i] == " "
                or rows[i] == "\t"  # skip empty rows
            ):
                rows = rows[i:]
                break

        sep = None
        # Find the file's separator
        for sep_candidate in COMPATIBLE_CSV_SEPS:
            if len(rows[0].split(sep_candidate)) == 2:
                sep = sep_candidate
                break
        if sep is None:
            logger.error(
                (
                    "Invalid file {} each file line must contain a percentage rate and a MRSS, "
                    + "separated by either of the following separators: {}"
                ).format(key, COMPATIBLE_CSV_SEPS)
            )
            return

        for row in rows:
            if row == "" or row == " " or row == "\t":  # skip empty rows
                continue
            # The numbers may be preceded by '≤' for instance
            dirty_numbers = row.split(sep)
            if len(dirty_numbers) != 2:
                logger.error("Invalid file {} each file line must contain a percentage rate and a MRSS".format(key))
                return
            parameters[str(find_and_parse_int(dirty_numbers[0]))] = find_and_parse_int(dirty_numbers[1])

    elif (  # Checks if the configuration file has a valid Configuration File Type
        file_path[1] == ConfigFileType.MEASURES_PER_PRODUCT.value
        or file_path[1] == ConfigFileType.MEASURES_PER_YEAR.value
        or file_path[1] == ConfigFileType.REFERENCE_ARRAY.value
        or file_path[1] == ConfigFileType.SINGLE_RATE_MEASURES.value
        or file_path[1] == ConfigFileType.MULTI_RATE_MEASURES.value
    ):  # json file
        parameters = json.loads(file_as_string)
    else:
        logger.error("File {} has is in an invalid path and will be moved to invalid folder".format(key))
        _copy_to(dest_folder="invalid", bucket_name=bucket_name, key=key, del_original=True)
        return

    # parameter_name = <config_file_type><year>
    parameter_name = "{}-{}".format(file_path[1], file_path[2])

    logger.info("Inserting parameters of {} in DynamoDB".format(key))
    update_calculus_parameters(db_table=db_table, parameter_name=parameter_name, parameters=parameters)


@logger.inject_lambda_context(log_event=log_events, clear_state=True)
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Processes the insertion of a new file to S3.

    Args:
        event: the event generated by the file insertion
    """
    global logger, s3, ssm, table_name, db_table
    s3 = boto3.client("s3")
    ssm = boto3.client("ssm")
    table_name = ssm.get_parameter(Name="/samplifier/dynamodb/table/name")["Parameter"]["Value"]
    db_table = boto3.resource("dynamodb").Table(table_name)

    bucket = event["Records"][0]["s3"]["bucket"]["name"]  # the S3 bucket

    # The object key is analog to a file path inside a bucket
    key = url_parser.unquote_plus(event["Records"][0]["s3"]["object"]["key"], encoding="utf-8")

    logger.info("Starting to process uploaded file {}".format(key))

    # The s3 object representation of the first record
    s3_object = s3.get_object(Bucket=bucket, Key=key)
    file_as_string = bytes(s3_object["Body"].read()).decode("utf-8")

    # Switch key.startswith handle file depending on the path.
    if key.startswith("pending/"):  # should be a new xml submission
        user_id = key.split("/")[1]
        update_last_user_upload(db_table=db_table, user_id=user_id, last_upload=s3_object["LastModified"])
        logger.info("File {} submitted".format(key))
        if key[-4:].lower() == ".xml":
            _handle_new_xml(xml_string=file_as_string, bucket_name=bucket, key=key)
        else:
            logger.error("File {} submitted with invalid extension {}".format(key, key[-4:]))

    elif key.startswith("validated/"):  # should be a validated file
        logger.info("File {} validated".format(key))

    elif key.startswith("invalid/"):  # should be an invalid file
        logger.info("File {} invalid".format(key))

    elif key.startswith("results/"):  # should be an export file
        logger.info("File {} exported".format(key))

    elif key.startswith("configs/"):  # should be a configuration
        logger.info("New configuration file {}".format(key))
        _handle_new_config_file(file_as_string=file_as_string, bucket_name=bucket, key=key)

    else:
        logger.error("File submitted to invalid path and will be deleted!\nFile key: {}\nEvent: {}".format(key, event))
        s3.delete_object(Bucket=bucket, Key=key)
    return "ok"
