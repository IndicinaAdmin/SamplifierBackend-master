import * as cdk from '@aws-cdk/core';
import * as apigateway from '@aws-cdk/aws-apigateway';
import * as logs from '@aws-cdk/aws-logs';
import * as cognito from '@aws-cdk/aws-cognito';
import * as route53 from "@aws-cdk/aws-route53";
import * as druid from 'druid-cdk-construct';
import * as lambda from "@aws-cdk/aws-lambda";
import * as iam from '@aws-cdk/aws-iam';
import * as wafv2 from '@aws-cdk/aws-wafv2';
import * as route53_targets from "@aws-cdk/aws-route53-targets";
import * as path from 'path';

import {ApiCustomDomain} from './api-custom-domain';
import {ParameterHelper} from './helpers/ssm-helper';

export interface BaseRestApiProps extends apigateway.RestApiProps {
    variables: any;
    userPool: cognito.IUserPool;
    hostedZoneInstance: route53.IHostedZone;
}

export class BaseRestApi extends apigateway.RestApi {
    private userPool: cognito.IUserPool;
    calcProxyFunction: druid.LambdaPowerToolsFunction;
    userProxyFunction: druid.LambdaPowerToolsFunction;

    constructor(scope: cdk.Construct, id: string, props: BaseRestApiProps) {
        // Create a cognito authorizer using the User Pool
        const authorizer = new apigateway.CognitoUserPoolsAuthorizer(scope, 'cognito-authorizer', {
            cognitoUserPools: [props.userPool]
        });

        const logGroup = new logs.LogGroup(scope, "api-default-log", {
            removalPolicy: cdk.RemovalPolicy.DESTROY,
            retention: logs.RetentionDays.SIX_MONTHS,
            logGroupName: String(props.variables.serviceName).concat('-default-log')
        });

        const logGroupDestination = new apigateway.LogGroupLogDestination(logGroup);

        const defaultProps = {
            restApiName: props.variables.serviceName,
            apiKeySourceType: apigateway.ApiKeySourceType.AUTHORIZER,
            cloudWatchRole: true,
            deployOptions: {
                stageName: "v1",
                /* This is equivalent to "Log full requests/responses data" in the API Gateway console at the stage's
                Logs/Tracing tab. If enabled will print logs containing the headers including the jwt token. */
                dataTraceEnabled: false,
                tracingEnabled: true,
                metricsEnabled: true,
                accessLogDestination: logGroupDestination,
                accessLogFormat: apigateway.AccessLogFormat.jsonWithStandardFields(),
                loggingLevel: apigateway.MethodLoggingLevel.INFO
            },
            defaultMethodOptions: {
                authorizationType: apigateway.AuthorizationType.COGNITO,
                authorizer: authorizer,
            },
            defaultCorsPreflightOptions: {
                allowOrigins: apigateway.Cors.ALL_ORIGINS,
                allowMethods: apigateway.Cors.ALL_METHODS,
                allowHeaders: apigateway.Cors.DEFAULT_HEADERS,
            },
        } as apigateway.RestApiProps;

        const mergeProps = Object.assign({}, defaultProps, props);
        super(scope, id, mergeProps);

        this.userPool = props.userPool;

        this.domainConfiguration(props.hostedZoneInstance);
        this.routes(props.variables.serviceName);
        this.parameters();
        this.waf(scope);
    }

    // all routes must be declared here
    private routes(apiName: string) {

        // route for calc
        this.calcProxyFunction = new druid.LambdaPowerToolsFunction(this, 'proxy-function', {
            entry: path.resolve(__dirname, '../runtime'),
            index: '_calc_proxy_controller.py',
            handler: 'handler',
            functionName: apiName.concat('-calc-proxy-controller'),
            serviceName: apiName,
            memorySize: 512,
            timeout: cdk.Duration.seconds(30),
            logRetention: logs.RetentionDays.SIX_MONTHS,
            environment: {
                LOG_EVENTS: "true"
            }
        });

        this.calcProxyFunction.role?.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMFullAccess'));

        const calcIntegration = new apigateway.LambdaIntegration(this.calcProxyFunction.alias);
        this.root.addResource('calc').addProxy({
            anyMethod: true,
            defaultIntegration: calcIntegration
        });

        // route for users
        this.userProxyFunction = new druid.LambdaPowerToolsFunction(this, 'user-proxy-function', {
            entry: path.resolve(__dirname, '../runtime'),
            index: '_user_proxy_controller.py',
            handler: 'handler',
            functionName: apiName.concat('-user-proxy-controller'),
            serviceName: apiName,
            logRetention: logs.RetentionDays.TWO_YEARS,
            environment: {
                LOG_EVENTS: "true"
            }
        });
        this.grantAccessToUserPool(this.userProxyFunction);
        this.userProxyFunction.role?.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMFullAccess'));
        this.userProxyFunction.role?.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSESFullAccess'));

        const userIntegration = new apigateway.LambdaIntegration(this.userProxyFunction.alias);
        this.root.addResource('user').addProxy({
            defaultIntegration: userIntegration,
            anyMethod: true
        });

        this.methods
            .filter((method) => method.httpMethod === "OPTIONS")
            .forEach((method) => {
                const methodCfn = method.node.defaultChild as apigateway.CfnMethod;
                methodCfn.authorizationType = apigateway.AuthorizationType.NONE;
                methodCfn.authorizerId = undefined;
            });
    }

