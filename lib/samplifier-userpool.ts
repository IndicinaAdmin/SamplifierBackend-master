import * as cdk from '@aws-cdk/core';
import * as cognito from '@aws-cdk/aws-cognito';
import * as path from 'path';
import * as route53 from "@aws-cdk/aws-route53";
import * as acm from '@aws-cdk/aws-certificatemanager';
import * as route53_targets from "@aws-cdk/aws-route53-targets";
import { CognitoUserPoolAdmin } from './base/base-cognito-userpool';
import { NodeFunction } from './base/node-function';
import { ParameterHelper } from './helpers/ssm-helper';

export interface SamplifierUserPoolProps {
    domainIdentityArn: string;
    hostedZone: route53.IHostedZone;
    variables: any;
}

export class SamplifierUserPool extends cdk.Construct {
    userPool: cognito.UserPool;
    private ssmParameters: any;
    private idp: any;

    constructor(scope: cdk.Construct, id: string, props: SamplifierUserPoolProps) {
        super(scope, id);
        this.ssmParameters = props.variables.ssmParameters;
        this.idp = props.variables.idp;

        //lambda trigger used by cognito
        const customMessage = new NodeFunction(this, 'custom-message-func', {
            entry: path.join(__dirname, '/../src/node/cognito/custom-message.ts'),
            handler: 'handler',
            functionName: 'samplifier-custom-message-cognito-trigger'
        });

        // provision cognito user pool
        this.userPool = new CognitoUserPoolAdmin(this, 'userpool-admin', {
            userPoolName: props.variables.serviceName,
            lambdaTriggers: {
                customMessage: customMessage
            }
        });

        // Setup Cognito to send emails using the custom AWS SES configuration
        const cfnUserPool = this.userPool.node.defaultChild as cognito.CfnUserPool;
        cfnUserPool.emailConfiguration = {
            emailSendingAccount: 'DEVELOPER',
            replyToEmailAddress: `no-reply@${props.hostedZone.zoneName}`,
            from: `no-reply@${props.hostedZone.zoneName}`,
            sourceArn: props.domainIdentityArn
        };

        this.configureACM(props.hostedZone);

        //Add IdPs - google, ms, etc
        //Setup Google as an Identity Provider
        const googleSecret = ParameterHelper.getParameter(this, this.ssmParameters.googleSecret);
        new cognito.UserPoolIdentityProviderGoogle(this, 'Google', {
            clientId: this.idp.googleId,
            clientSecret: googleSecret,
            userPool: this.userPool,
            attributeMapping: {
                email: cognito.ProviderAttribute.GOOGLE_EMAIL,
                familyName: cognito.ProviderAttribute.GOOGLE_FAMILY_NAME,
                givenName: cognito.ProviderAttribute.GOOGLE_GIVEN_NAME,
            },
            scopes: ["profile", "email", "openid"]
        });

        //Setup Microsoft as an Identity Provider
        const msSecret = ParameterHelper.getParameter(this, this.ssmParameters.msSecret);
        new cognito.CfnUserPoolIdentityProvider(this, "Microsoft", {
            providerName: "Microsoft",
            providerDetails: {
                client_id: this.idp.msId,
                client_secret: msSecret,
                attributes_request_method: "GET",
                oidc_issuer: "https://login.microsoftonline.com/9188040d-6c67-4c5b-b112-36a304b66dad/v2.0",
                authorize_scopes: "profile email openid"
            },
            providerType: "OIDC",
            attributeMapping: {
                "email": "email",
                "family_name": "family_name",
                "given_name": "given_name",
            },
            userPoolId: this.userPool.userPoolId
        });
    }

    private configureACM(hostedZone: route53.IHostedZone) {
        let cognitoDomain = `auth.${hostedZone.zoneName}`;

        //create a new certificate and validate at route53
        const cognitoCertificate = new acm.Certificate(this, 'distribution-certificate', {
            domainName: cognitoDomain,
            subjectAlternativeNames: [cognitoDomain],
            validation: acm.CertificateValidation.fromDns(hostedZone)
        });

        //Export the API certificate ARN to SSM
        ParameterHelper.putParameter(this, '/samplifier/cognito/certification/arn', cognitoCertificate.certificateArn);
        ParameterHelper.putParameter(this, '/samplifier/cognito/domainName', cognitoDomain);

        //configuring the certificate for userpool doamin
        const userPoolDomain = new cognito.UserPoolDomain(this, 'custom-domain', {
            userPool: this.userPool,
            customDomain: {
                certificate: cognitoCertificate,
                domainName: cognitoDomain
            }
        });
        ParameterHelper.putParameter(this, '/samplifier/cognito/userPoolDomain/distribution/domainName', userPoolDomain.cloudFrontDomainName);

        //create a new route53 A for cf distribution created by userpool
        new route53.ARecord(this, 'api-alias-record', {
            recordName: cognitoDomain,
            zone: hostedZone,
            target: route53.RecordTarget.fromAlias(new route53_targets.UserPoolDomainTarget(userPoolDomain))
        });
    }
}
