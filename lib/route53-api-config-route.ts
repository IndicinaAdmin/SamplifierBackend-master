import * as cdk from "@aws-cdk/core";
import * as route53 from '@aws-cdk/aws-route53';
import * as route53_targets from "@aws-cdk/aws-route53-targets";
import * as apiGtw from "@aws-cdk/aws-apigateway";

/**
 * Construction properties for a Route53ApiConfigRoute
 */
export interface Route53ApiConfigRouteProps {
    /** The full url of the API custom domains. */
    domainNames: string[];

    /** The ApiGateway API. */
    api: apiGtw.RestApi;

    /** The HostedZone that will hold the API custom domain records. */
    hostedZone: route53.IHostedZone;
}

/**
 * A CDK Construct to create the necessary Alias record on a HostedZone for an API custom domain
 */
export class Route53ApiConfigRoute extends cdk.Construct {

    constructor(scope: cdk.Construct, id: string, props: Route53ApiConfigRouteProps) {
        super(scope, id);

        this.configureRoute53Records(props.domainNames, props.api, props.hostedZone);
    }

    /**
     * Create the Alias record
     * @param domainNames The full url of the API custom domains.
     * @param api The ApiGateway API.
     * @param hostedZoneInstance
     * @private The HostedZone that will hold the API custom domain records.
     */
    private configureRoute53Records(domainNames: string[], api: apiGtw.RestApi, hostedZoneInstance: route53.IHostedZone) {

        //Creates records that points each domain name to the api gateway
        for (let i = 0; i < domainNames.length; i++) {
            new route53.ARecord(this, 'api-alias-record'.concat(i.toString()), {
                recordName: domainNames[i],
                zone: hostedZoneInstance,
                target: route53.RecordTarget.fromAlias(new route53_targets.ApiGateway(api))
            });
        }
    }
}