import * as cdk from '@aws-cdk/core';
import * as cognito from '@aws-cdk/aws-cognito';

/**
 * Construction properties for a SamplifierUserPoolClient
 */
export interface SamplifierUserPoolClientProps extends cognito.UserPoolClientProps {
    /**
     * The callback urls.
     * Where the where the Identity Providers should redirect users to after a sign in or sign out
     */
    cognitoCallbackUrls: string[];
}

/**
 * A custom Cognito UserPoolClient construct
 */
export class SamplifierUserPoolClient extends cognito.UserPoolClient {
    /** A domain address for the  Hosted UI */
    readonly userPoolDomain: cognito.UserPoolDomain;

    constructor(scope: cdk.Construct, id: string, props: SamplifierUserPoolClientProps) {

        // User Pool Client attributes
        const standardCognitoAttributes = {
            givenName: true,
            familyName: true,
            email: true,
            emailVerified: true
        };

        const clientReadAttributes = new cognito.ClientAttributes()
            .withStandardAttributes(standardCognitoAttributes)
            .withCustomAttributes(...['companyName']);

        const clientWriteAttributes = new cognito.ClientAttributes()
            .withStandardAttributes({
                ...standardCognitoAttributes,
                emailVerified: false,
                phoneNumberVerified: false,
            })
            .withCustomAttributes(...['companyName']);

        //Necessary so the User Pool Client supports our custom IdP
        const msUPCIdP = cognito.UserPoolClientIdentityProvider.custom("Microsoft");

        const defaultProps = {
            userPool: props.userPool,
            userPoolClientName: props.userPoolClientName,
            generateSecret: false,
            authFlows: {
                adminUserPassword: true,
                custom: true,
                userSrp: true,
            },
            oAuth: {
                callbackUrls: props.cognitoCallbackUrls,
                logoutUrls: props.cognitoCallbackUrls,
            },
            supportedIdentityProviders: [
                cognito.UserPoolClientIdentityProvider.COGNITO, cognito.UserPoolClientIdentityProvider.GOOGLE, msUPCIdP,
            ],
            readAttributes: clientReadAttributes,
            writeAttributes: clientWriteAttributes,
            refreshTokenValidity: cdk.Duration.hours(1),
            accessTokenValidity: cdk.Duration.minutes(15),
            idTokenValidity: cdk.Duration.minutes(15)
        } as cognito.UserPoolClientProps;

        super(scope, id, defaultProps);
    }
}