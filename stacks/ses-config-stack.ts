import * as cdk from '@aws-cdk/core';
import * as route53 from "@aws-cdk/aws-route53";
import * as ssm from '@aws-cdk/aws-ssm';
import * as iam from '@aws-cdk/aws-iam';
import * as customResources from '@aws-cdk/custom-resources';
import { ParameterHelper } from '../lib/helpers/ssm-helper';
export interface SesConfigStackProps extends cdk.StackProps {
    hostedZoneId: string,
    hostedZoneName: string,
}
export class SesConfigStack extends cdk.Stack {
    zone: route53.IHostedZone;
    domainIdentityArn: string;
    constructor(scope: cdk.Construct, id: string, props: SesConfigStackProps) {
        super(scope, id, props);

        this.zone = this.importHostedZone(props.hostedZoneId, props.hostedZoneName);

        const sesPolicy = new iam.PolicyStatement({
            actions: [
                'ses:CreateConfigurationSet',
                'ses:DeleteConfigurationSet',
                'ses:CreateConfigurationSetEventDestination',
                'ses:DeleteConfigurationSetEventDestination',
                'ses:CreateEmailIdentity',
                'ses:DeleteEmailIdentity',
                'ses:GetIdentityMailFromDomainAttributes',
                'ses:SetIdentityMailFromDomain',
                'ses:PutEmailIdentityMailFromAttributes'
            ],
            resources: ['*'], // Global is required to Create. Delete could be restricted if required.
            effect: iam.Effect.ALLOW,
        });

        // Add and verify Domain using DKIM
        const domainIdentity = new customResources.AwsCustomResource(this, 'ses-domain-identity', {
            onUpdate: {
                service: 'SESV2',
                action: 'createEmailIdentity',
                parameters: {
                    EmailIdentity: this.zone.zoneName,
                    // ConfigurationSetName: configurationSetName, // Will set the default Configuration Set for the domain
                },
                physicalResourceId: {},
            },
            onDelete: {
                service: 'SESV2',
                action: 'deleteEmailIdentity',
                parameters: {
                    EmailIdentity: this.zone.zoneName,
                },
            },
            policy: customResources.AwsCustomResourcePolicy.fromStatements([sesPolicy]),
            logRetention: 7,
        });

        //Assuming there are always 3 tokens returned as that is what all the docs indicate
        let dkimTokens = [
            domainIdentity.getResponseField('DkimAttributes.Tokens.0'),
            domainIdentity.getResponseField('DkimAttributes.Tokens.1'),
            domainIdentity.getResponseField('DkimAttributes.Tokens.2'),
        ];


        // Add DKIM tokens to domain (or just output for manual entry)
        dkimTokens.forEach((token, i) => {
            const recordName = `${token}._domainkey.${this.zone.zoneName}`;
            if (props.hostedZoneId) {
                let record = new route53.CnameRecord(this, `token${i + 1}`, {
                    domainName: `${token}.dkim.amazonses.com`,
                    zone: this.zone,
                    recordName,
                    comment: 'SES DKIM Verification',
                });
                record.node.addDependency(domainIdentity)
            }
        });

        //Get the Domain Identity ARN
        // @ts-ignore
        this.domainIdentityArn = cdk.Arn.format({
            service: "ses",
            resource: "identity",
            partition: "aws",
            resourceName: ParameterHelper.getParameter(this, props.hostedZoneName, 'ses'),
            sep: "/"
        }, this);

        new ssm.StringParameter(this, 'ses-domain-identity-arn', {
            stringValue: this.domainIdentityArn,
            parameterName: '/samplifier/ses/domainIdentity/arn'
        });

        const mailFromDomain = "mail.".concat(this.zone.zoneName);

        // Sets a custom MAIL FROM for the domain identity
        const mailFrom = new customResources.AwsCustomResource(this, 'ses-mail-from', {
            onUpdate: {
                service: 'SESV2',
                action: 'putEmailIdentityMailFromAttributes',
                parameters: {
                    EmailIdentity: this.zone.zoneName,
                    MailFromDomain: mailFromDomain,
                    BehaviorOnMxFailure: "USE_DEFAULT_VALUE"
                },
                physicalResourceId: {},
            },
            onDelete: {
                service: 'SESV2',
                //The same method is used to enable or disable the custom Mail-From domain configuration
                //for an email identity
                action: 'putEmailIdentityMailFromAttributes',
                parameters: {
                    EmailIdentity: this.zone.zoneName,
                },
            },
            policy: customResources.AwsCustomResourcePolicy.fromStatements([sesPolicy]),
            logRetention: 7,
        });

        mailFrom.node.addDependency(domainIdentity);

        //The custom mail from needs the addition of records to route53  to be validated
        //The value of this records follows the pattern presented in the link below:
        // https://docs.aws.amazon.com/ses/latest/DeveloperGuide/mail-from.html
        const mxRecord = new route53.MxRecord(this, 'mail-from-domain-mx-record', {
            values: [
                {
                    priority: 10,
                    hostName: "feedback-smtp.".concat(this.region).concat(".amazonses.com")
                }
            ],
            zone: this.zone,
            recordName: mailFromDomain,
        });
        mxRecord.node.addDependency(mailFrom);
        const txtRecord = new route53.TxtRecord(this, 'mail-from-domain-txt-record', {
            values: ["v=spf1 include:amazonses.com ~all"],
            zone: this.zone,
            recordName: mailFromDomain,
        });
        txtRecord.node.addDependency(mailFrom)
    }

    private importHostedZone(hostedZoneId: string, hostedZoneName: string) {
        const hostedZoneAttributes: route53.HostedZoneAttributes = {
            hostedZoneId: ParameterHelper.getParameter(this, hostedZoneId),
            zoneName: ParameterHelper.getParameter(this, hostedZoneName)
        }
        return route53.HostedZone.fromHostedZoneAttributes(this, 'importedHostedZone', hostedZoneAttributes);
    }
}