import * as cdk from '@aws-cdk/core';
import * as cognito from '@aws-cdk/aws-cognito';
import * as druid from 'druid-cdk-construct';
import * as ssm from '@aws-cdk/aws-ssm';

export class CognitoUserPoolAdmin extends cognito.UserPool {
    constructor(scope: cdk.Construct, id: string, props: cognito.UserPoolProps) {
        /**
         * The Default properties for the Cognito UserPool.
         */
        const defaultProps = {
            selfSignUpEnabled: true,
            userVerification: {
                emailSubject: 'Finish your sign in process!',
                emailBody: 'Error 4561. TBC {####}. ',
                emailStyle: cognito.VerificationEmailStyle.CODE, //Use a link instead of a Code
            },
            signInAliases: {
                email: true
            },
            signInCaseSensitive: false,
            autoVerify: { //Verify if the email contains '@'
                email: true,
            },
            standardAttributes: { //Which standard cognito attributes this UserPool will include
                email: {
                    required: true,
                    mutable: true,
                },
                familyName: {
                    mutable: true,
                    required: false,
                },
                givenName: {
                    mutable: true,
                    required: false,
                }
            },
            customAttributes: {
                'companyName': new cognito.StringAttribute({ mutable: true }),
            },
            passwordPolicy: {
                minLength: 8,
                requireDigits: true,
                requireLowercase: false,
                requireUppercase: true,
                requireSymbols: true,
            },
            accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
            removalPolicy: cdk.RemovalPolicy.RETAIN,
        } as cognito.UserPoolProps;

        const mergeProps = druid.overrideProps(defaultProps, props);
        super(scope, id, mergeProps);

        new ssm.StringParameter(this, 'cognito-pool-id', {
            stringValue: this.userPoolId,
            parameterName: '/samplifier/cognito/userPoolId'
        });
    }
}