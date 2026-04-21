import gc
import json
import re
import xml.etree.ElementTree as ET
from math import ceil
from re import Pattern
from typing import Tuple, Union

import boto3
from aws_lambda_powertools import Logger

from domain.dynamodb_utils import get_calculus_parameters, get_file_status, get_table, update_file_status
from domain.utils import ConfigFileType, FileStatus, find_and_parse_int, parse_boolean


def _get_mrss_for_rate(reference_array: dict, ordered_rates: list, rate: int, logger: Logger) -> int:
    """
    Gets the MRSS for a given rate using the reference array
    Args:
        reference_array(dict): the reference array with rate to MRSS relations
        ordered_rates(list): a list with the rates in the reference array ordered
        rate(int): the rate

    Returns:
        an int with the MRSS
    """
    # If rate is lower than the minimum value
    if rate < ordered_rates[0]:
        return reference_array[str(ordered_rates[0])]
    # If rate is higher than the maximum value on the reference array
    if rate > ordered_rates[-1]:
        return reference_array[str(ordered_rates[-1])]

    return reference_array[str(rate)]


class CalculatorService:
    """
    Executes the Samplifier calculations
    """

    class MockLogger:
        """
        A mock logger to avoid errors if no Logger is provided
        """

        def __init__(self):
            pass

        def info(self, *args, **kwargs):
            pass

        def error(self, *args, **kwargs):
            pass

    # ----- Class attributes

    logger: Union[Logger, MockLogger]  # A logger to log logs
    s3: object  # A S3 boto client
    db_table: object  # A DynamoDB table
    bucket_name: str  # The S3 bucket's name
    only_alpha: Pattern  # A regex pattern to filter only alphabetic chars

    def __init__(self, logger: Union[Logger, MockLogger] = None):
        self.only_alpha = re.compile("[^a-zA-Z]")
        self.s3 = boto3.client("s3")
        self.db_table = get_table()
        ssm = boto3.client("ssm")
        self.bucket_name = ssm.get_parameter(Name="/samplifier/backend/bucketcalc/name")["Parameter"]["Value"]
        if logger is None:
            self.logger = self.MockLogger()
        else:
            self.logger = logger

    def get_eligible_measures_per_year(self, year) -> Tuple[Union[set, None], Union[str, None]]:
        """
        Gets the list of eligible measures for a measurement year.

        Args:
            year(int): the measurement year

        Returns:
            a Tuple with:
            1: a set with the eligible measures if successful
               None otherwise
            2: A str with an error if not successful
               None otherwise
        """

        measures_per_year = get_calculus_parameters(
            db_table=self.db_table,
            parameter_name="{}-{}".format(ConfigFileType.MEASURES_PER_YEAR.value, year),
            logger=self.logger,
        )
        if measures_per_year is None:
            self.logger.error("No Hybrid Measures by Year entry for the year {}".format(year))
            error_msg = (
                "Impossible to calculate, the system is missing configuration files. "
                + "Please contact the administrators"
            )
            return None, error_msg

        eligible_measures = set()  # First store all the measures eligible for the year
        for measure in measures_per_year.keys():
            if bool(measures_per_year[measure]):
                # Remove any non-alphabetic chars and make it all upper cases.
                eligible_measures.add(str(self.only_alpha.sub("", measure)).upper())
        return eligible_measures, None

    def get_eligible_measures_per_product(
        self,
        metadata_elem: Union[ET.Element, ET.ElementTree],
        year: int,
    ) -> Tuple[Union[set, None], Union[str, None]]:
        """
        Gets the list of eligible measures for a product line year.

        Args:
            metadata_elem(ET.Element):
                the Metadata element of the XML submission
            year(int):
                the measurement year

        Returns:
            a Tuple with:
            1: a set with the eligible measures if successful
               None otherwise
            2: A str with an error if not successful
               None otherwise
        """
        product_line = metadata_elem.find("ProductLine")
        product_search_key = None
        if product_line.text == "Medicare":
            if metadata_elem.find("SpecialProject").text.startswith("MMP") or metadata_elem.find(
                    "SpecialProject"
            ).text.startswith("SNP"):
                product_search_key = "medicaresnp"

            elif metadata_elem.find("SpecialProject").text.startswith("CMS"):  # CMS means MedicareMA
                product_search_key = "medicarema"
            else:
                self.logger.error("Invalid Special Project: {}".format(metadata_elem.find("SpecialProject").text))
                return None, "Invalid Special Project: {}".format(metadata_elem.find("SpecialProject").text)
        elif product_line.text == "Commercial":
            product_search_key = "commercial"
        elif product_line.text == "Exchange":
            product_search_key = "exchange"
        elif product_line.text == "Medicaid":
            product_search_key = "medicaid"
        else:
            self.logger.error("Invalid Product Line: {}".format(metadata_elem.find("ProductLine").text))
            return None, "Invalid Product Line: {}".format(metadata_elem.find("ProductLine").text)
        # Use all lower letters
        product_search_key = product_search_key.lower()

        # Load the measures per product
        measures_per_product = get_calculus_parameters(
            db_table=self.db_table,
            parameter_name="{}-{}".format(ConfigFileType.MEASURES_PER_PRODUCT.value, year),
            logger=self.logger,
        )
        if measures_per_product is None:
            self.logger.error("No measures per product entry for the year {}".format(year))
            error_msg = (
                    "Impossible to calculate, the system is missing configuration files. "
                    + "Please contact the administrators"
            )
            return None, error_msg
        elif len(measures_per_product.keys()) == 1:  # Get the productLine value in the json object
            measures_per_product = list(measures_per_product.values())[0]

        found = False  # Found the product line among the keys in measures_per_product

        eligible_for_curr_product = set()

        # Remove the measures that are not eligible for the product
        for product_key in measures_per_product.keys():
            product_key = str(product_key)
            # We can not assume the product name in measures_per_product starts with a capital letter,
            # is camel case, etc..
            if str(self.only_alpha.sub("", product_key)).lower().startswith(product_search_key):
                found = True

                for measure in measures_per_product[product_key]:
                    if parse_boolean(measures_per_product[product_key][measure]):
                        # Remove any non-alphabetic chars and make it all upper cases.
                        eligible_for_curr_product.add(str(self.only_alpha.sub("", measure)).upper())
                break

        if found:
            return eligible_for_curr_product, None
        else:
            error_msg = str(
                "Not able to find a product that starts with {} among measures_per_product for the year {}"
            ).format(product_search_key, year)
            self.logger.error(error_msg)
            return None, error_msg

    def filter_eligible_measures_per_product(
        self,
        candidate_measures: set,
        product_search_key: str,
        year: int,
    ) -> Tuple[Union[set, None], Union[str, None]]:
        """
        Filter from a list of candidate measures the ones eligible for a product line

        Args:
            candidate_measures(set):
                the candidate measures
            product_search_key(str):
                a string with a case-insensitive prefix to identify the product line in the measures_per_product
            year(int):
                the measurement year

        Returns:
            a Tuple with:
            1: a set with the filtered eligible measures if successful
               None otherwise
            2: A str with an error if not successful
               None otherwise
        """
        # Use all lower letters
        product_search_key = product_search_key.lower()

        # Load the measures per product
        measures_per_product = get_calculus_parameters(
            db_table=self.db_table,
            parameter_name="{}-{}".format(ConfigFileType.MEASURES_PER_PRODUCT.value, year),
            logger=self.logger,
        )
        if measures_per_product is None:
            self.logger.error("No measures per product entry for the year {}".format(year))
            error_msg = (
                "Impossible to calculate, the system is missing configuration files. "
                + "Please contact the administrators"
            )
            return None, error_msg
        elif len(measures_per_product.keys()) == 1:  # Get the productLine value in the json object
            measures_per_product = list(measures_per_product.values())[0]

        found = False  # Found the product line among the keys in measures_per_product
        # Remove the measures that are not eligible for the product
        for product_key in measures_per_product.keys():
            product_key = str(product_key)
            # We can not assume the product name in measures_per_product starts with a capital letter,
            # is camel case, etc..
            if str(self.only_alpha.sub("", product_key)).lower().startswith(product_search_key):
                found = True
                eligible_for_curr_product = set()
                for measure in measures_per_product[product_key]:
                    if parse_boolean(measures_per_product[product_key][measure]):
                        # Remove any non-alphabetic chars and make it all upper cases.
                        eligible_for_curr_product.add(str(self.only_alpha.sub("", measure)).upper())

                # Get the intersection of the measures eligible for the measurement year and the product line
                candidate_measures = candidate_measures.intersection(eligible_for_curr_product)
                break

        if found:
            return candidate_measures, None
        else:
            error_msg = str(
                "Not able to find a product that starts with {} among measures_per_product for the year {}"
            ).format(product_search_key, year)
            self.logger.error(error_msg)
            return None, error_msg

    # flake8: noqa: C901
    def get_eligible_measures(
        self, metadata_elem: Union[ET.Element, ET.ElementTree], year: int
    ) -> Tuple[Union[set, None], Union[str, None]]:  # flake8: noqa: C901
        """
        Get the measures eligible for a xml submission in a given measure year

        Args:
            metadata_elem(ET.Element): the Metadata element of the XML submission
            year(int): the measurement year

        Returns:
            a list with the eligible measures if successful
            None otherwise
        """

        eligible_measures, error = self.get_eligible_measures_per_year(year=year)
        self.logger.info("Eligible measures for {}:\n{}".format(year, eligible_measures))
        if error is not None:
            self.logger.error("Error when getting eligible measures for year: {}".format(year))
            return None, error
        product_line = metadata_elem.find("ProductLine")
        product_search_key = None
        if product_line.text == "Medicare":
            if metadata_elem.find("SpecialProject").text.startswith("MMP") or metadata_elem.find(
                "SpecialProject"
            ).text.startswith("SNP"):
                product_search_key = "medicaresnp"

            elif metadata_elem.find("SpecialProject").text.startswith("CMS"):  # CMS means MedicareMA
                product_search_key = "medicarema"
            else:
                self.logger.error("Invalid Special Project: {}".format(metadata_elem.find("SpecialProject").text))
                return None, "Invalid Special Project: {}".format(metadata_elem.find("SpecialProject").text)
        elif product_line.text == "Commercial":
            product_search_key = "commercial"
        elif product_line.text == "Exchange":
            product_search_key = "exchange"
        elif product_line.text == "Medicaid":
            product_search_key = "medicaid"
        else:
            self.logger.error("Invalid Product Line: {}".format(metadata_elem.find("ProductLine").text))
            return None, "Invalid Product Line: {}".format(metadata_elem.find("ProductLine").text)
        # Remove the measures that are not eligible for the product
        eligible_measures, error = self.filter_eligible_measures_per_product(
            candidate_measures=eligible_measures, product_search_key=product_search_key, year=year
        )
        self.logger.info("Filtered eligible measures for {}:\n{}".format(product_search_key, eligible_measures))
        if error is not None:
            self.logger.error("Error when filtering eligible measures for ProductLine: {}".format(product_line.text))
            return None, error

        return eligible_measures, None

    # flake8: noqa: C901
    def _get_mrss_single_rate(
        self,
        measure_elem: Union[ET.Element, ET.ElementTree],
        full_measure_name: str,
        reference_array: dict,
        ordered_rates: list,
    ) -> Union[int, None]:  # flake8: noqa: C901
        """
        Calculates the MRSS for a given single rate measure

        Args:
            measure_elem(ET.Element): a measure element from the XML submission
            full_measure_name(str): the measure's full name
            reference_array(dict): the reference array
            ordered_rates(list): a list with the rates in the reference array ordered

        Returns:
            An int with the MRSS for the measure if successful;
            None otherwise
        """
        result_elem = None
        # If it is a COL with cohort stratification
        if ((full_measure_name in ["ColorectalCancerScreening", "EyeExams"]) and
            measure_elem.find(full_measure_name).find("Stratification") is not None):
            # Find the "Total" stratification for SESStratification and Age (2022 MEDICARE XML)
            # or find Stratification with AGE = TOTAL but with no SESStratification (2022 change for COMMERCIAL, EXCHANGE, and MEDICAID)
           for cohort_sub_measure in measure_elem.findall(full_measure_name):
               # If SESStratification tag is present
                if cohort_sub_measure.find("Stratification").find("SESStratification") is not None:
                    # If SESStratification is "Total" and Age is None or "Total"
                    if (cohort_sub_measure.find("Stratification").find("SESStratification").text == "Total" and
                       (cohort_sub_measure.find("Stratification").find("Age") is None or cohort_sub_measure.find("Stratification").find("Age").text == "Total")):
                        result_elem = cohort_sub_measure.find("Result")
                        break
                else:
                    # If AGE tag is present and is "Total"
                    if cohort_sub_measure.find("Stratification").find("Age") is not None and cohort_sub_measure.find("Stratification").find("Age").text == "Total":
                        result_elem = cohort_sub_measure.find("Result")
                        break
        # If it is a CBP with cohort stratification
        elif (full_measure_name == "ControlHighBP"):
            # Find the total where stratification tag is none
            for cohort_sub_measure in measure_elem.findall(full_measure_name):
                if cohort_sub_measure.find("Stratification") is None:
                    result_elem = cohort_sub_measure.find("Result")
                    break
        else:
            sub_measure = measure_elem.find(full_measure_name)
            if sub_measure is None:
                return 411
            result_elem = sub_measure.find("Result")
        if (
            result_elem is None
            or result_elem.find("Indicator").find("AuditDesignation").text in ["NB", "NR", "NQ", "BR", "UN"]
            or result_elem.find("Indicator").find("Rate") is None
            or result_elem.find("Indicator").find("Rate").text is None
            or result_elem.find("Indicator").find("Rate").text in ["", " ", "None", "null", "NULL"]
        ):
            return 411

        # Convert decimal to percentage and truncate
        rate = int(float(result_elem.find("Indicator").find("Rate").text) * 100)
        # In the PoorHbA1cControl sub-measure, use the complement instead of the value
        if full_measure_name == "PoorHbA1cControl":
            rate = 100 - rate
        if rate < ordered_rates[0]:
            return reference_array[str(ordered_rates[0])]
        if rate > ordered_rates[-1]:
            return reference_array[str(ordered_rates[-1])]

        return reference_array[str(rate)]

    # flake8: noqa: C901
    def _get_mrss_multiple_rate(
        self,
        measure_elem: Union[ET.Element, ET.ElementTree],
        reference_array: dict,
        ordered_rates: list,
    ) -> Union[int, None]:  # flake8: noqa: C901
        """
        Calculates the MRSS for a given multiple rate measure

        Args:
            measure_elem(ET.Element): a measure element from the XML submission
            reference_array(dict): the reference array
            ordered_rates(list): a list with the rates in the reference array ordered

        Returns:
            An int with the MRSS for the measure if successful;
            None otherwise
        """
        rate = 1000
        for sub_measure in measure_elem:
            if sub_measure.tag == "Metadata":
                continue
            result_elem = sub_measure.find("Result")

            if (
                result_elem is None
                or result_elem.find("Indicator").find("AuditDesignation").text in ["NB", "NR", "NQ", "BR", "UN"]
                or result_elem.find("Indicator").find("Rate") is None
                or result_elem.find("Indicator").find("Rate").text is None
                or result_elem.find("Indicator").find("Rate").text in ["", " ", "None", "null", "NULL"]
            ):
                continue
            # CDC has some peculiarities
            if measure_elem.tag == "CDC":
                # In the PoorHbA1cControl sub-measure, use the complement instead of the value
                if sub_measure.tag == "PoorHbA1cControl":
                    local_rate = float(result_elem.find("Indicator").find("Rate").text)
                    if local_rate > 0.09:
                        rate = min((1.0 - local_rate), rate)
                    else:
                        rate = min(local_rate, rate)
                    continue  # rate is already updated, skip to the next for iteration

                # If the current sub-measure is "EyeExams" and
                elif (
                    sub_measure.tag == "EyeExams"
                    and
                    # it has SES cohort stratification and
                    (sub_measure.find("Stratification") is not None)
                    and
                    # the current stratification is not Total
                    sub_measure.find("Stratification").find("SESStratification").text != "Total"
                ):
                    continue  # skip
                    
            # Prep for 2022 when HBD will not be inside CDC anymore
            if measure_elem.tag == "HBD":
                # ignore if sub measure has a stratification tag
                if sub_measure.find("Stratification") is not None:
                    continue  # skip                
                # In the PoorHbA1cControl sub-measure, use the complement instead of the value
                if sub_measure.tag == "PoorHbA1cControl":
                    local_rate = float(result_elem.find("Indicator").find("Rate").text)
                    if local_rate > 0.09:
                        rate = min((1.0 - local_rate), rate)
                    else:
                        rate = min(local_rate, rate)
                    continue  # rate is already updated, skip to the next for iteration
                # Ignore any other sub measure that is not PoorHbA1cControl or AdequateHbA1cControl
                elif sub_measure.tag != "AdequateHbA1cControl":
                    continue  # skip

            # Skip if the Measure is TRC or WCC,
            # and it has SES cohort stratification,
            # and the current stratification is not Total
            if ((measure_elem.tag == "TRC" or measure_elem.tag == "WCC")
               and (sub_measure.find("Stratification") is not None)
               and (sub_measure.find("Stratification").find("Age") is not None)
               and sub_measure.find("Stratification").find("Age").text != "Total"
            ):
                continue  # skip

           # Skip if the Measure is PPC and it has Stratification tag
            if (measure_elem.tag == "PPC" and sub_measure.find("Stratification") is not None):
                continue  # skip

            local_rate = float(result_elem.find("Indicator").find("Rate").text)
            rate = min(local_rate, rate)

        # There is no sub-measure with an 'R' AuditDesignation, rate has never been set
        if rate == 1000:
            return reference_array[str(ordered_rates[0])]
        # Truncate rate to an integer
        rate = int(rate * 100)
        return _get_mrss_for_rate(
            reference_array=reference_array, ordered_rates=ordered_rates, rate=rate, logger=self.logger
        )

    def get_mrss_for_measure(
        self,
        single_rate_measures_full_names,
        multi_rate_measures,
        measure_elem: Union[ET.Element, ET.ElementTree],
        reference_array: dict,
        ordered_rates: list,
        year: int
    ) -> Union[int, None]:
        """
        Calculates the MRSS for a given measure xml element

        Args:
            single_rate_measures_full_names: a dict acronym->full_name for single-rate measures
            multi_rate_measures: a set with the multi-rate measures acronyms
            measure_elem(ET.Element): a measure element from the XML submission
            reference_array(dict): the reference array
            ordered_rates(list): a list with the rates in the reference array ordered
            year: the measurement year

        Returns:
            An int with the MRSS for the measure if successful;
            None otherwise
        """
        if measure_elem.tag in single_rate_measures_full_names.keys():
            return self._get_mrss_single_rate(
                measure_elem=measure_elem,
                full_measure_name=single_rate_measures_full_names[measure_elem.tag],
                reference_array=reference_array,
                ordered_rates=ordered_rates,
            )
        elif measure_elem.tag in multi_rate_measures:
            return self._get_mrss_multiple_rate(
                measure_elem=measure_elem, reference_array=reference_array, ordered_rates=ordered_rates
            )
        else:
            self.logger.error("Not supported measure: {}".format({measure_elem.tag}))
            return None

    def get_pre_processed_mrsss(
        self, user_id: str, file_id: str, s3_key: str, year: int, timestamp: int, combine: dict = []
    ) -> Union[dict, None]:
        """
        Calculates the MRSSs for a submission file.
        Saves the MRSSs on the file's status and also return then in a dict

        Args:
            user_id(str): a string with the user's id
            file_id(str): a string with the file_id in the format <OrganizationId>-<SubmissionId>.xml
            s3_key: the key for the validated xml file in S3
            year: the measurement year
            timestamp: the timestamp that identifies each upload of files with the same OrganizationId and Submission
            combine: an array with sets of measures to combine

        Returns:
            A dict with the preprocessed MRSSs for the file
        """
        self.logger.info(
            "Calculating pre-processed MRSSs for s3_key: {}, year: {}, timestamp: {}, combine: {}".format(
                s3_key, year, timestamp, combine
            )
        )
        # Load the reference array
        reference_array = get_calculus_parameters(
            db_table=self.db_table,
            parameter_name="{}-{}".format(ConfigFileType.REFERENCE_ARRAY.value, year),
            logger=self.logger,
        )
        if reference_array is None:
            self.logger.error("No Reference Array entry for the year {}".format(year))
            update_file_status(
                db_table=self.db_table,
                user_id=user_id,
                file_id=file_id,
                new_status=FileStatus.UNEXPECTED_ERROR,
                timestamp=timestamp,
                error_msg="Impossible to calculate, the system is missing configuration files. "
                + "Please contact the administrators",
            )
            return None
        single_rate_measures_full_names = dict(get_calculus_parameters(
            db_table=self.db_table,
            parameter_name="{}-{}".format(ConfigFileType.SINGLE_RATE_MEASURES.value, year),
            logger=self.logger,
        ))
        if single_rate_measures_full_names is None:
            self.logger.error("No Rsingle_rate_measures_full_names entry for the year {}".format(year))
            update_file_status(
                db_table=self.db_table,
                user_id=user_id,
                file_id=file_id,
                new_status=FileStatus.UNEXPECTED_ERROR,
                timestamp=timestamp,
                error_msg="Impossible to calculate, the system is missing configuration files. "
                + "Please contact the administrators",
            )
            return None
        multi_rate_measures = set(get_calculus_parameters(
            db_table=self.db_table,
            parameter_name="{}-{}".format(ConfigFileType.MULTI_RATE_MEASURES.value, year),
            logger=self.logger,
        ))
        if multi_rate_measures is None:
            self.logger.error("No multi_rate_measures entry for the year {}".format(year))
            update_file_status(
                db_table=self.db_table,
                user_id=user_id,
                file_id=file_id,
                new_status=FileStatus.UNEXPECTED_ERROR,
                timestamp=timestamp,
                error_msg="Impossible to calculate, the system is missing configuration files. "
                + "Please contact the administrators",
            )
            return None
        try:
            s3_object = self.s3.get_object(Bucket=self.bucket_name, Key=s3_key)
            xml_string = bytes(s3_object["Body"].read()).decode("utf-8")
            del s3_object  # We don't need the s3_object after loading it's content to a str
            gc.collect()
        except Exception as ex:
            self.logger.error("Unable to read file. Bucket: {} Key: {}".format(self.bucket_name, s3_key))
            self.logger.error(str(ex))
            update_file_status(
                db_table=self.db_table,
                user_id=user_id,
                file_id=file_id,
                new_status=FileStatus.UNEXPECTED_ERROR,
                timestamp=timestamp,
                error_msg="Unable to read file. Bucket: {} Key: {}".format(self.bucket_name, s3_key),
            )
            return None
        try:
            xml_root = ET.fromstring(xml_string)
        except Exception as ex:
            self.logger.error("Cannot parse file {} to xml tree".format(s3_key))
            self.logger.error(str(ex))
            update_file_status(
                db_table=self.db_table,
                user_id=user_id,
                file_id=file_id,
                new_status=FileStatus.UNEXPECTED_ERROR,
                timestamp=timestamp,
                error_msg="Can not parse file to xml tree",
            )
            return None
        del xml_string  # We don't need the xml_string after parsing it to an ET.ElementTree
        gc.collect()
        metadata_elm = xml_root.find("Metadata")
        # First add the audited value
        result = {}
        measures_for_product, error = self.get_eligible_measures_per_product(metadata_elem=metadata_elm, year=year)
        measures_for_year, error = self.get_eligible_measures_per_year(year=year) if error is None else (None, error)
        if error is not None:
            self.logger.error(
                "Not able to get the eligible measures for s3_key: {}, year: {}".format(
                    s3_key, year, timestamp, combine
                )
            )
            update_file_status(
                db_table=self.db_table,
                user_id=user_id,
                file_id=file_id,
                new_status=FileStatus.UNEXPECTED_ERROR,
                timestamp=timestamp,
                error_msg=error,
            )
            return None
        ordered_rates = sorted([int(rate_str) for rate_str in reference_array.keys()])
        xml_measures = xml_root.find("Measures")
        if int(year) != 2020 and xml_measures.find("CDC"):
            for measure_elem in xml_measures:
                if measure_elem.tag == "CDC":
                    if "BPD" in measures_for_product:
                        if "BPD" not in measures_for_year:
                            result["BPD"] = 411
                        else:
                            result["BPD"] = self._get_mrss_single_rate(
                                measure_elem=measure_elem,
                                full_measure_name=single_rate_measures_full_names["BPD"],
                                reference_array=reference_array,
                                ordered_rates=ordered_rates,
                            )
                    if "EED" in measures_for_product:
                        if "EED" not in measures_for_year:
                            result["EED"] = 411
                        else:
                            result["EED"] = self._get_mrss_single_rate(
                                measure_elem=measure_elem,
                                full_measure_name=single_rate_measures_full_names["EED"],
                                reference_array=reference_array,
                                ordered_rates=ordered_rates,
                            )
                    if "HBD" in measures_for_product:
                        if "HBD" not in measures_for_year:
                            result["HBD"] = 411
                        else:
                            # HBD IS A MULTI-RATE MEASURE USE PoorHbA1cControl (INVERSE) AND AdequateHbA1cControl
                            if measure_elem.find("PoorHbA1cControl"):
                                result["HBD"] = self._get_mrss_single_rate(
                                    measure_elem=measure_elem,
                                    full_measure_name="PoorHbA1cControl",
                                    reference_array=reference_array,
                                    ordered_rates=ordered_rates,
                                )
                                if measure_elem.find("AdequateHbA1cControl"):
                                    result["HBD"] = max(result["HBD"], self._get_mrss_single_rate(
                                        measure_elem=measure_elem,
                                        full_measure_name="AdequateHbA1cControl",
                                        reference_array=reference_array,
                                        ordered_rates=ordered_rates,
                                    ))
                            else:
                                result["HBD"] = self._get_mrss_single_rate(
                                    measure_elem=measure_elem,
                                    full_measure_name="AdequateHbA1cControl",
                                    reference_array=reference_array,
                                    ordered_rates=ordered_rates,
                                )
                elif str(measure_elem.tag) in measures_for_product:
                    if measure_elem.tag not in measures_for_year:
                        result[measure_elem.tag] = 411
                    else:
                        result[str(measure_elem.tag)] = self.get_mrss_for_measure(
                            single_rate_measures_full_names=single_rate_measures_full_names,
                            multi_rate_measures=multi_rate_measures, measure_elem=measure_elem,
                            reference_array=reference_array, ordered_rates=ordered_rates, year = year
                        )
        else:
            for measure_elem in xml_measures:
                if str(measure_elem.tag) in measures_for_product:
                    if measure_elem.tag not in measures_for_year:
                        result[measure_elem.tag] = 411
                    else:
                        result[str(measure_elem.tag)] = self.get_mrss_for_measure(
                            single_rate_measures_full_names=single_rate_measures_full_names,
                            multi_rate_measures=multi_rate_measures, measure_elem=measure_elem,
                            reference_array=reference_array, ordered_rates=ordered_rates, year = year
                        )

        # Fill with 411 all the eligible measures that are missing in the xml
        missing_measures = set(measures_for_product) - set(result.keys())

        for measure in missing_measures:
            result[measure] = 411
        # Combine each set of measures to combine
        for combine_set in combine:
            if not isinstance(combine_set, (list, set)):
                break
            combine_set = set(combine_set)
            max_value = 0
            # Get their max value
            for combine_measure in combine_set:
                if combine_measure in result:
                    max_value = max(max_value, result[combine_measure])
            # Set the max value for every combined measure
            for combine_measure in combine_set:
                result[combine_measure] = max_value

        self.logger.info(
            "Calculated MRSSs for s3_key: {}, year: {}, timestamp: {}, combine: {}".format(
                s3_key, year, timestamp, combine
            )
        )
        update_file_status(
            db_table=self.db_table,
            user_id=user_id,
            file_id=file_id,
            new_status=FileStatus.VALID,
            timestamp=timestamp,
            pre_processed_mrsss=result,
            error_msg="No error",
        )
        return result

    def save_oversamples(self, user_id: str, file_submission_id: str, oversamples: dict) -> Union[str, None]:
        """

        Args:
            user_id:
            file_submission_id:
            oversamples:

        Returns:

        """
        if "." in file_submission_id:  # Remove the extension
            file_submission_id = file_submission_id[: file_submission_id.index(".")]
        s3_key = "results/{}/{}-oversamples.json".format(user_id, file_submission_id)
        try:
            data = json.dumps(oversamples, indent=2).encode(encoding="UTF-8")
        except Exception:
            self.logger.error("Error on parsing oversamples to json: {}".format(oversamples))
            return "Error on parsing oversamples to json."

        try:
            self.s3.put_object(Bucket=self.bucket_name, Key=s3_key, Body=data)
        except Exception:
            self.logger.error("Error on saving oversamples to s3.")
            return "Error on saving oversamples to s3"
        self.logger.info("Oversamples saved for user_id: {}, file_submission_id: {}.")
        return None

    def export_csv(self, user_id: str, file_id: str, timestamp: int, oversamples: dict) -> Union[str, None]:

        file_status = get_file_status(
            db_table=self.db_table, user_id=user_id, file_id=file_id, timestamp=timestamp, logger=self.logger
        )
        if file_status is None:
            self.logger.error(
                "Unable to retrieve file status for file. user_id: {}, file_id: {}, timestamp: {}".format(
                    user_id, file_id, timestamp
                )
            )
            update_file_status(
                db_table=self.db_table,
                user_id=user_id,
                file_id=file_id,
                new_status=FileStatus.UNEXPECTED_ERROR,
                timestamp=timestamp,
                error_msg=(
                    "Not able to retrieve the calculus configuration. "
                    + "Check if the file has been correctly submitted."
                ),
            )
            return None
        if not ("preProcessedMrsss" in file_status):
            self.logger.error(
                "Unable to retrieve preProcessedMrsss for file. user_id: {}, file_id: {}, timestamp: {}".format(
                    user_id, file_id, timestamp
                )
            )
            update_file_status(
                db_table=self.db_table,
                user_id=user_id,
                file_id=file_id,
                new_status=FileStatus.UNEXPECTED_ERROR,
                timestamp=timestamp,
                error_msg=(
                    "Not able to retrieve the calculus configuration. "
                    + "Check if the file has been correctly submitted."
                ),
            )
            return None

        if not ("outputMetadata" in file_status):
            self.logger.error(
                "Unable to retrieve outputMetadata for file. user_id: {}, file_id: {}, timestamp: {}".format(
                    user_id, file_id, timestamp
                )
            )
            update_file_status(
                db_table=self.db_table,
                user_id=user_id,
                file_id=file_id,
                new_status=FileStatus.UNEXPECTED_ERROR,
                timestamp=timestamp,
                error_msg=(
                    "Not able to retrive the calculus configuration. "
                    + "Check if the file has been correctly submitted."
                ),
            )
            return None
        output_metadata = file_status["outputMetadata"]
        csv_results = (
            '"OrganizationName","ProductLine","SpecialProject","ReportingProduct",'
            + '"OrganizationId","SubmissionId","IsAuditable"'
        )
        csv_results += '\n"{}","{}","{}","{}","{}","{}",{}\n'.format(
            output_metadata["organizationName"],
            output_metadata["productLine"],
            output_metadata["specialProject"],
            output_metadata["reportingProduct"],
            output_metadata["organizationId"],
            output_metadata["submissionId"],
            output_metadata["audited"],
        )
        mrsss = file_status["preProcessedMrsss"]
        csv_results += '\n"MeasureId","MRSS","Oversample%","FSS"'
        for measure in oversamples.keys():
            if not measure in mrsss:
                self.logger.error(
                    str(
                        "Unable to retrieve preProcessedMrsss for {} measure. "
                        + "user_id: {}, file_id: {}, timestamp: {}"
                    ).format(measure, user_id, file_id, timestamp)
                )
                update_file_status(
                    db_table=self.db_table,
                    user_id=user_id,
                    file_id=file_id,
                    new_status=FileStatus.UNEXPECTED_ERROR,
                    timestamp=timestamp,
                    error_msg=str(
                        "Not able to retrive the calculus configuration for {} measure. "
                        + "Check if the file has been correctly submitted."
                    ).format(measure),
                )
                return None
            fss = ceil(float(mrsss[measure]) * (1 + (float(oversamples[measure]) / 100.0)))
            csv_results += '\n"{}",{},{},{}'.format(
                measure, mrsss[measure], find_and_parse_int(oversamples[measure]), fss
            )
        self.logger.info("CSV successfully produced.")
        self.save_oversamples(user_id=user_id, file_submission_id=file_id, oversamples=oversamples)
        return csv_results