    private domainConfiguration(hostedZoneInstance: route53.IHostedZone) {
        // Sets a custom domain for the API, including the ACM certificate
        const apiCustomDomain = new ApiCustomDomain(this, 'api-custom-domain', {
            apiDomainName: `api.${hostedZoneInstance.zoneName}`,
            api: this,
            hostedZone: hostedZoneInstance,
        });

        const recordRoutAPI = new route53.ARecord(this, 'api-alias-record', {
            recordName: `api.${hostedZoneInstance.zoneName}`,
            zone: hostedZoneInstance,
            target: route53.RecordTarget.fromAlias(new route53_targets.ApiGateway(this))
        });

        ParameterHelper.putParameter(this, '/samplifier/backend/api/domain/url', `api.${hostedZoneInstance.zoneName}`);

        // The routes need to wait for the custom domain to be created
        recordRoutAPI.node.addDependency(apiCustomDomain);
    }

    private parameters() {
        ParameterHelper.putParameter(this, '/samplifier/backend/api/url', this.url);
        ParameterHelper.putParameter(this, '/samplifier/backend/api/restApiId', this.restApiId);
    }

    protected grantAccessToUserPool(fn: lambda.IFunction) {
        fn.addToRolePolicy(
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                actions: [
                    "cognito-identity:*",
                    "cognito-idp:*",
                ],
                resources: [
                    this.userPool.userPoolArn
                ],
            })
        );

        fn.role?.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonCognitoPowerUser'));
    }

    private waf(scope: cdk.Construct) {
        const webAcl = new wafv2.CfnWebACL(scope, 'ApiGWWebACL', {
            description: 'ACL for REST API',
            scope: 'REGIONAL',
            defaultAction: { allow: {} },
            visibilityConfig: {
                cloudWatchMetricsEnabled: true,
                metricName: 'WAF',
                sampledRequestsEnabled: true
            },
            rules: [{
                    priority: 1,
                    overrideAction: { none: {} },
                    visibilityConfig: {
                        sampledRequestsEnabled: true,
                        cloudWatchMetricsEnabled: true,
                        metricName: "AWS-AWSManagedRulesAmazonIpReputationList",
                    },
                    name: "AWS-AWSManagedRulesAmazonIpReputationList",
                    statement: {
                        managedRuleGroupStatement: {
                            vendorName: "AWS",
                            name: "AWSManagedRulesAmazonIpReputationList",
                        },
                    },
                },
                {
                    priority: 2,
                    overrideAction: { none: {} },
                    visibilityConfig: {
                        sampledRequestsEnabled: true,
                        cloudWatchMetricsEnabled: true,
                        metricName: "AWS-AWSManagedRulesCommonRuleSet",
                    },
                    name: "AWS-AWSManagedRulesCommonRuleSet",
                    statement: {
                        managedRuleGroupStatement: {
                            vendorName: "AWS",
                            name: "AWSManagedRulesCommonRuleSet",
                        },
                    },
                },
                {
                    priority: 3,
                    overrideAction: { none: {} },
                    visibilityConfig: {
                        sampledRequestsEnabled: true,
                        cloudWatchMetricsEnabled: true,
                        metricName: "AWS-AWSManagedRulesKnownBadInputsRuleSet",
                    },
                    name: "AWS-AWSManagedRulesKnownBadInputsRuleSet",
                    statement: {
                        managedRuleGroupStatement: {
                            vendorName: "AWS",
                            name: "AWSManagedRulesKnownBadInputsRuleSet",
                        },
                    },
                },
                {
                    priority: 4,
                    overrideAction: { none: {} },
                    visibilityConfig: {
                        sampledRequestsEnabled: true,
                        cloudWatchMetricsEnabled: true,
                        metricName: "AWS-AWSManagedRulesLinuxRuleSet",
                    },
                    name: "AWS-AWSManagedRulesLinuxRuleSet",
                    statement: {
                        managedRuleGroupStatement: {
                            vendorName: "AWS",
                            name: "AWSManagedRulesLinuxRuleSet",
                        },
                    },
                },
            ]
        })

        const arn = `arn:aws:apigateway:${this.env.region}::/restapis/${this.restApiId}/stages/${this.deploymentStage.stageName}`;

        new wafv2.CfnWebACLAssociation(scope, "WebAclAssociation", {
            webAclArn: webAcl.attrArn,
            resourceArn: arn,
        });
    }
}