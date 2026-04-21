import * as apiGtw from "@aws-cdk/aws-apigateway";
import * as route53 from "@aws-cdk/aws-route53";
import * as cdk from "@aws-cdk/core";
import * as acm from '@aws-cdk/aws-certificatemanager';
import * as ssm from '@aws-cdk/aws-ssm';

/**
 * Construction properties for a ApiCustomDomain
 */
export interface ApiCustomDomainProps {
    /**
     * The full url of the API custom domain endpoint.
     */
    apiDomainName: string;
    /**
     * The ApiGateway API.
     */
    api: apiGtw.RestApi;
    /**
     * The HostedZone that will hold the API custom domain records.
     */
    hostedZone: route53.IHostedZone;
}

/**
 * A CDK Construct that creates a Custom Domain for an API Gateway's RestAPI and the necessary ACM Certificate.
 */
export class ApiCustomDomain extends cdk.Construct {
    apiDomain: apiGtw.DomainName;

    constructor(scope: cdk.Construct, id: string, props: ApiCustomDomainProps) {
        super(scope, id);

        //Create the ACM Certificate for the API custom domain and the Route53 record necessary to validate it
        const apiCertificate = new acm.Certificate(this, 'api-certificate', {
            domainName: props.apiDomainName,
            validation: acm.CertificateValidation.fromDns(props.hostedZone),
        });

        props.api.addDomainName("api-custom-domain-name", {
            domainName: props.apiDomainName,
            securityPolicy: apiGtw.SecurityPolicy.TLS_1_2,
            certificate: apiCertificate
        });

        //Export the API certificate ARN to SSM
        new ssm.StringParameter(this, 'api-certificate-arn', {
            stringValue: apiCertificate.certificateArn,
            parameterName: '/samplifier/backend/acm/apiCertificate/arn'
        });

    }
}