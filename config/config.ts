export const CONFIG = { //Never modify this parameters
    serviceName: "samplifier-backend-api",
    deployment: {
        account: "988544517913",
        region: "us-east-1"
    },
    ssmParameters: {
        hostedZoneId: "/samplifier/route53/hostedzone/id",
        hostedZoneName: "/samplifier/route53/hostedzone/name",
        googleSecret: "/samplifier/cognito/idp/google/clientSecret",
        msSecret: "/samplifier/cognito/idp/microsoft/clientSecret"
    },
    dev: {
        account: "267274201794",
        region: "us-east-1",
        idp: {
            googleId: "152972182391-juivom3i9cjd98lqnsghh222m7athv58.apps.googleusercontent.com",
            msId: "b4c3b21b-1240-4c81-b235-4604a9f68e2d"
        }
    },
    staging: {
        account: "134727687918",
        region: "us-east-1",
        idp: {
            googleId: "947470417324-kvebe75gk9vl8iff6821to90dkug94j8.apps.googleusercontent.com",
            msId: "4da9d172-68f2-45fb-96b1-0ddbc8f07c0d"
        }
    },
    prod: {
        account: "153856174313",
        region: "us-east-1",
        idp: {
            googleId: "122210451561-vklcqo6fbmvvinkf23muutaeq822h64j.apps.googleusercontent.com",
            msId: "a7ca82e0-2401-42dd-8f91-399f9e8de93a"
        }
    }
}