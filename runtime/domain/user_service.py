import os.path

import boto3
import chevron
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities import parameters
from botocore.exceptions import ClientError


class UserService:
    cognitoClient = boto3.client("cognito-idp")
    sesClient = boto3.client("ses", region_name=boto3.session.Session().region_name)
    logger: Logger
    cognitoUserPoolId: str
    sesIdentity: str

    def __init__(self, logger: Logger = None):
        self.logger = logger
        self.cognitoUserPoolId = parameters.get_parameter("/samplifier/cognito/userPoolId")
        self.sesIdentity = parameters.get_parameter("/samplifier/route53/hostedzone/name")

    def delete_user(self, user_name: str):
        user = self.cognitoClient.admin_get_user(UserPoolId=self.cognitoUserPoolId, Username=user_name)
        user_email = next(obj for obj in user["UserAttributes"] if obj["Name"] == "email")["Value"]
        given_name = next(obj for obj in user["UserAttributes"] if obj["Name"] == "given_name")["Value"]

        try:
            self.cognitoClient.admin_delete_user(UserPoolId=self.cognitoUserPoolId, Username=user_name)
        except Exception as ex:
            self.logger.error("Error when deleting account from cognito.")
            self.logger.error(str(ex))
            return

        self.logger.debug(f"Deleted user from cognito '{user_name}'!")
        self.__send_account_deleted_email(user_email, given_name)

    def __send_account_deleted_email(self, user_email: str, given_name: str):
        CHARSET = "UTF-8"
        SUBJECT = "Samplifier account deleted"

        self.logger.debug("Sending email")
        try:
            # Provide the contents of the email.
            response = self.sesClient.send_email(
                Destination={
                    "ToAddresses": [user_email],
                },
                Message={
                    "Body": {
                        "Html": {
                            "Charset": CHARSET,
                            "Data": self.__get_account_deleted_html_email(given_name),
                        },
                        "Text": {
                            "Charset": CHARSET,
                            "Data": "Your account has been deleted.",
                        },
                    },
                    "Subject": {
                        "Charset": CHARSET,
                        "Data": SUBJECT,
                    },
                },
                Source="no-reply@{domain}".format(domain=self.sesIdentity),
            )

            self.logger.debug("Email sent")
        # Display an error if something goes wrong.
        except ClientError as e:
            self.logger.error(e.response["Error"]["Message"])
        else:
            self.logger.debug("Email sent! Message ID:"),
            self.logger.debug(response["MessageId"])

    def __get_account_deleted_html_email(self, user_name: str):
        domain_name = parameters.get_parameter("/samplifier/route53/hostedzone/name")
        file_path = os.path.dirname(__file__) + "/../resources/emails/account_deleted_email.handlebars"
        with open(file_path, "r") as f:
            return chevron.render(
                f, {"baseUrl": "https:{domain_name}".format(domain_name=domain_name), "name": user_name}
            )
