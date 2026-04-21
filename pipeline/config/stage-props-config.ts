import { STAGES } from "druid-cdk-construct"

export const CONFIG = {
    qa: {
        configAction: {
            useOutputs: {},
            commands: [
                "make runtime-int-test"
            ],
            name: "integration-tests"
        },
        name: STAGES.QASATGE
    },
    preProd: {
        name: STAGES.QASATGE,
        configAction: {
            useOutputs: {
                "FUNC_NAME": "functionName"
            },
            commands: [
                "make cdk-e2e funcName=$FUNC_NAME"
            ],
            name: "e2e-tests"
        }
    },
    prod: {
        name: STAGES.QASATGE
    }
}